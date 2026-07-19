# Checks — verification-self

`foss-setup/verification/checks.d/verification-self.yaml` — 5 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

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

## `verification-tree-macos-junk`

/opt/verification carries no ._*/.DS_Store artifacts

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-45` · **enabled:** True
- **expects:** `^0$`

```bash
find /opt/verification \( -name '._*' -o -name '.DS_Store' \) 2>/dev/null | wc -l
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
