# Checks — lan-exposure

`foss-setup/verification/checks.d/lan-exposure.yaml` — 4 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `lan-listeners-drift-mini`

mini all-interface TCP listeners match the intended-exposure baseline (SM56/SM58)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-51` · **enabled:** True
- **expects:** `^LISTENER_DRIFT=NONE`

```bash
/opt/verification/bin/listener-drift.sh mini
```

## `lan-listeners-drift-rig`

rig all-interface TCP listeners match the intended-exposure baseline (SM58)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-51` · **enabled:** True
- **expects:** `^LISTENER_DRIFT=NONE`

```bash
/opt/verification/bin/listener-drift.sh rig
```

## `lan-listeners-drift-nas`

NAS all-interface TCP listeners match the intended-exposure baseline (SM58)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-51` · **enabled:** True
- **expects:** `^LISTENER_DRIFT=NONE`

```bash
/opt/verification/bin/listener-drift.sh nas
```

## `booklogr-registration-posture`

BookLogr registration posture recorded + container/.env agree (SM24)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-51` · **enabled:** True
- **expects:** `^BOOKLOGR_REG=(True|False) envfile=(True|False) match=yes$`

```bash
env=$(docker inspect booklogr-api --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null | grep -E '^AUTH_ALLOW_REGISTRATION=' | cut -d= -f2); dotenv=$(sudo -n grep -E '^AUTH_ALLOW_REGISTRATION=' /opt/stacks/booklogr/.env 2>/dev/null | cut -d= -f2); match=$([ "$env" = "$dotenv" ] && echo yes || echo no); echo "BOOKLOGR_REG=${env:-UNSET} envfile=${dotenv:-UNSET} match=$match"
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
