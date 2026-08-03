# `reopen-report.py`

> reopen-report.py (fix-61 / SM47) — the REAL consumer of the reopen bridge.

**Path:** `foss-setup/scripts/verification/reopen-report.py` · **Category:** [verification](index.md) · **Type:** Python

## What it does

```text
reopen-report.py (fix-61 / SM47) — the REAL consumer of the reopen bridge.

The runner (verify-05) writes /var/lib/verification/reopen-suggestions.json on
mini: every task_id that a currently-failing check points at. That is a raw list,
NOT a vetted reopen set — the runner has no tracker access, so it cannot tell a
done task (a genuine regression to reopen) from an already-open one (ha-19, whose
failing check is already covered) or a stale/orphan task_id (verify-06 before it
existed in tasks.json). For weeks the docs claimed "the AI session-start protocol
consumes this file", but nothing did — it was write-only.

This script IS that consumer. It fetches the suggestions (over ssh from mini by
default, or from a local --file for testing), cross-references docs/progress.json
and docs/tasks.json in this repo, and splits the task_ids into:

  REOPEN CANDIDATES  — marked done (and not retired) with a failing check now
  already open        — failing check is on a still-open task (already covered)
  reopened/deferred/retired — annotated, no action
  UNKNOWN task_id     — points at no task in tasks.json (fix the check's task_id)

Run by /fleet-sweep and /resolve-finding as the session-start step. Read-only:
prints a report and never edits the tracker (reopening stays a human/AI judgment
call, per verify-05's design). stdlib only.

Usage:
  scripts/verification/reopen-report.py              # ssh mini for the live file
  scripts/verification/reopen-report.py --file X.json # use a local copy
```

## See also

- [`deploy.sh`](deploy-sh.md)
- [`stack-mirror-check.sh`](stack-mirror-check-sh.md)
- [`tracker-count-check.py`](tracker-count-check-py.md)
- [`tracker-integrity.py`](tracker-integrity-py.md)
- [`unit-drift-check.sh`](unit-drift-check-sh.md)
- [verification scripts](index.md) · [All scripts](../index.md)
