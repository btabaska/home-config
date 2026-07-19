# Checks — media-aux

`foss-setup/verification/checks.d/media-aux.yaml` — 6 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `navidrome-backup-fresh`

navidrome: a backup file <26h old and >1MB exists in ./backup (M15)

- **host:** `mini` · **severity:** `crit` · **guards task:** `fix-37` · **enabled:** True
- **expects:** `^fresh_backups=[1-9][0-9]*$`

```bash
echo "fresh_backups=$(find /opt/stacks/navidrome/backup -name 'navidrome_backup_*.db' -mmin -1560 -size +1M 2>/dev/null | wc -l)"
```

## `navidrome-backup-armed`

navidrome: no 'Periodic backup is DISABLED' since container start (M15 class)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-37` · **enabled:** True
- **expects:** `^disabled_msgs=0$`

```bash
echo "disabled_msgs=$(docker logs navidrome 2>&1 | grep -ci 'backup is DISABLED')"
```

## `kometa-run-clean`

kometa: latest run logged 0 config/builder errors (M16 class)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-37` · **enabled:** True
- **expects:** `^kometa_run_errors=0$`

```bash
awk '/Starting .* Run/{n=NR} {l[NR]=$0} END{c=0; if(!n)n=1; for(i=n;i<=NR;i++) if(l[i] ~ /Config Error|Error: |\[ERROR\]|\[CRITICAL\]/ && l[i] !~ /\[DEBUG\]/ && l[i] !~ /Convert Warning/) c++; print "kometa_run_errors=" c}' /opt/stacks/kometa/config/logs/meta.log
```

## `pinchflat-pot-provider`

pinchflat: yt-dlp lists bgutil:http POT provider as available (M14)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-37` · **enabled:** True
- **expects:** `^bgutil:http-`

```bash
docker exec pinchflat sh -c 'yt-dlp -v --simulate --print id "https://www.youtube.com/watch?v=jNQXAC9IVRw" 2>&1 | grep -oE "bgutil:http-[0-9.]+ \(external\)" | head -1'
```

## `pinchflat-stuck-media`

pinchflat: no new bot-check-stranded media beyond the 7 accepted (M14 class)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-37` · **enabled:** True
- **expects:** `^new_botcheck_stuck=0$`

```bash
python3 -c "import sqlite3; c=sqlite3.connect('/opt/stacks/pinchflat/config/db/pinchflat.db'); print('new_botcheck_stuck=%d' % c.execute(\"select count(*) from media_items where last_error like '%Sign in to confirm%' and media_filepath is null and id not in (409,702,895,915,939,1008,1333)\").fetchone()[0])"
```

## `romm-content-ingest`

romm: NAS share content and DB rom count are consistent (M18 class)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-37` · **enabled:** True
- **expects:** `^ROMM_CONSISTENT`

```bash
mountpoint -q /mnt/share/Games || { echo GAMES_MOUNT_DOWN; exit 0; }; f=$(find /mnt/share/Games/romm -type f -not -path '*/#recycle/*' 2>/dev/null | wc -l); r=$(docker exec romm-db sh -c 'mariadb -u root -p"$MARIADB_ROOT_PASSWORD" romm -N -e "select count(*) from roms"' 2>/dev/null) || r=DB_ERR; if [ "$r" = "DB_ERR" ]; then echo "ROMM_DB_UNREACHABLE"; elif [ "$f" -gt 0 ] && [ "$r" -eq 0 ]; then echo "ROMM_CONTENT_NOT_INGESTED files=$f roms=0"; elif [ "$f" -eq 0 ] && [ "$r" -gt 0 ]; then echo "ROMM_LIBRARY_VANISHED files=0 roms=$r"; else echo "ROMM_CONSISTENT files=$f roms=$r"; fi
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
