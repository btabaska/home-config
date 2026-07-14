# Checks — backups

`foss-setup/verification/checks.d/backups.yaml` — 5 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

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

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
