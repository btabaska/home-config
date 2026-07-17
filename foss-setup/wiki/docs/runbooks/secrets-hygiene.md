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
  `/opt/verification/bin/run-checks.sh --host nas`.
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

- **2026-07-17 (fix-23):** health.env 0777→600 + token rotated & revoked; ~all of
  `/volume1/docker` de-world-written; five *arr `config.xml` + `stash/.env` +
  `media-automation/.env` → 600; `soularr/config.ini.bak-wrong-path` junk removed;
  vault backfilled (soulseek×4, whisparr API key, Forgejo admin — password reset via
  container CLI); 15 GB `migration-snapshot/` deleted from iCloud; deluge.port was
  already corrected to 5945 by fix-21.
