# Checks — backups

`foss-setup/verification/checks.d/backups.yaml` — 13 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `backup-immich-dump-fresh`

immich DB dump on NAS newer than 26h

- **host:** `nas` · **severity:** `crit` · **guards task:** `nas-08` · **enabled:** True
- **expects:** `\.sql\.gz`

```bash
find /volume1/docker/immich/backups -name '*.sql.gz' -mmin -1560 | grep .
```

## `restic-snapshot-fresh-mini`

restic B2 snapshot for mini newer than 26h

- **host:** `mini` · **severity:** `crit` · **guards task:** `nas-04` · **enabled:** True
- **expects:** `^FRESH`

```bash
sudo -n /usr/local/bin/restic-latest-age
```

## `restic-snapshot-fresh-rig`

restic B2 snapshot for rig newer than 26h

- **host:** `rig` · **severity:** `warn` · **guards task:** `nas-05` · **enabled:** True
- **expects:** `^FRESH`

```bash
sudo -n /usr/local/bin/restic-latest-age
```

## `backup-immich-dump-nonempty`

newest immich DB dump is >1MB (not a truncated/empty dump)

- **host:** `nas` · **severity:** `warn` · **guards task:** `nas-08` · **enabled:** True
- **expects:** `\.sql\.gz`

```bash
find /volume1/docker/immich/backups -name '*.sql.gz' -size +1M | grep .
```

## `nas-hyperbackup-b2-fresh`

NAS Tier-1 Hyper Backup -> B2 succeeded within 50h

- **host:** `nas` · **severity:** `crit` · **guards task:** `nas-02` · **enabled:** True
- **expects:** `^tok=ok$`

```bash
find /volume1/@img_bkp_cache/ClientCache_cloud_image_aws_s3.*/last_version_inodedb -mmin -3000 2>/dev/null | grep -q . && echo tok=ok || echo tok=BAD
```

## `b2-restic-immutable`

bucket-restic is actually immutable (retention + live delete refused 401)

- **host:** `mini` · **severity:** `crit` · **guards task:** `fix-22` · **enabled:** True
- **expects:** `^IMMUTABLE`

```bash
python3 /opt/verification/bin/b2-bucket-guard.py --immutable
```

## `b2-bucket-policy`

B2 account bucket set + lock/lifecycle policy match the manifest

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-22` · **enabled:** True
- **expects:** `^POLICY-OK`

```bash
python3 /opt/verification/bin/b2-bucket-guard.py --policy
```

## `restic-snapshot-hygiene-mini`

mini restic repo: no synthetic-host/test junk snapshots

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-22` · **enabled:** True
- **expects:** `^HYGIENE-OK`

```bash
sudo -n /usr/local/bin/restic-snapshot-hygiene
```

## `restic-snapshot-hygiene-rig`

rig restic repo: no synthetic-host/test junk snapshots

- **host:** `rig` · **severity:** `warn` · **guards task:** `fix-22` · **enabled:** True
- **expects:** `^HYGIENE-OK`

```bash
sudo -n /usr/local/bin/restic-snapshot-hygiene
```

## `restic-role-matches-source-mini`

mini restic deployment byte-matches roles/backup source (no drift, no no-op)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-42` · **enabled:** True
- **expects:** `^RESTIC-ROLE-OK$`

```bash
S=$HOME/.ansible-pull/foss-setup/scripts/backup; T=OK; cmp -s "$S/restic-backup.sh" /opt/scripts/restic-backup.sh || T=DRIFT-restic-backup.sh; cmp -s "$S/ntfy-notify.sh" /opt/scripts/ntfy-notify.sh || T=DRIFT-ntfy-notify.sh; cmp -s "$S/pre-backup-db-dumps.sh" /opt/scripts/pre-backup-db-dumps.sh || T=DRIFT-pre-backup; cmp -s "$S/restic-backup.service" /etc/systemd/system/restic-backup.service || T=DRIFT-service; cmp -s "$S/restic-backup.timer" /etc/systemd/system/restic-backup.timer || T=DRIFT-timer; cmp -s "$S/ntfy-notify@.service" /etc/systemd/system/ntfy-notify@.service || T=DRIFT-ntfy-unit; cmp -s "$S/restic-backup-healthchecks.conf" /etc/systemd/system/restic-backup.service.d/healthchecks.conf || T=DRIFT-dropin; cmp -s "$S/restic-latest-age.sh" /usr/local/bin/restic-latest-age || T=DRIFT-latest-age; cmp -s "$S/restic-snapshot-hygiene.sh" /usr/local/bin/restic-snapshot-hygiene || T=DRIFT-hygiene; systemctl is-enabled --quiet restic-backup.timer || T=TIMER-DISABLED; ! dpkg -s restic >/dev/null 2>&1 || T=APT-RESTIC-PRESENT; v=$(restic version 2>/dev/null | awk '{print $2}'); [ "$(printf '0.19.1\n%s\n' "$v" | sort -V | head -1)" = "0.19.1" ] || T=RESTIC-OLD-$v; echo "RESTIC-ROLE-$T"
```

## `restic-role-matches-source-rig`

rig restic deployment byte-matches roles/backup source (no drift, no no-op)

- **host:** `rig` · **severity:** `warn` · **guards task:** `fix-42` · **enabled:** True
- **expects:** `^RESTIC-ROLE-OK$`

```bash
S=$HOME/.ansible-pull/foss-setup/scripts/backup; T=OK; cmp -s "$S/restic-backup.sh" /opt/scripts/restic-backup.sh || T=DRIFT-restic-backup.sh; cmp -s "$S/ntfy-notify.sh" /opt/scripts/ntfy-notify.sh || T=DRIFT-ntfy-notify.sh; cmp -s "$S/restic-backup.service" /etc/systemd/system/restic-backup.service || T=DRIFT-service; cmp -s "$S/restic-backup.timer" /etc/systemd/system/restic-backup.timer || T=DRIFT-timer; cmp -s "$S/ntfy-notify@.service" /etc/systemd/system/ntfy-notify@.service || T=DRIFT-ntfy-unit; cmp -s "$S/restic-backup-healthchecks.conf" /etc/systemd/system/restic-backup.service.d/healthchecks.conf || T=DRIFT-dropin; cmp -s "$S/restic-latest-age.sh" /usr/local/bin/restic-latest-age || T=DRIFT-latest-age; cmp -s "$S/restic-snapshot-hygiene.sh" /usr/local/bin/restic-snapshot-hygiene || T=DRIFT-hygiene; systemctl is-enabled --quiet restic-backup.timer || T=TIMER-DISABLED; v=$(restic version 2>/dev/null | awk '{print $2}'); [ "$(printf '0.19.1\n%s\n' "$v" | sort -V | head -1)" = "0.19.1" ] || T=RESTIC-OLD-$v; echo "RESTIC-ROLE-$T"
```

## `ansible-site-converged-mini`

site.yml --check on mini: changed=0 failed=0 (live == ansible source)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-42` · **enabled:** True
- **expects:** `changed=0\s+unreachable=0\s+failed=0`

```bash
cd $HOME/.ansible-pull/foss-setup/configs/ansible && ansible-playbook -i inventory.ini --connection local --limit macmini --check site.yml 2>&1 | grep -E '^macmini' | tail -1
```

## `ansible-pull-ok-rig`

ansible-pull last run on rig succeeded (DR convergence loop alive)

- **host:** `rig` · **severity:** `crit` · **guards task:** `fix-42` · **enabled:** True
- **expects:** `^ExecMainStatus=0$`

```bash
systemctl show ansible-pull.service -p ExecMainStatus
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
