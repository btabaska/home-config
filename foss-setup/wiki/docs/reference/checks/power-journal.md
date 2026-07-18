# Checks — power-journal

`foss-setup/verification/checks.d/power-journal.yaml` — 3 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `nut-monitor-retired`

fix-31 mini nut-monitor is retired (masked+inactive, no dead-poll spam)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-31` · **enabled:** True
- **expects:** `^NUT_RETIRED_OK$`

```bash
a=$(systemctl is-active nut-monitor.service 2>/dev/null || true); e=$(systemctl is-enabled nut-monitor.service 2>/dev/null || true); errs=$(journalctl -u nut-monitor.service --since '-2 min' 2>/dev/null | grep -c 'connect failed' || true); if [ "$a" != active ] && [ "$e" = masked ] && [ "${errs:-1}" -eq 0 ]; then echo NUT_RETIRED_OK; else echo "NUT_NOT_RETIRED active=$a enabled=$e errs2m=${errs:-?}"; fi
```

## `journal-not-bloated-mini`

fix-31 mini systemd journal is under the size cap (<2G)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-31` · **enabled:** True
- **expects:** `^JOURNAL_OK`

```bash
u=$(journalctl --disk-usage 2>/dev/null | grep -oE '[0-9.]+[KMGT]' | tail -n1); b=$(numfmt --from=iec "$u" 2>/dev/null || echo 0); if [ "${b:-0}" -lt 2147483648 ]; then echo "JOURNAL_OK usage=$u"; else echo "JOURNAL_BLOAT usage=$u cap=2G"; fi
```

## `journal-not-bloated-rig`

fix-31 rig systemd journal is under the size cap (<2G)

- **host:** `rig` · **severity:** `warn` · **guards task:** `fix-31` · **enabled:** True
- **expects:** `^JOURNAL_OK`

```bash
u=$(journalctl --disk-usage 2>/dev/null | grep -oE '[0-9.]+[KMGT]' | tail -n1); b=$(numfmt --from=iec "$u" 2>/dev/null || echo 0); if [ "${b:-0}" -lt 2147483648 ]; then echo "JOURNAL_OK usage=$u"; else echo "JOURNAL_BLOAT usage=$u cap=2G"; fi
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
