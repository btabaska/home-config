# `checksd-runbook-lint.py`

> checksd-runbook-lint — every checks.d `runbook:` must resolve to a real wiki page.

**Path:** `foss-setup/scripts/verification/checksd-runbook-lint.py` · **Category:** [verification](index.md) · **Type:** Python

## What it does

```text
checksd-runbook-lint — every checks.d `runbook:` must resolve to a real wiki page.

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
```

## See also

- [`catalog-vhost-parity.py`](catalog-vhost-parity-py.md)
- [`deploy.sh`](deploy-sh.md)
- [`reopen-report.py`](reopen-report-py.md)
- [`repo-secret-scan.py`](repo-secret-scan-py.md)
- [`stack-mirror-check.sh`](stack-mirror-check-sh.md)
- [`tracker-count-check.py`](tracker-count-check-py.md)
- [`tracker-integrity.py`](tracker-integrity-py.md)
- [`unit-drift-check.sh`](unit-drift-check-sh.md)
- [verification scripts](index.md) · [All scripts](../index.md)
