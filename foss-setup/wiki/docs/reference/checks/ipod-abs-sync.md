# Checks — ipod-abs-sync

`foss-setup/verification/checks.d/ipod-abs-sync.yaml` — 1 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `ipod-abs-stage-fresh`

iPod ABS stage healthy (manifest + staged files present); iPod DB in sync when mounted

- **host:** `rig` · **severity:** `warn` · **guards task:** `read-19` · **enabled:** True
- **expects:** `^IPOD_(SYNC_OK|MOUNTED_UNSYNCED|ABSENT)`

```bash
python3 /home/btabaska/bin/abs-ipod-verify.py
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
