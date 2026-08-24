#!/usr/bin/env python3
"""checksd-runbook-lint — every checks.d `runbook:` must resolve to a real wiki page.

fix-99 (2026-08-23): the 2026-08-23 sweep found ~160 checks pointing at nonexistent
runbook paths — two classes: the wrong prefix (`wiki/runbooks/X.md` instead of the
published `wiki/docs/runbooks/X.md`) and basenames that never existed (docker.md,
dns.md, nas.md, rig.md, media.md, …). A crit alert's runbook link dead-ended exactly
when an operator needed it. This lint is the recurrence guard: it fails the publish if
any `runbook:` FIELD (not comment prose) doesn't resolve, so a dead link is unpushable
rather than discovered mid-incident.

A runbook value resolves if it is:
  - wiki/docs/runbooks/<name>.md  and foss-setup/wiki/docs/runbooks/<name>.md exists, or
  - wiki/docs/{services,reference}/….md  and that file exists.

Run from the repo root (or anywhere — it locates foss-setup/ relative to itself).
Exit 0 clean, 1 on any dead reference. Prints each offender as <file>:<line> <value>.
"""
import glob
import os
import re
import sys

FIELD = re.compile(r"^\s*runbook:\s*(\S+)\s*$")


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", ".."))  # foss-setup/
    checks_glob = os.path.join(root, "verification", "checks.d", "*.yaml")
    runbooks = {os.path.basename(p)[:-3]
                for p in glob.glob(os.path.join(root, "wiki", "docs", "runbooks", "*.md"))}
    dead = []
    total = 0
    for f in sorted(glob.glob(checks_glob)):
        for n, line in enumerate(open(f), 1):
            m = FIELD.match(line)
            if not m:
                continue
            total += 1
            v = m.group(1)
            ok = False
            if v.startswith("wiki/docs/runbooks/"):
                ok = v.split("/")[-1][:-3] in runbooks
            elif v.startswith("wiki/docs/services/") or v.startswith("wiki/docs/reference/"):
                ok = os.path.exists(os.path.join(root, v))
            if not ok:
                dead.append(f"{os.path.basename(f)}:{n}: {v}")
    if dead:
        print(f"RUNBOOK-LINT FAIL — {len(dead)} dead runbook reference(s):")
        for d in dead:
            print("  " + d)
        sys.exit(1)
    print(f"RUNBOOK-LINT OK — all {total} checks.d runbook: references resolve to a wiki page")


if __name__ == "__main__":
    main()
