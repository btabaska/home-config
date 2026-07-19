#!/usr/bin/env python3
"""tracker-count-check.py — fix-43 (L77/L78) tracker-arithmetic regression guard.

The generated tracker views must stay arithmetically consistent with the JSONs.
Dual-status tasks (in `done` AND `retired`, e.g. sbom-01/04) count exactly once —
retired wins — which is what gen-todo.py / gen-roadmap-pages.py enforce since
fix-43. Against a repo checkout given as argv[1] this checks:

  1. todo.md summary line: done + open + deferred + retired == total tasks
  2. that line matches a fresh recount from tasks.json + progress.json
  3. wiki/docs/roadmap/index.md has no negative table cell (the L77 symptom)

Prints TRACKER-COUNTS-OK on success; prints the mismatch and exits 1 otherwise.
"""
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
tasks = json.load(open(root / "foss-setup/docs/tasks.json"))
prog = json.load(open(root / "foss-setup/docs/progress.json"))
done = {k for k, v in prog["done"].items() if v}
retired = set(prog.get("retired", {}))
deferred = set(prog.get("deferred", {}))

ids = [t["id"] for t in tasks]
n = len(ids)
nd = sum(1 for i in ids if i in done and i not in retired)
nr = sum(1 for i in ids if i in retired)
ndf = sum(1 for i in ids if i in deferred and i not in done and i not in retired)
no = n - nd - nr - ndf

s = (root / "todo.md").read_text()
m = re.search(
    r"\*\*(\d+)/(\d+) done\*\* · \*\*(\d+) open\*\* · \*\*(\d+) deferred\*\* · (\d+) retired", s)
if not m:
    sys.exit("FAIL: todo.md summary line not found/parseable")
a, b, c, d, e = map(int, m.groups())

errs = []
if a + c + d + e != b:
    errs.append(f"todo.md arithmetic broken: {a}+{c}+{d}+{e} != {b}")
if (a, b, c, d, e) != (nd, n, no, ndf, nr):
    errs.append(f"todo.md stale vs JSONs: page says {(a, b, c, d, e)}, "
                f"recount says {(nd, n, no, ndf, nr)} — regenerate (gen-todo.py)")
idx = (root / "foss-setup/wiki/docs/roadmap/index.md").read_text()
if re.search(r"\|\s*-\d", idx):
    errs.append("roadmap index.md has a negative count cell — regenerate (gen-roadmap-pages.py)")

if errs:
    print("\n".join(errs))
    sys.exit(1)
print("TRACKER-COUNTS-OK")
