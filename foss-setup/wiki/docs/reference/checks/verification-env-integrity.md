# Checks — verification-env-integrity

`foss-setup/verification/checks.d/verification-env-integrity.yaml` — 2 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `verification-env-source-clean`

sec-12: /etc/verification/env sources clean — no unquoted/multi-line value executes or leaks (regression + class guard)

- **host:** `mini` · **severity:** `crit` · **guards task:** `sec-12` · **enabled:** True
- **expects:** `^ENV_SOURCE_CLEAN$`

```bash
out=$({ set -a; . /etc/verification/env; set +a; } 2>&1); rc=$?; if [ "$rc" -eq 0 ] && ! printf '%s' "$out" | grep -q 'command not found'; then echo ENV_SOURCE_CLEAN; else echo "ENV_SOURCE_DIRTY rc=$rc"; fi
```

## `mini-onfailure-ntfy-delivers`

sec-12: mini OnFailure ntfy paging delivers end-to-end (publish + read-back on the backups topic)

- **host:** `mini` · **severity:** `crit` · **guards task:** `sec-12` · **enabled:** True
- **expects:** `^NTFY_DELIVERY_OK$`

```bash
N="sec12chk-$(date +%s)-$$"; B="${NTFY_URL%/*}"; S=$(date +%s); curl -fsS -m 10 -H "Authorization: Bearer $NTFY_TOKEN" -H "Priority: min" -H "Tags: test_tube" -H "Title: sec-12 paging self-test" -d "$N" "$B/backups" >/dev/null || { echo NTFY_PUBLISH_FAIL; exit 0; }; for i in 1 2 3 4 5 6; do curl -fsS -m 8 -H "Authorization: Bearer $NTFY_TOKEN" "$B/backups/json?poll=1&since=$S" 2>/dev/null | grep -q "$N" && { echo NTFY_DELIVERY_OK; exit 0; }; sleep 1; done; echo NTFY_DELIVERY_FAIL
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
