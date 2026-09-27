# Hyper Backup DSM scheduled tasks (NAS)

Mirrors of `/usr/syno/etc/synoschedule.d/root/{11,12}.task` — the DSM Task Scheduler
entries that drive the off-site "S3 Backup enc" Hyper Backup (task 3):

| file | task | schedule | command |
|------|------|----------|---------|
| `11.task` | id=11 daily data backup | **01:10 EDT daily** | `dsmbackup --backup 3` |
| `12.task` | id=12 weekly integrity check | **Sat 08:10 EDT** | `detect_monitor -t -k 3 -f -T -1` |

## 2026-09-27 reschedule (Kobo sync RCA)

Both tasks used to run in the evening (daily 19:10, Sat 21:10). The daily backup's
~4.3h data phase froze /volume1 (btrfs `commit_transaction`/fsync stalls >120s,
kernel hung-task traces on dockerd/python3/postgres), which stalled CWA's single
gevent event loop server-wide and made the Kobo Forma abort every sync at its ~30s
client timeout ("Sync Failed. No Internet access"). Moved to 01:10 / Sat 08:10 to
clear the evening reading window. Full RCA: `foss-setup/docs/kobo-sync-rca-2026-09-27.md`.

## How to change these schedules

DSM regenerates `/etc/crontab` from the `.task` files — never edit crontab directly.
Procedure (as used for the reschedule):

```sh
sudo sed -i 's/^run hour=19$/run hour=1/' /usr/syno/etc/synoschedule.d/root/11.task
sudo /usr/syno/bin/synoschedtask --sync     # syncs the task store
sudo systemctl restart crond                # regenerates /etc/crontab from the store
grep 'id=11' /etc/crontab                   # verify the new line
```

Note: `synoschedtask --sync` alone does NOT rewrite `/etc/crontab`; the crond
restart is what regenerates it. Editing the schedule from the Hyper Backup UI
would also rewrite these `.task` files — re-mirror here if that happens.
