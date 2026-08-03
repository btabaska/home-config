# Checks — verification-self

`foss-setup/verification/checks.d/verification-self.yaml` — 7 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `llm-triage-completion-e2e`

verify-04 LLM triage: real completion succeeds (not just /models 200)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-30` · **enabled:** True
- **expects:** `TRIAGE_LLM_OK`

```bash
/opt/verification/bin/llm-triage-probe.sh
```

## `restic-marker-writer-rig`

rig restic-backup.service writes the freshness marker (reboot-durable)

- **host:** `rig` · **severity:** `warn` · **guards task:** `fix-30` · **enabled:** True
- **expects:** `MARKER_WRITER_PRESENT`

```bash
systemctl cat restic-backup.service | grep -q 'restic-mon/last-success' && echo MARKER_WRITER_PRESENT || echo MARKER_WRITER_MISSING
```

## `restic-marker-writer-mini`

mini restic-backup.service writes the freshness marker (reboot-durable)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-30` · **enabled:** True
- **expects:** `MARKER_WRITER_PRESENT`

```bash
systemctl cat restic-backup.service | grep -q 'restic-mon/last-success' && echo MARKER_WRITER_PRESENT || echo MARKER_WRITER_MISSING
```

## `verification-bin-refs-present`

verification: every check-referenced bin script is deployed

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-30` · **enabled:** True
- **expects:** `BIN_REFS_OK`

```bash
/opt/verification/bin/bin-refs-present.sh
```

## `daily-sweep-completed`

verification: previous daily sweep completed cleanly (not killed/overrun)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-61` · **enabled:** True
- **expects:** `^SWEEP_OK$`

```bash
r=$(systemctl show verification.service -p Result --value); ts=$(stat -c %Y /var/lib/verification/results.json 2>/dev/null || echo 0); age=$(( ( $(date +%s) - ts ) / 3600 )); if [ "$r" = success ] && [ "$age" -lt 26 ]; then echo SWEEP_OK; else echo "SWEEP_BAD result=$r results_age_h=$age"; fi
```

## `triage-verdicts-well-formed`

verify-04 LLM triage: newest run's verdicts are mostly well-formed (not fallbacks)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-61` · **enabled:** True
- **expects:** `^TRIAGE_WELLFORMED_OK`

```bash
/opt/verification/bin/triage-wellformed.py
```

## `verification-tree-macos-junk`

/opt/verification carries no ._*/.DS_Store artifacts

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-45` · **enabled:** True
- **expects:** `^0$`

```bash
find /opt/verification \( -name '._*' -o -name '.DS_Store' \) 2>/dev/null | wc -l
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
