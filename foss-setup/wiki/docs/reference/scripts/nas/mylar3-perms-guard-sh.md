# `mylar3-perms-guard.sh`

> run ON the nas (Synology DS920+) as root (DSM task id=16,

**Path:** `foss-setup/scripts/nas/mylar3-perms-guard.sh` · **Category:** [NAS tasks](index.md) · **Type:** Bash

## What it does

```text
 mylar3-perms-guard.sh — run ON the nas (Synology DS920+) as root (DSM task id=16,
 every 15 min). fix-53 (fleet-sweep 2026-08-02, findings SM2/SM3): the Jul 27 mylar3
 deploy reintroduced the fix-23 file-permission failure class on the NAS.

 ROOT CAUSE (why a one-off chmod is not enough): mylar3 (github.com/mylar3/mylar3)
 calls os.umask(0) WITHOUT restoring it in PostProcessor.py and filechecker.py
 (e.g. filechecker.py:1917/1946 "this is probably redundant, but it doesn't hurt to
 clear the umask here"), so after the first grab/tag the whole mylar process runs at
 umask 0 and every file/dir it then creates under /config/mylar/cache and
 /config/mylar/.ComicTagger lands 0666/0777 (world-writable). Some paths are also
 hard-chmod'd 0777 (cmtagmylar.py:55, webviewer.py:137). The container entrypoint
 umask (compose) fixes config.ini's CREATE path but is DEFEATED by these os.umask(0)
 leaks for the cache — so this guard periodically re-secures the tree.

 config.ini itself (23 credential-class keys) is written IN-PLACE by configparser, so
 once it is 0600 the app's rewrites preserve the mode; we still re-assert it here as
 defense-in-depth (a fresh recreate would create it 0600 via the entrypoint umask).

 Anti-drift: mirrored in foss-setup/scripts/nas/. Installed by
 install-mylar3-perms-guard-task.sh (writes 16.task — never edit /etc/crontab on DSM).
 Re-greens verification checks nas-secret-file-perms (crit) + nas-worldwritable-sweep.
```

## Environment / variables referenced

`CFG_ROOT`, `CONFIG_INI`, `PGID`, `PUID`

## See also

- [`apply-compose-restart-policy.sh`](apply-compose-restart-policy-sh.md)
- [`empty-recycle-30d.sh`](empty-recycle-30d-sh.md)
- [`ensure-navidrome-music-ignore.sh`](ensure-navidrome-music-ignore-sh.md)
- [`harden-backups-acl.sh`](harden-backups-acl-sh.md)
- [`immich-db-dump.sh`](immich-db-dump-sh.md)
- [`immich-pg-dump.sh`](immich-pg-dump-sh.md)
- [`import-seedbox-roms.sh`](import-seedbox-roms-sh.md)
- [`install-beets-task.sh`](install-beets-task-sh.md)
- [`install-immich-dump-task.sh`](install-immich-dump-task-sh.md)
- [`install-kiwix-refresh-task.sh`](install-kiwix-refresh-task-sh.md)
- [`install-mylar3-perms-guard-task.sh`](install-mylar3-perms-guard-task-sh.md)
- [`install-nas-docker-health-task.sh`](install-nas-docker-health-task-sh.md)
- [NAS tasks scripts](index.md) · [All scripts](../index.md)
