# Checks — soularr-backlog

`foss-setup/verification/checks.d/soularr-backlog.yaml` — 2 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `soularr-denylist-no-ghosts`

soularr: failed-import denylist has 0 ghosts (complete/unmonitored/deleted) (fix-56)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-56` · **enabled:** True
- **expects:** `^DENYLIST_OK`

```bash
python3 /opt/verification/bin/soularr-denylist-ghosts.py
```

## `soularr-reconcile-timer-healthy`

soularr denylist reconciler timer active + last run not failed (fix-56)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-56` · **enabled:** True
- **expects:** `^RECONCILE_TIMER_OK`

```bash
systemctl is-active --quiet soularr-denylist-reconcile.timer && [ "$(systemctl show -p Result --value soularr-denylist-reconcile.service)" != failed ] && echo RECONCILE_TIMER_OK || echo RECONCILE_TIMER_BAD
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
