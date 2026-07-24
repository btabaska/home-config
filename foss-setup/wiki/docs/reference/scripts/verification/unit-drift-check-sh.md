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

 glue-13 extended coverage to the rig's other hand-copied foss-setup host units
 (gpu-power-tune.service, the export-manifests service+timer). Nothing converges
 these either — see configs/host/rig/README.md for the full unit->source map.
 Only STATIC foss-setup mirrors are checked here: ansible-managed backup units
 (restic-backup, ntfy-notify@) are templated + self-heal daily, and fleet-mcp /
 the ollama override are owned by the separate local-ai-tooling repo.

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
