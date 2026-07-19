# `tracker-integrity.py`

> data-level consistency check for the task tracker.

**Path:** `foss-setup/scripts/verification/tracker-integrity.py` · **Category:** [verification](index.md) · **Type:** Python

## Synopsis

```
python3 foss-setup/scripts/verification/tracker-integrity.py
```

## What it does

```text
tracker-integrity.py — data-level consistency check for the task tracker.

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
```

## See also

- [`deploy.sh`](deploy-sh.md)
- [`stack-mirror-check.sh`](stack-mirror-check-sh.md)
- [`tracker-count-check.py`](tracker-count-check-py.md)
- [`unit-drift-check.sh`](unit-drift-check-sh.md)
- [verification scripts](index.md) · [All scripts](../index.md)
