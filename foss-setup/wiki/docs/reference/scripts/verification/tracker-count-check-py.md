# `tracker-count-check.py`

> fix-43 (L77/L78) tracker-arithmetic regression guard.

**Path:** `foss-setup/scripts/verification/tracker-count-check.py` · **Category:** [verification](index.md) · **Type:** Python

## What it does

```text
tracker-count-check.py — fix-43 (L77/L78) tracker-arithmetic regression guard.

The generated tracker views must stay arithmetically consistent with the JSONs.
Dual-status tasks (in `done` AND `retired`, e.g. sbom-01/04) count exactly once —
retired wins — which is what gen-todo.py / gen-roadmap-pages.py enforce since
fix-43. Against a repo checkout given as argv[1] this checks:

  1. todo.md summary line: done + open + deferred + retired == total tasks
  2. that line matches a fresh recount from tasks.json + progress.json
  3. wiki/docs/roadmap/index.md has no negative table cell (the L77 symptom)

Prints TRACKER-COUNTS-OK on success; prints the mismatch and exits 1 otherwise.
```

## See also

- [`deploy.sh`](deploy-sh.md)
- [`stack-mirror-check.sh`](stack-mirror-check-sh.md)
- [`unit-drift-check.sh`](unit-drift-check-sh.md)
- [verification scripts](index.md) · [All scripts](../index.md)
