# `unit-drift-check.sh`

> fix-43 (L86 class): hand-copied systemd unit files must

**Path:** `foss-setup/scripts/verification/unit-drift-check.sh` · **Category:** [verification](index.md) · **Type:** Bash

## Synopsis

```
unit-drift-check.sh <repo-checkout-root>
```

## What it does

```text
 unit-drift-check.sh — fix-43 (L86 class): hand-copied systemd unit files must
 stay byte-identical to the repo copy on every host that runs them. The
 ansible-pull units are NOT converged by the pull flow itself (site.yml does
 not install them — see the timer's own header), so drift here is silent until
 it bites (the 2026-07-15 stale-playbook-path missed run, L6).

 Usage: unit-drift-check.sh <repo-checkout-root>
 Prints UNIT-DRIFT-OK, or lists each mismatch and exits 1. An unreachable rig
 counts as drift (fail-loud beats silently skipping the comparison).
```

## See also

- [`deploy.sh`](deploy-sh.md)
- [`stack-mirror-check.sh`](stack-mirror-check-sh.md)
- [`tracker-count-check.py`](tracker-count-check-py.md)
- [`tracker-integrity.py`](tracker-integrity-py.md)
- [verification scripts](index.md) · [All scripts](../index.md)
