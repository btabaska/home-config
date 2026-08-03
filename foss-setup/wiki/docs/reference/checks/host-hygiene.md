# Checks — host-hygiene

`foss-setup/verification/checks.d/host-hygiene.yaml` — 10 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `ptero-lemp-retired`

pterodactyl LEMP stays retired: no packages, no artisan cron, no app dir (M1)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-39` · **enabled:** True
- **expects:** `^pkgs=0:cron=0:www=absent$`

```bash
echo "pkgs=$(dpkg -l 2>/dev/null | awk '$1=="ii"{print $2}' | grep -cE '^(nginx|php8\.3-fpm|mariadb-server|redis-server)$'):cron=$(sudo -n crontab -l 2>/dev/null | grep -c artisan):www=$([ -e /var/www/pterodactyl ] && echo present || echo absent)"
```

## `etckeeper-lock-races`

etckeeper dropped no /etc commit to an index.lock race in 24h (M2)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-39` · **enabled:** True
- **expects:** `^races=0$`

```bash
echo "races=$(journalctl -S -24h --no-pager 2>/dev/null | grep -cE 'etckeeper-serialized[^ ]*: fatal.*index\.lock|etckeeper.*code=exited, status=75')"
```

## `spent-enabled-timers`

no spent one-shot systemd timer is still enabled/active (M3 class)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-39` · **enabled:** True
- **expects:** `^SPENT_ENABLED=NONE$`

```bash
/opt/verification/bin/spent-timers.sh
```

## `cron-targets-exist`

every absolute-path cron command is an existing executable file (M62 class)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-39` · **enabled:** True
- **expects:** `^BROKEN_CRON=NONE$`

```bash
/opt/verification/bin/cron-target-sanity.sh
```

## `tv-share-no-ancient-leftovers`

tv-torrent share holds nothing older than 40 days (M62 consumer end)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-39` · **enabled:** True
- **expects:** `^stale=0$`

```bash
echo "stale=$(find /mnt/share/torrents/tv -mindepth 1 -maxdepth 1 -mtime +40 2>/dev/null | wc -l)"
```

## `tv-cleanup-timer-armed`

tv-torrent-cleanup.timer is enabled with a next fire scheduled

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-39` · **enabled:** True
- **expects:** `^enabled=enabled:next=scheduled$`

```bash
echo "enabled=$(systemctl is-enabled tv-torrent-cleanup.timer 2>/dev/null):next=$(systemctl list-timers tv-torrent-cleanup.timer --no-legend --plain | awk '{print ($1=="n/a")?"none":"scheduled"}')"
```

## `stacks-orphan-dirs`

/opt/stacks has no container-less dirs off-allowlist and no macOS junk

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-43` · **enabled:** True
- **expects:** `^orphans=NONE junk=NONE$`

```bash
allow=" backups wiki frigate recyclarr meme-review "; bad=""; wds=$(docker ps -a --format '{{.Label "com.docker.compose.project.working_dir"}}'); for d in /opt/stacks/*/; do n=$(basename "$d"); case "$allow" in *" $n "*) continue;; esac; echo "$wds" | grep -qxF "/opt/stacks/$n" || bad="$bad $n"; done; junk=$(find /opt/stacks -maxdepth 1 \( -name '._*' -o -name '.DS_Store' \) -print 2>/dev/null | tr '\n' ' '); echo "orphans=${bad:-NONE} junk=${junk:-NONE}"
```

## `mini-scratch-hygiene`

mini: no auth-material or aged scratch piling up in /tmp or the verification state dir (SL40/SL41)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-69` · **enabled:** True
- **expects:** `HYGIENE_OK$`

```bash
secrets=$(find /tmp -maxdepth 1 \( -name '*.cookies' -o -name '*cookies*.txt' -o -name '*.pem' -o -name 'id_*' \) 2>/dev/null | wc -l); scratch=$(find /tmp -maxdepth 1 -mtime +7 \( -type f -o -type d \) ! -path /tmp ! -name '.*-unix' ! -name 'systemd-private-*' ! -name 'tmux-*' 2>/dev/null | wc -l); stale=$(for f in /var/lib/verification/results-*.json; do case "$f" in *.streak.json) continue;; esac; python3 -c "import json,sys,datetime,os; t=json.load(open(sys.argv[1])).get('timestamp'); age=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(t).astimezone(datetime.timezone.utc)).days; print(os.path.basename(sys.argv[1])) if age>14 else None" "$f" 2>/dev/null; done | grep -c .); echo "secrets=$secrets scratch7d=$scratch staleresults14d=$stale"; [ "$secrets" -eq 0 ] && [ "$scratch" -le 10 ] && [ "$stale" -eq 0 ] && echo HYGIENE_OK || echo HYGIENE_DIRTY
```

## `unpackerr-host-retired`

mini: no host-level unpackerr unit/process/package (SL18 — NAS container is the real one)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-69` · **enabled:** True
- **expects:** `UNPACKERR_RETIRED$`

```bash
u=$(systemctl list-unit-files unpackerr.service --no-legend 2>/dev/null | grep -c .); p=$(pgrep -x unpackerr 2>/dev/null | grep -c .); k=$(dpkg -l unpackerr 2>/dev/null | awk '$1=="ii"' | grep -c .); echo "unit=$u proc=$p pkg=$k"; [ "$u" -eq 0 ] && [ "$p" -eq 0 ] && [ "$k" -eq 0 ] && echo UNPACKERR_RETIRED || echo UNPACKERR_BACK
```

## `mini-reboot-not-stale`

mini: no kernel/libc reboot pending across >45d uptime (SL7 — schedule it in the 4-7AM window)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-69` · **enabled:** True
- **expects:** `REBOOT_OK$`

```bash
if [ ! -e /var/run/reboot-required ]; then echo "reboot_pending=no uptime_days=0"; echo REBOOT_OK; else up=$(awk '{printf "%d", $1/86400}' /proc/uptime); echo "reboot_pending=yes uptime_days=$up"; [ "$up" -le 45 ] && echo REBOOT_OK || echo REBOOT_STALE; fi
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
