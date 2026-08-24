# Checks — secrets

`foss-setup/verification/checks.d/secrets.yaml` — 7 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

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

## `nas-mylar3-umask-guard`

mylar3 container entrypoint sets umask 077 (fix-53 structural fix intact)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-53` · **enabled:** True
- **expects:** `^umask=set$`

```bash
ep=$(printf '%s\n' "$NAS_SUDO_PASSWORD" | ssh -o BatchMode=yes -o ConnectTimeout=10 nas "sudo -S -p '' /usr/local/bin/docker inspect mylar3 --format '{{json .Config.Entrypoint}}'" 2>/dev/null); echo "$ep" | grep -q 'umask 077' && echo umask=set || echo "umask=MISSING ep=${ep:-inspect_failed}"
```

## `nas-ha-backup-acl`

HA offsite backup tars: only administrators/ha-backup can write/delete (SM42)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-53` · **enabled:** True
- **expects:** `^backup_open_write_aces=0$`

```bash
n=$(printf '%s\n' "$NAS_SUDO_PASSWORD" | ssh -o BatchMode=yes -o ConnectTimeout=10 nas "sudo -S -p '' sh -c 'F=\$(ls -1t /volume1/backups/*.tar 2>/dev/null | head -1); /usr/syno/bin/synoacltool -get /volume1/backups; [ -n \"\$F\" ] && /usr/syno/bin/synoacltool -get \"\$F\"'" 2>/dev/null | grep -Ec 'group:(media|users|http|household|docker-service):allow:rwxpdD'); echo "backup_open_write_aces=${n:-query_failed}"
```

## `repo-secret-scan-clean`

no secret-shaped strings in pushed origin/main (fix-84 recurrence monitor)

- **host:** `mini` · **severity:** `crit` · **guards task:** `fix-84` · **enabled:** True
- **expects:** `^SECRETS-CLEAN`

```bash
cd /opt/foss-setup 2>/dev/null && git fetch -q origin main 2>/dev/null; hits=$(git -C /opt/foss-setup grep -I -n -E 'tk_[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}' origin/main -- . ':!*.example' ':!*unpackerr.conf' 2>/dev/null | grep -vi redacted | wc -l | tr -d ' '); if [ "${hits:-1}" -eq 0 ]; then echo "SECRETS-CLEAN pushed origin/main pattern-scan 0 hits"; else echo "SECRETS-FOUND $hits secret-shaped string(s) in origin/main"; fi
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
