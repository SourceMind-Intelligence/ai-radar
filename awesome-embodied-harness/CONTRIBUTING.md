# Contributing

Humans and the daily radar agent follow the same rules. The list in `README.md` is generated; edit the YAML in `data/` instead.

```bash
pip install pyyaml
python3 scripts/awesome.py find "<name or url>"   # 1. not already listed?
# 2. edit data/<category>.yaml
python3 scripts/awesome.py validate               # 3. schema + duplicate checks
python3 scripts/awesome.py check-links --ids <id> # 4. links resolve, arXiv title/date match
python3 scripts/awesome.py build                  # 5. regenerate README.md / SURVEY.md blocks
```

CI runs `validate` and `build --check` on every pull request that touches this folder.

## Scope

A system belongs here if it is part of the **embodied harness stack**: anything that helps turn a foundation model into an agent acting in the physical world, or in a simulation built to transfer to it. `taxonomy.yaml` lists the categories, and [SURVEY.md](SURVEY.md) explains the layers. Pick the category that matches the item's *primary* contribution. Each system appears once; use `tags` for everything else.

Out of scope:

- purely digital agents (web, GUI, coding), unless the work transfers directly to embodied agents (for example, harness-engineering reviews);
- classical robotics without a learned or language-model component;
- hardware launches with no software, model or agent story.

## Inclusion bar

An item needs **all** of the following:

1. **In scope.** It fits one of the categories.
2. **Primary source.** A paper, an official repository, an official blog or model card, or a technical report. News articles only count when an industry announcement has no other public source.
3. **Verifiable.** Every link has been opened and resolves. Titles and dates match the source.

It also needs **at least one** of the following:

- it introduces a new harness pattern or component (a new way to expose skills, represent world state, verify outcomes, or keep the robot safe);
- it comes from a major lab or company, or is a widely adopted open-source project;
- it releases code, weights or data that others can build on;
- it is a benchmark, dataset or survey that the field uses to compare systems;
- it is strong, clearly documented work that fills a gap in a category.

## Entry schema

```yaml
- id: thea                     # lowercase kebab-case, unique across all files, never changes
  name: Thea                   # short system name as its authors write it
  title: Towards the Harness of Embodied Agents   # exact paper/report title (optional for non-papers)
  date: 2026-08                # YYYY-MM of first public release (arXiv v1 month, launch post)
  org: EIT Ningbo              # optional, short lab/company names
  summary: >-                  # 1-2 factual sentences, <= 320 characters
    Wraps robot capabilities as tools in an agentic loop, keeps a persistent scene
    graph as context, and treats evaluation as exit codes.
  links:                       # at least one; keys: paper, code, project, blog, weights, data, docs, video
    paper: https://arxiv.org/abs/2608.11246
    project: https://eit-hai.github.io/thea/
  access: closed               # open | partial | api | closed
  tags: [agentic-loop, scene-graph, tool-use]      # from taxonomy.yaml
  aliases: []                  # optional other names, used by `find`
  note: ""                     # optional caveat, e.g. "first-party results, not reproduced"
  added: 2026-09-29            # date the entry was added
  updated: 2026-10-02          # optional, date of the last material change
```

The `access` values mean:

| access | meaning |
|---|---|
| `open` | Code, and weights for models, publicly released. |
| `partial` | Some artifacts released: weights without training code, code without weights, dataset only. |
| `api` | Usable through an API, SDK or product, but not open. |
| `closed` | Paper, blog post or demo only. |

## Writing summaries

- Say what the system **is** and **does**: its mechanism, not its marketing. "Hierarchical VLA: a VLM plans in language and a flow-matching action expert executes at 50 Hz" beats "a groundbreaking step toward general robots".
- Paraphrase the abstract, README or official post. Do not copy it.
- Use numbers sparingly. When you use one, attribute it: "(first-party, LIBERO)".
- No superlatives ("first", "state-of-the-art", "best") unless you can attribute them to the source ("claims the first …").
- Link the arXiv **abs** page without a version suffix. Do not link PDFs or mirrors.

## Radar candidates

Some items look important but cannot be verified yet: an announcement with no paper, a demo video, a rumor. They go into `radar/candidates.yaml`, not `data/`:

```yaml
- name: Example Robot Brain 2
  url: https://example.com/announcement
  first_seen: 2026-09-29
  last_checked: 2026-09-29
  suggested_category: policy
  reason: Announced on stage; no paper, code or model card yet.
```
