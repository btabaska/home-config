#!/usr/bin/env python3
"""tracker-integrity.py — data-level consistency check for the task tracker.

wiki-drift-check.sh proves the GENERATED pages match the tracker sources
(same-commit rule); this proves the SOURCES themselves are coherent. Added by
fix-44 for audit finding M46: progress.json carried an orphan done id
(nas-00e, no definition in tasks.json) and stale _meta counts that disagreed
with the generated todo.md — two published done-counts, one wrong.

FAILS (exit 1, prints every reason) when:
  - a task id appears more than once in tasks.json
  - any id in progress.json done/retired/deferred/reopened has no
    definition in tasks.json (the M46 orphan-id regression)
  - an id is both deferred and done, or deferred and retired
    (contradictory status the generators would misrender — the L77 class)
  - progress.json _meta carries task_count/completed_count again (fix-44
    removed them: no code consumer since the HTML tracker retired, they only
    drift; the generated todo.md/wiki roadmap are the only published counts)
  - the done/open/deferred/retired partition fails to sum to the task total
    under the generators' rules (retired wins over done; see gen-todo.py)

exit 0 = coherent · exit 1 = integrity violation · exit 2 = tooling error.

Usage: python3 foss-setup/scripts/verification/tracker-integrity.py
Wired into verification as the `tracker-integrity` check
(verification/checks.d/git-hygiene.yaml), run daily on mini against a fetched
clone of origin/main HEAD so the logic self-updates with the repo. Sibling of
tracker-count-check.py (fix-43), which checks the generated VIEWS against
these sources; this checks the sources themselves.
"""
import json
import sys
from pathlib import Path

FOSS = Path(__file__).resolve().parents[2]          # .../foss-setup
try:
    tasks = json.load(open(FOSS / "docs" / "tasks.json"))
    prog = json.load(open(FOSS / "docs" / "progress.json"))
except Exception as e:                              # noqa: BLE001
    print(f"tracker-integrity: cannot load tracker json: {e}", file=sys.stderr)
    sys.exit(2)

errs = []

ids = [t.get("id") for t in tasks]
idset = set(ids)
dups = sorted({i for i in ids if ids.count(i) > 1})
if dups:
    errs.append(f"duplicate task ids in tasks.json: {dups}")
if None in idset:
    errs.append("task entry with no id in tasks.json")

done = {k for k, v in prog.get("done", {}).items() if v}
retired = set(prog.get("retired", {}))
deferred = set(prog.get("deferred", {}))
reopened = set(prog.get("reopened", {}))
for name, s in (("done", done), ("retired", retired),
                ("deferred", deferred), ("reopened", reopened)):
    orphans = sorted(s - idset)
    if orphans:
        errs.append(f"orphan {name} ids (no definition in tasks.json): {orphans}")

for label, clash in (("deferred+done", deferred & done),
                     ("deferred+retired", deferred & retired)):
    if clash:
        errs.append(f"contradictory status {label}: {sorted(clash)}")

meta = prog.get("_meta", {})
stale = [k for k in ("task_count", "completed_count") if k in meta]
if stale:
    errs.append(f"_meta count fields reintroduced (fix-44 removed them; "
                f"todo.md/wiki are the only published counts): {stale}")

# Partition arithmetic under the generators' rules (retired wins over done,
# deferred only applies to still-open tasks) — mirrors gen-todo.py exactly.
n_done = sum(1 for i in idset if i in done and i not in retired)
n_ret = len(idset & retired)
n_def = sum(1 for i in idset if i in deferred and i not in done and i not in retired)
n_open = len(idset) - n_done - n_ret - n_def
if n_open < 0 or n_done + n_ret + n_def + n_open != len(idset):
    errs.append(f"partition broken: done={n_done} retired={n_ret} "
                f"deferred={n_def} open={n_open} total={len(idset)}")

if errs:
    print("TRACKER INTEGRITY: " + " | ".join(errs))
    sys.exit(1)

print(f"tracker coherent: {len(idset)} tasks = {n_done} done + {n_open} open "
      f"+ {n_def} deferred + {n_ret} retired; all status ids resolve")
