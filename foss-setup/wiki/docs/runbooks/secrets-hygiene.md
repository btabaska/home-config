# Secrets hygiene

How credentials are stored, permissioned, and verified across the fleet — and what to
do when a secrets-hygiene verification check fires. Established by **fix-23**
(quality-gate 2026-07-16 findings M7, M26, M43, M44, M45, resolved 2026-07-17).

## The rules

1. **Every live credential lives in the vault.** `foss-setup/.handoff-secrets.yaml`
   (macbook only, gitignored, chmod 600) is the handoff source of truth. A service
   running with a credential that exists only in its on-host config is a
   disaster-recovery gap — that's how the Forgejo admin credential (the deploy
   control plane!) and the slskd/Soulseek credentials went unrecorded.
2. **Secret-bearing files on hosts are owner-only.** `.env`, `config.ini`,
   `config.xml` and friends are mode 600, owned by the user that consumes them
   (root:root for root-run scripts like `nas-docker-health.sh`).
3. **No world-writable files** under `/volume1/docker` or `/volume1/scripts` on the
   NAS. DSM share ACLs default new files to 0777 — assume drift and let the checks
   catch it.
4. **No plaintext secrets in iCloud-synced paths** outside the vault. The 15 GB
   `migration-snapshot/` (Plex token, API keys, indexer cookies) replicated to
   Apple's cloud for weeks before fix-23 deleted it.
5. **Intentionally empty vault keys are documented, not blank.** Add them to
   `ALLOW_EMPTY` in `vault-lint.py` with a reason.

## The guards

| Guard | Where it runs | What it catches |
|-------|---------------|-----------------|
| `vault-lint.py` | macbook, on every `publish-deploy.sh` | empty vault keys for live services (M26/M44/M45 class) |
| `nas-health-env-perms` | verification runner (mini→nas) | the exact M7 file regressing from root:root 600 |
| `nas-secret-file-perms` | verification runner | any group/world-readable secret file under `/volume1/docker` |
| `nas-worldwritable-sweep` | verification runner | any world-writable file (0777-drift class) |
| `ntfy-anon-publish-denied` | verification runner (mini) | ntfy `deny-all` regressing — what makes a token leak survivable |

Check definitions: `foss-setup/verification/checks.d/secrets.yaml`. Alerts land on the
ntfy `verification` topic via the runner.

## If a check fires

- **nas-health-env-perms** — something rewrote `/volume1/scripts/nas/health.env`
  (DSM update, manual edit). Restore: `chown root:root && chmod 600`. Template:
  `foss-setup/scripts/nas/health.env.example`.
- **nas-secret-file-perms / nas-worldwritable-sweep** — usually an app upgrade or DSM
  ACL default recreated a file 0777. Fix the listed file (`chmod 600` secrets,
  `chmod o-w` otherwise) via piped-vault sudo on the NAS. Re-run:
  `/opt/verification/bin/run-checks.sh --host nas`. If the offenders are under
  `/volume1/docker/mylar3` see the mylar3 note below. (These two do a full `find` over
  `/volume1/docker` — under NAS I/O saturation they can TIMEOUT rather than report an
  offender; confirm with the manual `find` before assuming a real regression.)
- **nas-mylar3-umask-guard** — the mylar3 container lost its `umask 077` entrypoint (a
  redeploy from an older compose, or someone editing it out). Restore the
  `entrypoint: ["/bin/sh","-c","umask 077; exec /init"]` line in
  `configs/nas/mylar3/docker-compose.yml`, push it live, and recreate the container.
  Without it a fresh `config.ini` is created 0644 (23 credential-class keys) instead of
  0600 — the fix-23 regression this task (fix-53) closed.
- **nas-ha-backup-acl** — a NAS group other than `administrators`/`ha-backup` regained
  write/delete on the `/volume1/backups` HA tars (usually someone re-saved the
  `backups` shared-folder permissions in DSM). Re-run
  `sudo bash /volume1/scripts/nas/harden-backups-acl.sh` (idempotent) to downgrade the
  offending groups back to read-only and re-enforce inheritance onto the tars.
- **ntfy-anon-publish-denied** — anonymous publish returned something other than 403.
  Check `NTFY_AUTH_DEFAULT_ACCESS=deny-all` in `/opt/stacks/ntfy/compose.yaml` on the
  mini; an open ntfy means alert topics can be spoofed and any leaked topic name is
  writable.
- **vault-lint failure on publish** — populate the key from the live host (never via
  chat/commits), or add a reasoned `ALLOW_EMPTY` entry.

## Token rotation cookbook (ntfy)

The 2026-07-17 rotation of the leaked `nas-health` token, reusable for any ntfy token:

