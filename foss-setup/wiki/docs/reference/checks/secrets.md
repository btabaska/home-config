# Checks — secrets

`foss-setup/verification/checks.d/secrets.yaml` — 4 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `nas-health-env-perms`

health.env is root:root 600 (was 0777 with a live ntfy admin token)

- **host:** `nas` · **severity:** `crit` · **guards task:** `fix-23` · **enabled:** True
- **expects:** `^600 root:root$`

```bash
stat -c '%a %U:%G' /volume1/scripts/nas/health.env
```

## `nas-secret-file-perms`

no group/world-readable .env|config.ini|config.xml under /volume1/docker

- **host:** `nas` · **severity:** `crit` · **guards task:** `fix-23` · **enabled:** True
- **expects:** `^0$`

```bash
sh -c 'find /volume1/docker \( -name @eaDir -o -name "#recycle" \) -prune -o -type f \( -name "*.env" -o -name ".env" -o -name "config.ini" -o -name "config.xml" \) -perm /0044 -print 2>/dev/null | wc -l'
```

## `nas-worldwritable-sweep`

no world-writable files under /volume1/docker or /volume1/scripts

- **host:** `nas` · **severity:** `warn` · **guards task:** `fix-23` · **enabled:** True
- **expects:** `^0$`

```bash
sh -c 'find /volume1/docker /volume1/scripts \( -name @eaDir -o -name "#recycle" \) -prune -o ! -type l -perm -0002 -print 2>/dev/null | wc -l'
```

## `ntfy-anon-publish-denied`

ntfy denies anonymous publish to homelab-alerts (deny-all intact)

- **host:** `mini` · **severity:** `crit` · **guards task:** `fix-23` · **enabled:** True
- **expects:** `^403$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' -X POST -d probe https://ntfy.tabaska.us/homelab-alerts
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
