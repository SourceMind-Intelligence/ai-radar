---
name: embodied-harness-radar
description: Run the daily Awesome Embodied Harness radar. Scan arXiv, Hugging Face, GitHub, lab blogs and news for new embodied-harness systems (robot agent loops, VLAs, embodied reasoning models, robot tool interfaces, memory, verification, safety, sims, benchmarks, data). Verify each against primary sources, update awesome-embodied-harness/data, write the radar log, rebuild the README, then commit and push. Use when asked to run the embodied harness radar, or to add or refresh entries in the awesome-embodied-harness list.
---

# Embodied harness radar

The canonical procedure is `awesome-embodied-harness/radar/PLAYBOOK.md`. Read it in full and follow it step by step. This file only summarizes it.

1. `cd awesome-embodied-harness && python3 scripts/awesome.py validate`
2. `python3 scripts/awesome.py scan`, then run the web searches and check the watch pages listed in `radar/sources.yaml`.
3. Triage each candidate as add, update, watch or skip, using the inclusion bar in `CONTRIBUTING.md`.
4. Verify every add. Use `find` against duplicates and `stub <arxiv-id>` for exact titles and dates. Open each link. Never guess a URL.
5. Edit `data/<category>.yaml` and `radar/candidates.yaml`, then run `validate`, `check-links --added-since <today>` and `build`.
6. Write `radar/log/<today>.md` from the template in the playbook, run `build` again, then commit and push.

When the user runs this by hand and passes arguments (for example a date window or a single paper to add), apply the playbook to that scope only.
