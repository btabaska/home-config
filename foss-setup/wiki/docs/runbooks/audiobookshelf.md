# Audiobookshelf (audiobooks + podcasts)

Runbook for the `audiobookshelf-libraries-consumer` verification check and general
operation of Audiobookshelf on the NAS. Service page: [audiobookshelf](../services/audiobookshelf.md).

- **Host:** NAS (Synology DS920+, `192.168.10.4`), DSM Container Manager, project `audiobookshelf`
- **URL:** <https://abs.tabaska.us> (LAN `http://192.168.10.4:13378`)
- **Compose:** live `/volume1/docker/audiobookshelf/docker-compose.yml`; repo mirror `foss-setup/configs/nas/audiobookshelf/`
- **Image:** `ghcr.io/advplyr/audiobookshelf:2.35.1` (digest-pinned)
- **Secrets:** vault `audiobookshelf.{admin_user,admin_password,api_key}`, `homepage_widgets.audiobookshelf_key`; runner env `AUDIOBOOKSHELF_API_KEY`

## The consumer check

`audiobookshelf-libraries-consumer` (in `verification/checks.d/reading.yaml`) authenticates
with the long-lived API key and asserts `/api/libraries` returns both a **book** and a
**podcast** library AND that the Audiobooks library holds **≥1 item**. It is a consumer probe,
not a `/status` 200 — it fails on a revoked/expired key (401), a deleted library, an emptied
library, or the container being down.

Green looks like: `ABS_OK books=<n> podcasts=<m>`.

## Alert: check is red

1. **Is the container up?** `ssh nas` then `sudo /usr/local/bin/docker ps --filter name=audiobookshelf`.
   If it's restart-looping, check `sudo /usr/local/bin/docker logs audiobookshelf | tail`.
   - `listen EACCES … :80` → the non-root port trap. The compose must set `PORT=13378` (a
     non-root user can't bind port 80). Restore it and `docker compose up -d`.
2. **Does the API key still work?** From the mini runner:
   `curl -s -H "Authorization: Bearer $AUDIOBOOKSHELF_API_KEY" http://192.168.10.4:13378/api/libraries`.
   A `401`/`403` means the key was revoked or rotated — mint a new one (Settings > Users >
   API Keys, or `POST /api/api-keys`), then update **both** vault
   `homepage_widgets.audiobookshelf_key` / `audiobookshelf.api_key`, the mini
   `/etc/verification/env` `AUDIOBOOKSHELF_API_KEY`, and the homepage stack `.env`
   `HOMEPAGE_VAR_ABS_KEY` (restart homepage).
3. **`books=0`?** The Audiobooks library is empty. Add a book under
   `/volume1/audiobooks/<Author or Title>/…` and trigger a scan
   (`POST /api/libraries/<id>/scan`). Do not point the library at `/volume1/books` (that's the
   calibre ebook tree).

## Libraries & paths

- `Audiobooks` → `/volume1/audiobooks` (book type). MAM audiobooks land here.
- `Podcasts` → `/volume1/podcasts` (podcast type). ABS-managed episode downloads.
- Both dedicated trees are owned `1026:100`; ABS runs as `1026:100`, so SMB-dropped and
  ABS-written files stay co-owned. Never point a library at the *arr/calibre trees.

## Upgrades

```
ssh -t nas 'cd /volume1/docker/audiobookshelf && sudo /usr/local/bin/docker compose pull && sudo /usr/local/bin/docker compose up -d'
```

Then bump the tag+digest in `foss-setup/configs/nas/audiobookshelf/docker-compose.yml` to match
what was pulled and commit (repo↔live anti-drift).
