# Checks — nas-io-storm

`foss-setup/verification/checks.d/nas-io-storm.yaml` — 2 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `nas-io-pressure`

NAS: 15-min I/O-load below threshold (not saturated — the fix-55 storm signal)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-55` · **enabled:** True
- **expects:** `status=OK`

```bash
python3 /opt/verification/bin/nas-io-storm-probe.py io
```

## `arr-sqlite-not-locked`

NAS arrs: no SQLite 'database is locked' storm in the last 15min (lidarr/radarr/whisparr)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-55` · **enabled:** True
- **expects:** `status=OK`

```bash
python3 /opt/verification/bin/nas-io-storm-probe.py locks
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
