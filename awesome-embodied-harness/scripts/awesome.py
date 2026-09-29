#!/usr/bin/env python3
"""Maintenance CLI for Awesome Embodied Harness.

Commands (run from anywhere; paths resolve relative to the project root):

  validate                 Check data/*.yaml, radar/candidates.yaml and radar logs.
  build [--check]          Regenerate categories/*.md and the generated blocks in
                           README.md and SURVEY.md. --check exits 1 if anything is
                           out of date (for CI).
  find QUERY...            Look for existing entries by id, name, title, alias or URL.
                           Run this before adding anything.
  stub ARXIV_ID...         Print YAML entry stubs with title/date/link filled in from
                           the arXiv API (summary, org and access still need a human).
  scan [--since DATE]      List new arXiv and Hugging Face daily papers that match the
                           radar queries in radar/sources.yaml and are not yet listed.
  check-links              Verify links: arXiv IDs and titles through the arXiv API,
                           GitHub repos through raw.githubusercontent.com, other URLs
                           over HTTP. Exits 1 if any link is definitely broken.
  stats                    Print entry counts by category, year and access level.
  fmt [--check]            Rewrite data/*.yaml in canonical form (key order, folded
                           summaries, flow-style tags). Entry order is preserved.

Only PyYAML is required (pip install pyyaml).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required: pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TAXONOMY = ROOT / "taxonomy.yaml"
README = ROOT / "README.md"
SURVEY = ROOT / "SURVEY.md"
RADAR_DIR = ROOT / "radar"
LOG_DIR = RADAR_DIR / "log"
CANDIDATES = RADAR_DIR / "candidates.yaml"
CATEGORY_DIR = ROOT / "categories"
README_PER_CATEGORY = 10  # newest entries shown per category in README.md
SOURCES = RADAR_DIR / "sources.yaml"

USER_AGENT = "awesome-embodied-harness/1.0 (+https://github.com/SourceMind-Intelligence/ai-radar)"
ARXIV_API = "https://export.arxiv.org/api/query"
HF_DAILY_API = "https://huggingface.co/api/daily_papers"
ATOM = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

ENTRY_KEYS = {"id", "name", "title", "date", "org", "summary", "links", "access",
              "tags", "note", "aliases", "added", "updated"}
REQUIRED_KEYS = ("id", "name", "date", "summary", "links", "access", "added")
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MONTH_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])(?:-(0[1-9]|[12]\d|3[01]))?$")
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ARXIV_ID_RE = re.compile(r"arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})(?:v\d+)?", re.I)
GITHUB_RE = re.compile(r"^https://github\.com/([^/\s]+)/([^/\s#?]+)", re.I)
SUMMARY_MAX = 320
GEN_RE = re.compile(r"(<!-- BEGIN GENERATED: ([a-z-]+) -->\n)(.*?)(<!-- END GENERATED: \2 -->)", re.S)


# --------------------------------------------------------------------------- io

def load_yaml(path: Path):
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def as_str(value) -> str:
    """YAML turns 2026-09-29 into a date object; normalise dates back to text."""
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()[:10]
    return "" if value is None else str(value)


def load_taxonomy() -> dict:
    tax = load_yaml(TAXONOMY)
    tax["baseline"] = as_str(tax.get("baseline"))
    tax["category_keys"] = [c["key"] for c in tax["categories"]]
    return tax


def load_entries(tax: dict) -> dict[str, list[dict]]:
    """Return {category: [entry, ...]} with dates normalised to strings."""
    out: dict[str, list[dict]] = {}
    for key in tax["category_keys"]:
        path = DATA_DIR / f"{key}.yaml"
        items = load_yaml(path) if path.exists() else []
        items = items or []
        for item in items:
            if isinstance(item, dict):
                for field in ("date", "added", "updated"):
                    if field in item:
                        item[field] = as_str(item[field])
                item["_category"] = key
        out[key] = items
    return out


def all_entries(entries: dict[str, list[dict]]) -> list[dict]:
    return [e for items in entries.values() for e in items if isinstance(e, dict)]


def arxiv_ids(entry: dict) -> list[str]:
    ids = []
    for url in (entry.get("links") or {}).values():
        m = ARXIV_ID_RE.search(str(url))
        if m:
            ids.append(m.group(1))
    return ids


def norm_url(url: str) -> str:
    url = str(url).strip().lower()
    m = ARXIV_ID_RE.search(url)
    if m:
        return f"arxiv:{m.group(1)}"
    url = re.sub(r"^https?://(www\.)?", "", url)
    url = re.sub(r"(\.git)?/*$", "", url)
    return url


def norm_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(text).lower())


def norm_title(text: str) -> str:
    """Compare titles without LaTeX markup: arXiv writes 'RobotArena $\\infty$'."""
    return norm_text(re.sub(r"\\[a-zA-Z]+", "", str(text)))


def http_get(url: str, timeout: float = 30, method: str = "GET") -> tuple[int, bytes]:
    req = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read() if method == "GET" else b""
    except urllib.error.HTTPError as err:
        return err.code, b""


def today() -> str:
    return dt.date.today().isoformat()


# --------------------------------------------------------------------- validate

class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def validate_entry(entry, where: str, tax: dict, rep: Report) -> None:
    if not isinstance(entry, dict):
        rep.error(f"{where}: entry is not a mapping")
        return
    for key in REQUIRED_KEYS:
        if not entry.get(key):
            rep.error(f"{where}: missing required field '{key}'")
    for key in entry:
        if key not in ENTRY_KEYS and not key.startswith("_"):
            rep.error(f"{where}: unknown field '{key}'")

    eid = str(entry.get("id", ""))
    if eid and not ID_RE.match(eid):
        rep.error(f"{where}: id '{eid}' must be lowercase kebab-case")

    date = as_str(entry.get("date"))
    m = MONTH_RE.match(date)
    if date and not m:
        rep.error(f"{where}: date '{date}' must be YYYY-MM or YYYY-MM-DD")
    elif m and not (1990 <= int(m.group(1)) <= dt.date.today().year + 1):
        rep.error(f"{where}: date '{date}' is out of range")

    for field in ("added", "updated"):
        value = as_str(entry.get(field))
        if value and not DAY_RE.match(value):
            rep.error(f"{where}: {field} '{value}' must be YYYY-MM-DD")

    summary = entry.get("summary")
    if summary is not None:
        if not isinstance(summary, str):
            rep.error(f"{where}: summary must be a string")
        elif len(summary) > SUMMARY_MAX:
            rep.error(f"{where}: summary is {len(summary)} chars (max {SUMMARY_MAX})")

    if entry.get("access") and entry["access"] not in tax["access"]:
        rep.error(f"{where}: access '{entry['access']}' not in {sorted(tax['access'])}")

    links = entry.get("links")
    if links is not None:
        if not isinstance(links, dict) or not links:
            rep.error(f"{where}: links must be a non-empty mapping")
        else:
            for key, url in links.items():
                if key not in tax["link_keys"]:
                    rep.error(f"{where}: link key '{key}' not in {tax['link_keys']}")
                if not isinstance(url, str) or not url.startswith("https://"):
                    rep.error(f"{where}: link '{key}' must be an https:// URL")
                    continue
                if re.search(r"arxiv\.org/(pdf|html)/", url):
                    rep.error(f"{where}: link to the arXiv abs page, not {url}")
                if re.search(r"arxiv\.org/abs/\d{4}\.\d{4,5}v\d+$", url):
                    rep.error(f"{where}: drop the version suffix from {url}")

    tags = entry.get("tags") or []
    if not isinstance(tags, list):
        rep.error(f"{where}: tags must be a list")
    else:
        for tag in tags:
            if tag not in tax["tags"]:
                rep.warn(f"{where}: tag '{tag}' is not in taxonomy.yaml")

    aliases = entry.get("aliases")
    if aliases is not None and not (isinstance(aliases, list) and all(isinstance(a, str) for a in aliases)):
        rep.error(f"{where}: aliases must be a list of strings")


def validate(tax: dict, entries: dict[str, list[dict]]) -> Report:
    rep = Report()
    known = set(tax["category_keys"])
    for path in sorted(DATA_DIR.glob("*.yaml")):
        if path.stem not in known:
            rep.error(f"data/{path.name}: no category '{path.stem}' in taxonomy.yaml")
    for key in tax["category_keys"]:
        if not (DATA_DIR / f"{key}.yaml").exists():
            rep.error(f"data/{key}.yaml is missing")

    ids: dict[str, str] = {}
    urls: dict[str, str] = {}   # normalised paper/code URLs, for the candidates check
    papers: dict[tuple[str, str], str] = {}
    names: dict[str, str] = {}
    for key, items in entries.items():
        if not isinstance(items, list):
            rep.error(f"data/{key}.yaml must contain a YAML list")
            continue
        for idx, entry in enumerate(items):
            where = f"data/{key}.yaml[{idx}]"
            if isinstance(entry, dict) and entry.get("id"):
                where = f"data/{key}.yaml:{entry['id']}"
            validate_entry(entry, where, tax, rep)
            if not isinstance(entry, dict):
                continue
            eid = entry.get("id")
            if eid:
                if eid in ids:
                    rep.error(f"{where}: duplicate id (also in {ids[eid]})")
                ids[eid] = where
            # One paper can introduce several listed artifacts (a model and its
            # dataset, say), but within one category a repeated paper link is
            # almost always the same system listed twice. Shared code links are
            # fine (openpi hosts several pi-models).
            for link_key in ("paper", "code"):
                url = (entry.get("links") or {}).get(link_key)
                if isinstance(url, str):
                    urls.setdefault(norm_url(url), where)
            paper = (entry.get("links") or {}).get("paper")
            if isinstance(paper, str):
                slot = (key, norm_url(paper))
                if slot in papers:
                    rep.error(f"{where}: paper link duplicates {papers[slot]}")
                papers[slot] = where
            # Same name and same release month is probably one system listed twice;
            # same name in different months is usually two different papers.
            name = norm_text(entry.get("name", "")) + "@" + str(entry.get("date", ""))[:7]
            if not name.startswith("@"):
                if name in names:
                    rep.warn(f"{where}: same name and date as {names[name]} — duplicate?")
                names[name] = where

    if CANDIDATES.exists():
        cands = load_yaml(CANDIDATES) or []
        if not isinstance(cands, list):
            rep.error("radar/candidates.yaml must contain a YAML list")
        else:
            for idx, cand in enumerate(cands):
                where = f"radar/candidates.yaml[{idx}]"
                if not isinstance(cand, dict):
                    rep.error(f"{where}: not a mapping")
                    continue
                for field in ("name", "url", "first_seen", "suggested_category", "reason"):
                    if not cand.get(field):
                        rep.error(f"{where}: missing '{field}'")
                if cand.get("suggested_category") and cand["suggested_category"] not in known:
                    rep.error(f"{where}: unknown suggested_category '{cand['suggested_category']}'")
                if cand.get("url") and norm_url(cand["url"]) in urls:
                    rep.warn(f"{where}: '{cand.get('name')}' is already listed; remove it from candidates")

    for log in sorted(LOG_DIR.glob("*.md")):
        meta = read_front_matter(log)
        if not meta.get("date") or not meta.get("headline"):
            rep.error(f"radar/log/{log.name}: front matter needs 'date' and 'headline'")
        elif as_str(meta["date"]) != log.stem:
            rep.error(f"radar/log/{log.name}: front matter date does not match file name")
    return rep


def read_front_matter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    meta = yaml.safe_load(m.group(1)) or {}
    return meta if isinstance(meta, dict) else {}


def cmd_validate(args) -> int:
    tax = load_taxonomy()
    entries = load_entries(tax)
    rep = validate(tax, entries)
    for msg in rep.warnings:
        print(f"warning: {msg}")
    for msg in rep.errors:
        print(f"error: {msg}")
    total = len(all_entries(entries))
    print(f"{total} entries, {len(rep.errors)} errors, {len(rep.warnings)} warnings")
    return 1 if rep.errors else 0


# ------------------------------------------------------------------------ build

def sort_key(entry: dict):
    return (entry.get("date", ""), entry.get("name", "").lower())


def primary_link(entry: dict, tax: dict) -> tuple[str | None, str | None]:
    links = entry.get("links") or {}
    for key in ("paper", "project", "blog", "code", "docs", "weights", "data", "video"):
        if links.get(key):
            return key, links[key]
    return None, None


def md_escape(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def render_entry(entry: dict, tax: dict) -> str:
    icon = tax["access"].get(entry.get("access"), {}).get("icon", "")
    name = md_escape(entry["name"])
    key, url = primary_link(entry, tax)
    title = md_escape(entry.get("title", "")).replace('"', "'")
    if url:
        tip = f' "{title}"' if title and norm_text(title) != norm_text(name) else ""
        head = f"[**{name}**]({url}{tip})"
    else:
        head = f"**{name}**"
    meta = [entry.get("date", "")[:7]]
    if entry.get("org"):
        meta.append(md_escape(entry["org"]))
    extras = []
    for link_key in tax["link_keys"]:
        link = (entry.get("links") or {}).get(link_key)
        if link and link != url:
            extras.append(f"[{link_key}]({link})")
    line = f"- {icon} {head} · {' · '.join(meta)} — {md_escape(entry['summary'])}"
    if entry.get("note"):
        line += f" _Note: {md_escape(entry['note'])}_"
    if extras:
        line += " " + " · ".join(extras)
    return line


def render_years(items: list[dict], tax: dict) -> str:
    by_year: dict[str, list[dict]] = defaultdict(list)
    for entry in sorted(items, key=sort_key, reverse=True):
        by_year[entry.get("date", "")[:4]].append(entry)
    parts = []
    for year in sorted(by_year, reverse=True):
        parts.append(f"**{year}**\n")
        parts.append("\n".join(render_entry(e, tax) for e in by_year[year]) + "\n")
    return "\n".join(parts)


def legend(tax: dict) -> str:
    return "**Legend:** " + " · ".join(f"{v['icon']} {v['label'].split(' — ')[0]}" for v in tax["access"].values())


def render_list(tax: dict, entries: dict[str, list[dict]]) -> str:
    """README overview: the newest entries of each category plus a link to its full page."""
    parts = []
    for cat in tax["categories"]:
        items = sorted(entries.get(cat["key"], []), key=sort_key, reverse=True)
        page = f"categories/{cat['key']}.md"
        parts.append(f'<a id="{cat["key"]}"></a>\n## {cat["title"]}\n')
        parts.append(f"> {md_escape(cat['blurb'])}  \n> Layer: {cat['layer']} · {len(items)} entries · "
                     f"**[full list →]({page})**\n")
        if not items:
            parts.append("_Nothing here yet._\n")
            continue
        shown = items[:README_PER_CATEGORY]
        parts.append("\n".join(render_entry(e, tax) for e in shown) + "\n")
        more = len(items) - len(shown)
        tail = f"[+ {more} more in the full list]({page}) · " if more > 0 else ""
        parts.append(f"<sub>{tail}[↑ back to contents](#contents)</sub>\n")
    return "\n".join(parts)


def render_category_page(cat: dict, items: list[dict], tax: dict) -> str:
    return (
        f"<!-- Generated by scripts/awesome.py build from data/{cat['key']}.yaml. Edit the YAML, not this file. -->\n\n"
        f"# {cat['title']}\n\n"
        f"> {md_escape(cat['blurb'])}  \n> Layer: {cat['layer']} · {len(items)} entries · "
        f"[overview](../README.md#{cat['key']}) · [survey](../SURVEY.md)\n\n"
        f"{legend(tax)}. Hover a name for the full paper title. Newest first within each year.\n\n"
        + (render_years(items, tax) if items else "_Nothing here yet._\n")
    )


def render_toc(tax: dict, entries: dict[str, list[dict]]) -> str:
    lines = []
    for cat in tax["categories"]:
        n = len(entries.get(cat["key"], []))
        lines.append(f"- [{cat['title']}](#{cat['key']}) ({n})")
    return "\n".join(lines) + "\n"


def render_recent(tax: dict, entries: dict[str, list[dict]], days: int = 30) -> str:
    flat = all_entries(entries)
    fresh = [e for e in flat if e.get("added") and e["added"] != tax["baseline"]]
    if fresh:
        newest = max(e["added"] for e in fresh)
        cutoff = (dt.date.fromisoformat(newest) - dt.timedelta(days=days)).isoformat()
        fresh = [e for e in fresh if e["added"] >= cutoff]
    if not fresh:
        return ("_No additions since the initial import on "
                f"{tax['baseline']}. The daily radar lists new entries here._\n")
    cats = {c["key"]: c["title"] for c in tax["categories"]}
    fresh.sort(key=lambda e: (e["added"], e.get("date", "")), reverse=True)
    lines = [f"Added in the {days} days up to {fresh[0]['added']}:\n"]
    for entry in fresh:
        lines.append(render_entry(entry, tax) + f" _(added {entry['added']} to [{cats[entry['_category']]}](#{entry['_category']}))_")
    return "\n".join(lines) + "\n"


def render_radar(limit: int = 7) -> str:
    logs = sorted(LOG_DIR.glob("*.md"), reverse=True)[:limit]
    if not logs:
        return "_No radar runs yet._\n"
    lines = []
    for log in logs:
        meta = read_front_matter(log)
        counts = []
        for field in ("added", "updated", "candidates"):
            if meta.get(field):
                counts.append(f"{meta[field]} {field}")
        suffix = f" ({', '.join(counts)})" if counts else ""
        lines.append(f"- [{log.stem}](radar/log/{log.name}) — {md_escape(meta.get('headline', ''))}{suffix}")
    return "\n".join(lines) + "\n"


def render_badges(tax: dict, entries: dict[str, list[dict]]) -> str:
    total = len(all_entries(entries))
    logs = sorted(LOG_DIR.glob("*.md"))
    last = logs[-1].stem if logs else "none"
    badge = lambda label, value, color: (
        f"![{label}](https://img.shields.io/badge/{urllib.parse.quote(label)}-"
        f"{urllib.parse.quote(str(value).replace('-', '--'))}-{color})")
    return " ".join([
        badge("entries", total, "blue"),
        badge("categories", len(tax["categories"]), "blueviolet"),
        badge("last radar", last, "success"),
        badge("license", "CC0-1.0", "lightgrey"),
    ]) + "\n"


def render_stats(tax: dict, entries: dict[str, list[dict]]) -> str:
    flat = all_entries(entries)
    years = sorted({e.get("date", "")[:4] for e in flat if e.get("date")})
    recent_years = [y for y in years if y >= "2022"]
    head = "| Category | Layer | Total | " + " | ".join(
        (["≤2021"] if any(y < "2022" for y in years) else []) + recent_years) + " | open |"
    sep = "|" + "---|" * (head.count("|") - 1)
    rows = [head, sep]
    for cat in tax["categories"]:
        items = entries.get(cat["key"], [])
        counts = Counter(e.get("date", "")[:4] for e in items)
        cells = [f"[{cat['title']}](categories/{cat['key']}.md)", cat["layer"], str(len(items))]
        if any(y < "2022" for y in years):
            cells.append(str(sum(v for y, v in counts.items() if y < "2022")))
        cells += [str(counts.get(y, 0)) for y in recent_years]
        cells.append(str(sum(1 for e in items if e.get("access") == "open")))
        rows.append("| " + " | ".join(cells) + " |")
    counts = Counter(e.get("date", "")[:4] for e in flat)
    total = ["**Total**", "", f"**{len(flat)}**"]
    if any(y < "2022" for y in years):
        total.append(str(sum(v for y, v in counts.items() if y < "2022")))
    total += [str(counts.get(y, 0)) for y in recent_years]
    total.append(str(sum(1 for e in flat if e.get("access") == "open")))
    rows.append("| " + " | ".join(total) + " |")
    return "\n".join(rows) + "\n"


def fill(text: str, blocks: dict[str, str], path: Path) -> str:
    seen = set()

    def repl(m: re.Match) -> str:
        name = m.group(2)
        if name not in blocks:
            return m.group(0)
        seen.add(name)
        return f"{m.group(1)}{blocks[name]}{m.group(4)}"

    out = GEN_RE.sub(repl, text)
    missing = set(blocks) - seen
    if missing:
        raise SystemExit(f"{path.name}: missing generated markers for {sorted(missing)}")
    return out


def cmd_build(args) -> int:
    tax = load_taxonomy()
    entries = load_entries(tax)
    rep = validate(tax, entries)
    if rep.errors:
        for msg in rep.errors:
            print(f"error: {msg}")
        print("fix validation errors before building")
        return 1
    targets = {
        README: {
            "badges": render_badges(tax, entries),
            "toc": render_toc(tax, entries),
            "radar": render_radar(),
            "recent": render_recent(tax, entries),
            "list": render_list(tax, entries),
        },
        SURVEY: {"stats": render_stats(tax, entries)},
    }
    stale = []
    for path, blocks in targets.items():
        old = path.read_text(encoding="utf-8")
        new = fill(old, blocks, path)
        if new != old:
            stale.append(path.name)
            if not args.check:
                path.write_text(new, encoding="utf-8")
    if not args.check:
        CATEGORY_DIR.mkdir(exist_ok=True)
    for cat in tax["categories"]:
        path = CATEGORY_DIR / f"{cat['key']}.md"
        new = render_category_page(cat, entries.get(cat["key"], []), tax)
        old = path.read_text(encoding="utf-8") if path.exists() else ""
        if new != old:
            stale.append(f"categories/{path.name}")
            if not args.check:
                path.write_text(new, encoding="utf-8")
    if args.check:
        if stale:
            print(f"out of date: {', '.join(stale)} — run: python3 scripts/awesome.py build")
            return 1
        print("generated files are up to date")
        return 0
    print(f"updated: {', '.join(stale)}" if stale else "nothing to update")
    return 0


# ------------------------------------------------------------------------- find

def cmd_find(args) -> int:
    tax = load_taxonomy()
    flat = all_entries(load_entries(tax))
    hits = 0
    for query in args.query:
        q_text = norm_text(query)
        q_url = norm_url(query) if ("/" in query or "." in query) else None
        m = ARXIV_ID_RE.search(query)
        bare = re.fullmatch(r"\d{4}\.\d{4,5}", query.strip())
        q_arxiv_id = m.group(1) if m else (query.strip() if bare else None)
        for entry in flat:
            fields = [entry.get("id", ""), entry.get("name", ""), entry.get("title", "")] + list(entry.get("aliases") or [])
            match = bool(q_text) and any(q_text in norm_text(f) for f in fields if f)
            links = (entry.get("links") or {}).values()
            if q_url and any(q_url == norm_url(u) or q_url in norm_url(u) for u in links):
                match = True
            if q_arxiv_id and q_arxiv_id in arxiv_ids(entry):
                match = True
            if match:
                hits += 1
                print(f"{query!r}: {entry['_category']}/{entry['id']} — {entry.get('name')} ({entry.get('date')})")
    if not hits:
        print("no matches")
    return 0


# ------------------------------------------------------------------------ arXiv

def arxiv_lookup(ids: list[str]) -> dict[str, dict]:
    """Fetch metadata for arXiv IDs in batches. Returns {id: {...}}."""
    out: dict[str, dict] = {}
    for start in range(0, len(ids), 50):
        batch = ids[start:start + 50]
        url = f"{ARXIV_API}?id_list={','.join(batch)}&max_results={len(batch)}"
        for attempt in range(3):
            status, body = http_get(url, timeout=60)
            if status == 200:
                break
            time.sleep(5 * (attempt + 1))
        else:
            raise RuntimeError(f"arXiv API returned {status}")
        out.update(parse_arxiv_feed(body))
        time.sleep(3)  # arXiv asks for at most one request every 3 seconds
    return out


def parse_arxiv_feed(body: bytes) -> dict[str, dict]:
    out = {}
    root = ET.fromstring(body)
    for e in root.findall("a:entry", ATOM):
        raw_id = e.findtext("a:id", default="", namespaces=ATOM)
        m = ARXIV_ID_RE.search(raw_id)
        if not m:
            continue
        prim = e.find("arxiv:primary_category", ATOM)
        out[m.group(1)] = {
            "id": m.group(1),
            "title": " ".join(e.findtext("a:title", default="", namespaces=ATOM).split()),
            "published": e.findtext("a:published", default="", namespaces=ATOM)[:10],
            "abstract": " ".join(e.findtext("a:summary", default="", namespaces=ATOM).split()),
            "authors": [a.findtext("a:name", default="", namespaces=ATOM) for a in e.findall("a:author", ATOM)],
            "category": prim.attrib.get("term", "") if prim is not None else "",
        }
    return out


def slugify(title: str) -> str:
    head = title.split(":")[0] if ":" in title and len(title.split(":")[0]) <= 40 else " ".join(title.split()[:4])
    head = head.replace("π", "pi").replace("₀", "0")
    return re.sub(r"[^a-z0-9]+", "-", head.lower()).strip("-")


def cmd_stub(args) -> int:
    meta = arxiv_lookup(args.ids)
    stubs = []
    for aid in args.ids:
        info = meta.get(aid)
        if not info:
            print(f"# {aid}: not found on arXiv", file=sys.stderr)
            continue
        name = info["title"].split(":")[0] if ":" in info["title"] and len(info["title"].split(":")[0]) <= 40 else info["title"]
        stubs.append({
            "id": slugify(info["title"]),
            "name": name,
            "title": info["title"],
            "date": info["published"][:7],
            "org": "TODO",
            "summary": "TODO — paraphrase the abstract in <= 2 factual sentences.",
            "links": {"paper": f"https://arxiv.org/abs/{aid}"},
            "access": "closed",
            "tags": [],
            "added": today(),
        })
        print(f"# {aid} [{info['category']}] {', '.join(info['authors'][:6])}{' et al.' if len(info['authors']) > 6 else ''}")
        print(f"# abstract: {info['abstract'][:900]}")
    if stubs:
        print(yaml.safe_dump(stubs, sort_keys=False, allow_unicode=True, width=100))
    return 0


# ------------------------------------------------------------------------- scan

def keyword_score(text: str, keywords: dict[str, float]) -> tuple[float, list[str]]:
    low = text.lower()
    score, hits = 0.0, []
    for kw, weight in keywords.items():
        if re.search(r"(?<![a-z0-9])" + re.escape(kw.lower()) + r"s?(?![a-z0-9])", low):
            score += float(weight)
            hits.append(kw)
    return score, hits


def last_log_date() -> str | None:
    logs = sorted(LOG_DIR.glob("*.md"))
    return logs[-1].stem if logs else None


def cmd_scan(args) -> int:
    tax = load_taxonomy()
    flat = all_entries(load_entries(tax))
    listed = {aid for e in flat for aid in arxiv_ids(e)}
    listed_urls = {norm_url(u) for e in flat for u in (e.get("links") or {}).values()}
    if CANDIDATES.exists():
        for cand in load_yaml(CANDIDATES) or []:
            if isinstance(cand, dict) and cand.get("url"):
                listed_urls.add(norm_url(cand["url"]))
                m = ARXIV_ID_RE.search(str(cand["url"]))
                if m:
                    listed.add(m.group(1))
    sources = load_yaml(SOURCES)
    scan_cfg = sources.get("scan", {})
    keywords = scan_cfg.get("keywords", {})
    required = {kw: 1 for kw in scan_cfg.get("require_any", [])}
    min_score = float(args.min_score if args.min_score is not None else scan_cfg.get("min_score", 3))

    since = args.since or last_log_date() or (dt.date.today() - dt.timedelta(days=2)).isoformat()
    until = args.until or today()
    print(f"# Radar scan {since} .. {until} (min score {min_score})\n", file=sys.stderr)

    found: dict[str, dict] = {}
    arxiv_cfg = sources.get("arxiv", {})
    for query in arxiv_cfg.get("queries", []):
        params = urllib.parse.urlencode({
            "search_query": query, "sortBy": "submittedDate", "sortOrder": "descending",
            "max_results": arxiv_cfg.get("max_results_per_query", 100)})
        status, body = http_get(f"{ARXIV_API}?{params}", timeout=60)
        time.sleep(3)
        if status != 200:
            print(f"warning: arXiv query failed ({status}): {query}", file=sys.stderr)
            continue
        for aid, info in parse_arxiv_feed(body).items():
            if not (since <= info["published"] <= until) or aid in listed:
                continue
            score, hits = keyword_score(f"{info['title']} {info['title']} {info['abstract']}", keywords)
            prev = found.get(aid)
            if prev is None or score > prev["score"]:
                found[aid] = {**info, "source": "arxiv", "score": score, "hits": hits,
                              "url": f"https://arxiv.org/abs/{aid}"}

    if sources.get("huggingface", {}).get("daily_papers", True):
        day = dt.date.fromisoformat(since)
        while day <= dt.date.fromisoformat(until):
            status, body = http_get(f"{HF_DAILY_API}?date={day.isoformat()}", timeout=60)
            if status == 200:
                for item in json.loads(body or b"[]"):
                    paper = item.get("paper", {})
                    aid = paper.get("id", "")
                    if not aid or aid in listed:
                        continue
                    text = f"{paper.get('title', '')} {paper.get('title', '')} {paper.get('summary', '')}"
                    score, hits = keyword_score(text, keywords)
                    upvotes = int(paper.get("upvotes") or 0)
                    entry = found.get(aid) or {
                        "id": aid, "title": " ".join(str(paper.get("title", "")).split()),
                        "published": str(paper.get("publishedAt", ""))[:10], "category": "",
                        "abstract": " ".join(str(paper.get("summary", "")).split()),
                        "score": score, "hits": hits, "source": "hf-daily",
                        "url": f"https://arxiv.org/abs/{aid}"}
                    entry["hf_upvotes"] = upvotes
                    entry["github"] = paper.get("githubRepo") or entry.get("github")
                    entry["project"] = paper.get("projectPage") or entry.get("project")
                    if "hf-daily" not in entry["source"]:
                        entry["source"] += "+hf-daily"
                    found[aid] = entry
            day += dt.timedelta(days=1)

    def relevant(f: dict) -> bool:
        return f["score"] >= min_score and (
            not required or keyword_score(f"{f['title']} {f['abstract']}", required)[0] > 0)

    for f in found.values():  # rank = keyword score + a small boost for HF upvotes
        f["rank"] = round(f["score"] + min(f.get("hf_upvotes", 0), 50) / 10, 1)
    ranked = sorted((f for f in found.values() if relevant(f)),
                    key=lambda f: (f["rank"], f["published"]), reverse=True)[: args.limit]
    if args.json:
        print(json.dumps(ranked, indent=2, ensure_ascii=False))
        return 0
    print(f"{len(ranked)} candidates (of {len(found)} unlisted papers in window)\n")
    for f in ranked:
        extra = []
        if f.get("hf_upvotes"):
            extra.append(f"HF↑{f['hf_upvotes']}")
        if f.get("github"):
            extra.append(f"code: {f['github']}")
        if f.get("project"):
            extra.append(f"project: {f['project']}")
        print(f"- [{f['rank']:g}] {f['id']} ({f['published']}, {f['category'] or f['source']}) {f['title']}")
        print(f"    matched: {', '.join(f['hits'])}{' | ' + ' | '.join(extra) if extra else ''}")
        print(f"    {f['abstract'][:320]}{'…' if len(f['abstract']) > 320 else ''}")
    return 0


# ------------------------------------------------------------------ check-links

def check_url(url: str) -> tuple[str, str]:
    """Return (status, detail) where status is ok | broken | unverifiable."""
    try:
        m = GITHUB_RE.match(url)
        if m:
            owner, repo = m.group(1), m.group(2).removesuffix(".git")
            for readme in ("README.md", "readme.md", "README.rst", "README", "Readme.md", "README.MD"):
                code, _ = http_get(f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{readme}",
                                   timeout=20, method="HEAD")
                if code == 200:
                    return "ok", "github"
                if code != 404:
                    return "unverifiable", f"github raw {code}"
            return "broken", "github repo not found (no README at HEAD)"
        code, _ = http_get(url, timeout=25, method="HEAD")
        if code in (400, 403, 405, 501) or code >= 500:
            code, _ = http_get(url, timeout=25)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as err:
        return "unverifiable", f"{type(err).__name__}: {getattr(err, 'reason', err)}"
    if 200 <= code < 400:
        return "ok", str(code)
    if code in (404, 410):
        return "broken", str(code)
    return "unverifiable", str(code)


def cmd_check_links(args) -> int:
    tax = load_taxonomy()
    flat = all_entries(load_entries(tax))
    if args.ids:
        flat = [e for e in flat if e.get("id") in set(args.ids)]
    if args.category:
        flat = [e for e in flat if e["_category"] == args.category]
    if args.added_since:
        flat = [e for e in flat if (e.get("added") or "") >= args.added_since or (e.get("updated") or "") >= args.added_since]
    print(f"checking {len(flat)} entries", file=sys.stderr)

    broken, unverifiable, warnings = [], [], []
    by_arxiv = defaultdict(list)
    others = []
    for entry in flat:
        for key, url in (entry.get("links") or {}).items():
            m = ARXIV_ID_RE.search(url)
            if m:
                by_arxiv[m.group(1)].append((entry, key))
            else:
                others.append((entry, key, url))

    if by_arxiv:
        try:
            meta = arxiv_lookup(sorted(by_arxiv))
        except RuntimeError as err:
            meta = None
            unverifiable.append(f"arXiv API unavailable: {err}")
        if meta is not None:
            for aid, refs in by_arxiv.items():
                info = meta.get(aid)
                for entry, key in refs:
                    tag = f"{entry['_category']}/{entry['id']} {key}"
                    if not info:
                        broken.append(f"{tag}: arXiv {aid} not found")
                        continue
                    if key == "paper" and entry.get("title") and norm_title(entry["title"]) != norm_title(info["title"]):
                        warnings.append(f"{tag}: title differs from arXiv: {info['title']!r}")
                    # `date` is the first public release, which may be a code or
                    # blog release before the paper, but never after arXiv v1.
                    if key == "paper" and entry.get("date", "")[:7] > info["published"][:7]:
                        warnings.append(f"{tag}: date {entry.get('date')} is after arXiv v1 {info['published'][:7]}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(check_url, url): (entry, key, url) for entry, key, url in others}
        for fut in concurrent.futures.as_completed(futures):
            entry, key, url = futures[fut]
            status, detail = fut.result()
            tag = f"{entry['_category']}/{entry['id']} {key} {url}"
            if status == "broken":
                broken.append(f"{tag}: {detail}")
            elif status == "unverifiable":
                unverifiable.append(f"{tag}: {detail}")

    for msg in sorted(warnings):
        print(f"warning: {msg}")
    for msg in sorted(unverifiable):
        print(f"unverifiable: {msg}")
    for msg in sorted(broken):
        print(f"broken: {msg}")
    n_links = sum(len(v) for v in by_arxiv.values()) + len(others)
    print(f"{n_links} links: {len(broken)} broken, {len(unverifiable)} unverifiable, {len(warnings)} warnings")
    return 1 if broken else 0


# -------------------------------------------------------------------------- fmt

KEY_ORDER = ["id", "name", "title", "aliases", "date", "org", "summary", "links",
             "access", "tags", "note", "added", "updated"]


def yaml_scalar(value) -> str:
    text = as_str(value) if isinstance(value, (dt.date, dt.datetime)) else value
    if isinstance(text, str) and (DAY_RE.match(text) or MONTH_RE.match(text)):
        return text
    out = yaml.safe_dump(text, allow_unicode=True, width=10**9, default_flow_style=True).strip()
    return out[:-3].strip() if out.endswith("...") else out


def dump_entry(entry: dict, tax: dict) -> str:
    import textwrap
    lines = []
    keys = [k for k in KEY_ORDER if k in entry] + sorted(
        k for k in entry if k not in KEY_ORDER and not k.startswith("_"))
    for i, key in enumerate(keys):
        value = entry[key]
        prefix = "- " if i == 0 else "  "
        if value in (None, "", [], {}):
            continue
        if key == "summary" or (key in ("note", "title") and len(str(value)) > 80):
            body = textwrap.wrap(" ".join(str(value).split()), width=88,
                                 break_long_words=False, break_on_hyphens=False)
            lines.append(f"{prefix}{key}: >-")
            lines.extend(f"    {line}" for line in body)
        elif key == "links":
            lines.append(f"{prefix}links:")
            order = [k for k in tax["link_keys"] if k in value] + [k for k in value if k not in tax["link_keys"]]
            lines.extend(f"    {k}: {yaml_scalar(value[k])}" for k in order)
        elif key in ("tags", "aliases"):
            lines.append(f"{prefix}{key}: [{', '.join(yaml_scalar(t) for t in value)}]")
        else:
            lines.append(f"{prefix}{key}: {yaml_scalar(value)}")
    return "\n".join(lines)


def dump_entries(items: list[dict], tax: dict, header: str = "") -> str:
    if not items:
        return header + "[]\n"
    return header + "\n\n".join(dump_entry(e, tax) for e in items) + "\n"


def file_header(path: Path) -> str:
    """Keep the leading comment block of a data file."""
    if not path.exists():
        return ""
    head = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or (not line.strip() and head):
            head.append(line)
        else:
            break
    while head and not head[-1].strip():
        head.pop()
    return ("\n".join(head) + "\n\n") if head else ""


def cmd_fmt(args) -> int:
    tax = load_taxonomy()
    entries = load_entries(tax)
    changed = []
    for key, items in entries.items():
        path = DATA_DIR / f"{key}.yaml"
        new = dump_entries(items, tax, file_header(path))
        old = path.read_text(encoding="utf-8") if path.exists() else ""
        if yaml.safe_load(new) is None and items:
            raise SystemExit(f"formatter produced invalid YAML for {path}")
        if new != old:
            changed.append(path.name)
            if not args.check:
                path.write_text(new, encoding="utf-8")
    if args.check and changed:
        print(f"not canonical: {', '.join(changed)} — run: python3 scripts/awesome.py fmt")
        return 1
    print(f"formatted: {', '.join(changed)}" if changed else "all data files are canonical")
    return 0


# ------------------------------------------------------------------------ stats

def cmd_stats(args) -> int:
    tax = load_taxonomy()
    entries = load_entries(tax)
    flat = all_entries(entries)
    print(f"total: {len(flat)}")
    for cat in tax["categories"]:
        print(f"  {cat['key']:<13} {len(entries.get(cat['key'], [])):>4}")
    years = Counter(e.get("date", "")[:4] for e in flat)
    print("by year: " + ", ".join(f"{y}: {years[y]}" for y in sorted(years)))
    access = Counter(e.get("access") for e in flat)
    print("by access: " + ", ".join(f"{k}: {v}" for k, v in access.most_common()))
    return 0


# ------------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate").set_defaults(func=cmd_validate)
    p = sub.add_parser("build")
    p.add_argument("--check", action="store_true")
    p.set_defaults(func=cmd_build)
    p = sub.add_parser("find")
    p.add_argument("query", nargs="+")
    p.set_defaults(func=cmd_find)
    p = sub.add_parser("stub")
    p.add_argument("ids", nargs="+", metavar="ARXIV_ID")
    p.set_defaults(func=cmd_stub)
    p = sub.add_parser("scan")
    p.add_argument("--since", help="YYYY-MM-DD (default: date of the latest radar log)")
    p.add_argument("--until", help="YYYY-MM-DD (default: today)")
    p.add_argument("--min-score", type=float)
    p.add_argument("--limit", type=int, default=60)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_scan)
    p = sub.add_parser("check-links")
    p.add_argument("--ids", nargs="*")
    p.add_argument("--category")
    p.add_argument("--added-since", help="only entries added or updated on/after YYYY-MM-DD")
    p.add_argument("--workers", type=int, default=8)
    p.set_defaults(func=cmd_check_links)
    sub.add_parser("stats").set_defaults(func=cmd_stats)
    p = sub.add_parser("fmt")
    p.add_argument("--check", action="store_true")
    p.set_defaults(func=cmd_fmt)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
