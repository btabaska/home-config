#!/usr/bin/env python3
"""reopen-report.py (fix-61 / SM47) — the REAL consumer of the reopen bridge.

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
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

FOSS = Path(__file__).resolve().parents[2]  # .../foss-setup
REMOTE = "/var/lib/verification/reopen-suggestions.json"


def load_suggestions(args):
    if args.file:
        return json.load(open(args.file))
    out = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", args.host,
         f"cat {REMOTE}"],
        capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        print(f"reopen-report: cannot read {args.host}:{REMOTE}: "
              f"{out.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    return json.loads(out.stdout)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="mini")
    ap.add_argument("--file", help="read a local reopen-suggestions.json instead of ssh")
    args = ap.parse_args()

    sug = load_suggestions(args)
    tasks = json.load(open(FOSS / "docs" / "tasks.json"))
    prog = json.load(open(FOSS / "docs" / "progress.json"))
    idset = {t.get("id") for t in tasks}
    done = {k for k, v in prog.get("done", {}).items() if v}
    retired = set(prog.get("retired", {}))
    deferred = set(prog.get("deferred", {}))
    reopened = set(prog.get("reopened", {}))

    # map task_id -> failing check ids
    checks_by_task = {}
    for c in sug.get("failed_checks", []):
        checks_by_task.setdefault(c.get("task_id"), []).append(
            f"{c.get('id')}({c.get('severity')})")

    reopen, open_covered, other, unknown = [], [], [], []
    for tid in sorted(sug.get("task_ids", [])):
        checks = ", ".join(checks_by_task.get(tid, []))
        row = (tid, checks)
        if tid not in idset:
            unknown.append(row)
        elif tid in retired:
            other.append((tid, checks, "retired"))
        elif tid in reopened:
            other.append((tid, checks, "already reopened"))
        elif tid in done:
            reopen.append(row)
        elif tid in deferred:
            other.append((tid, checks, "deferred"))
        else:
            open_covered.append(row)

    print(f"# Reopen report — suggestions generated {sug.get('generated','?')}")
    print(f"# {len(sug.get('task_ids', []))} task_ids from "
          f"{len(sug.get('failed_checks', []))} failing checks\n")

    print(f"## REOPEN CANDIDATES ({len(reopen)}) — done tasks with a failing check")
    for tid, checks in reopen:
        print(f"  - {tid:12s} <- {checks}")
    if not reopen:
        print("  (none)")

    print(f"\n## already open ({len(open_covered)}) — failing check on an open task (covered)")
    for tid, checks in open_covered:
        print(f"  - {tid:12s} <- {checks}")
    if not open_covered:
        print("  (none)")

    if other:
        print(f"\n## no action ({len(other)})")
        for tid, checks, why in other:
            print(f"  - {tid:12s} [{why}] <- {checks}")

    print(f"\n## UNKNOWN task_ids ({len(unknown)}) — not in tasks.json (fix the check's task_id)")
    for tid, checks in unknown:
        print(f"  - {tid:12s} <- {checks}")
    if not unknown:
        print("  (none)")

    # exit 1 only if a task_id resolves to nothing — a traceability defect worth
    # surfacing; the reopen/open split itself is informational (exit 0).
    sys.exit(1 if unknown else 0)


if __name__ == "__main__":
    main()
