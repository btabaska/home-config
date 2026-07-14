#!/usr/bin/env python3
"""gen-todo.py — generate the single todo.md (all remaining project tasks).

Reads the canonical task data (docs/tasks.json = definitions) + docs/progress.json
(status) and writes /todo.md at the repo root: every REMAINING task (open +
deferred), grouped by track, plus a summary. This is the one working todo list;
the wiki roadmap is the browsable mirror; both generate from the same data. Run
after any task change. Deterministic.

Usage: python3 foss-setup/scripts/docs/gen-todo.py
"""
import json
from pathlib import Path

FOSS = Path(__file__).resolve().parents[2]          # .../foss-setup
REPO_ROOT = FOSS.parent                              # .../Home
tasks = json.load(open(FOSS / "docs" / "tasks.json"))
prog = json.load(open(FOSS / "docs" / "progress.json"))
done = {k for k, v in prog["done"].items() if v}
deferred = prog.get("deferred", {})
retired = prog.get("retired", {})

by_track = {}
for t in tasks:
    by_track.setdefault(t.get("track", "uncategorized"), []).append(t)

n_done = sum(1 for t in tasks if t["id"] in done)
n_ret = sum(1 for t in tasks if t["id"] in retired)
open_tasks, def_tasks = [], []
for t in tasks:
    if t["id"] in done or t["id"] in retired:
        continue
    (def_tasks if t["id"] in deferred else open_tasks).append(t)

L = ["# TODO — Going Analogue homelab", "",
     "**The single todo list for this project.** Generated from `foss-setup/docs/tasks.json` "
     "(task definitions) + `foss-setup/docs/progress.json` (status) by "
     "`foss-setup/scripts/docs/gen-todo.py`. The wiki is the browsable mirror + the reference "
     "source of truth: <https://wiki.tabaska.us/roadmap/>. Re-run the generator after any change.", "",
     f"**{n_done}/{len(tasks)} done** · **{len(open_tasks)} open** · **{len(def_tasks)} deferred** · {n_ret} retired.", "",
     "---", "", "## Open (remaining work)", ""]

for track in sorted(by_track):
    ts = sorted((t for t in by_track[track] if t in open_tasks), key=lambda x: x["id"])
    if not ts:
        continue
    L.append(f"### {track}")
    for t in ts:
        est = t.get("estimate", "")
        gate = t.get("gate", "")
        extra = (f" _(est {est})_" if est else "") + (f" — ⛔ gate: {gate}" if gate else "")
        L.append(f"- [ ] **`{t['id']}`** {t.get('title','')}{extra}")
    L.append("")

L += ["---", "", "## Deferred (parked — optional / hardware-gated / someday)", ""]
for t in sorted(def_tasks, key=lambda x: x["id"]):
    reason = deferred.get(t["id"], "")
    reason = reason.split(":", 1)[-1].strip() if ":" in reason else reason
    L.append(f"- **`{t['id']}`** {t.get('title','')} — _{reason[:120]}_")
L += ["", "---", "",
      "_Hardware to buy for these: see `foss-setup/docs/hardware-shopping-list.md` "
      "(wiki: <https://wiki.tabaska.us/reference/hardware/>). Full per-track tables + done/retired "
      "history: the wiki roadmap._", ""]

(REPO_ROOT / "todo.md").write_text("\n".join(L))
print(f"wrote {REPO_ROOT/'todo.md'}: {len(open_tasks)} open, {len(def_tasks)} deferred, {n_done} done")