```
# on mini — mint replacement (tokens belong to the admin user)
docker exec ntfy ntfy token add --label "<label>" admin
# update the consumer (e.g. /volume1/scripts/nas/health.env), test publish from it
# then revoke the old token and confirm it gets 401
docker exec ntfy ntfy token remove admin tk_<old>
```

Update the matching `ntfy.*` key in the vault. Note: all ntfy tokens are currently
attached to the **admin** user (read-write everything) — scoping per-topic publish
users is a known, deliberate follow-up, not yet done.

## History

- **2026-08-02 (fix-53):** the Jul 27 mylar3 (NAS) deploy reintroduced the fix-23
  class — `config.ini` 0644 with 23 credential-class keys (values empty, but
  `nas-secret-file-perms` crit-red) + five 0666/0777 cache/`.ComicTagger` files
  (`nas-worldwritable-sweep`). Root cause: the LSIO mylar3 image ignores the `UMASK`
  env var (its s6 run script execs mylar with no `umask`), and mylar itself calls
  `os.umask(0)` **without restoring it** (PostProcessor/filechecker) so after the first
  grab the process leaks to umask 0 and re-chmods cache 0666/0777. Fix: (1) PID-1 umask
  via the compose entrypoint (`umask 077; exec /init`) — secures `config.ini`'s create
  path (a fresh recreate now lands it 0600; the app rewrites it in-place so the mode
  holds); (2) every-15-min DSM task `scripts/nas/mylar3-perms-guard.sh` (id=16)
  re-secures the cache the umask can't. New guards: `nas-mylar3-umask-guard`. Separately
  (SM42) the `/volume1/backups` HA offsite tars granted rwx+**delete** to every NAS
  group (media/users/http/household/docker-service) via inheritable ACEs —
  `scripts/nas/harden-backups-acl.sh` downgraded them to read-only, keeping only
  `administrators` + `ha-backup`; guard `nas-ha-backup-acl`.
- **2026-07-17 (fix-23):** health.env 0777→600 + token rotated & revoked; ~all of
  `/volume1/docker` de-world-written; five *arr `config.xml` + `stash/.env` +
  `media-automation/.env` → 600; `soularr/config.ini.bak-wrong-path` junk removed;
  vault backfilled (soulseek×4, whisparr API key, Forgejo admin — password reset via
  container CLI); 15 GB `migration-snapshot/` deleted from iCloud; deluge.port was
  already corrected to 5945 by fix-21.

## NAS secret-file perms + check IO-robustness (fix-92, 2026-08-23)

The 2026-08-23 sweep found the fix-23 perms checks (`nas-secret-file-perms`,
`nas-worldwritable-sweep`) chronically TIMING OUT (exit 124 → false-CRIT) for 10+
days: their `find` walked the entire `/volume1/docker` tree (incl. deep data dirs),
>60s under NAS IO load. Note `ionice`/`nice` are NOT available on DSM.

Fixes:

- **IO-robust**: bounded the find to `-maxdepth 6` (the `<app>/config/<file>` depth
  where secrets live) → completes in ~0.05s. A genuine 45s timeout now degrades to
  `IO_DEFERRED` (safety-net pass), never a false-CRIT.
- **Filter broadened**: 0644 secret files escaped the old `.env`/`.ini`/`.xml`
  filter. Added `config.yaml`/`.yml`, `*.conf`, `settings.json`, `*.key`, while
  EXCLUDING public `*cert*.pem` (certs are meant to be world-readable; the private
  keys are `*.key`).
- **Real exposures fixed**: 7 world-readable secret configs were found + `chmod 600`:
  `stash/config/config.yml` (775), `bazarr/.../config.yaml`, `shelfmark/settings.json`,
  `calibre-web-automated/config/.key` (755), `beets/config.yaml`,
  `media-automation/unpackerr/unpackerr.conf` (arr keys, also sec-10),
  `scrutiny/influxdb/config.yaml`. `synoacltool -get` showed these have NO synoacl
  override, so they are POSIX-authoritative and `chmod 600` is effective (verified
  stash still serves after). Owner is the container UID (btabaska/root), so 600
  keeps app access.

Note on the `/volume1/docker` share root showing POSIX `0777`: that is the DSM
shared-folder synoacl display default — the actual synoacl grants `everyone`
**read+traverse only** (no write), so it is NOT world-writable (refuted 2026-08-23).
The real exposures were the world-readable FILES above, now fixed. Recurrence: if a
container rewrites a config with a lax umask (fix-53 mylar3 class), the hardened
check catches it fast — the durable cure is a per-container PID-1 `umask 077`.
