# calibre-web-automated

Calibre-Web-Automated (CWA) on Synology DS920+ (Container Manager / Docker Compose)

| | |
|---|---|
| **Host** | [nas](../hosts/nas.md) |
| **URL** | https://books.tabaska.us |
| **Source** | `foss-setup/configs/nas/calibre-web-automated/docker-compose.yml` |
| **Notes** | Ebook library (CWA). |
| **Upstream docs** | <https://github.com/new-usemame/Calibre-Web-NextGen/releases/tag/v4.0.7> |

## About

Calibre-Web-Automated (CWA) is the ebook library and reading server running as the `calibre-web-automated` container on the Synology NAS (`192.168.10.4`), pinned to the community fork `ghcr.io/new-usemame/calibre-web-nextgen:v4.0.7` (the fork carries the CVE-2026-7713 Kobo auth-token IDOR fix that never shipped to the upstream `crocodilestick/calibre-web-automated` Docker Hub image, which stops at v4.0.6). Supply-chain posture (fix-38/I68, assessed 2026-07-18): the fork account is young and pseudonymous (created 2025-12, name reads like 'new-username' with an rn→m swap), so the image is pinned by sha256 DIGEST in the compose file — the tag alone is mutable and must never be trusted; the `cwa-image-digest-pinned` + `cwa-ghcr-tag-digest-drift` checks alert if the pin is dropped or the remote tag is re-pointed, and `cwa-upstream-cve-catchup` alerts when upstream ships a ≥4.0.7 release (the signal to migrate back off the fork). It auto-ingests ebooks dropped into `/volume1/docker/calibre-web-automated/ingest` (mounted `/cwa-book-ingest`, where Readarr's Connect script deposits imports) into the Calibre library at `/volume1/books` (mounted `/calibre-library`, holding `metadata.db`), and serves the web UI, OPDS, Kobo sync, and KOSync on `:8083`. Kobo store passthrough (`config_kobo_proxy` in `app.db`) is intentionally ENABLED — it carries the Kobo OAuth flow; a 2026-07-09 disable (after a kobo2 sync stall) was silently reverted by the same-day redeploy, the stall never recurred, and the ENABLED state was accepted as intent on 2026-07-18 (fix-38/M35, guarded by `cwa-kobo-proxy-intent`). It runs `PUID=1026`/`PGID=100` to match the DSM `btabaska:users` owner of the volumes, and is kept LAN/Tailscale-only (never a raw public `:8083`); the public `https://books.tabaska.us` name is fronted via the reverse-proxy/Tailscale path. The live container and the compose file both run `NETWORK_SHARE_MODE=false` (reconciled fix-38): the CIFS/SMB inotify watcher is unreliable, so ingest is instead driven by a scheduled/manual Library Refresh. Ingest dedupe (media-08, 2026-07-20): `auto_ingest_automerge` in `cwa.db` is set to `overwrite`, so a Readarr re-import/upgrade of a book CWA already holds merges into the existing record (same book id, file replaced) instead of minting a duplicate entry — the Connect script itself cannot dedupe because the readarr container can't see the CWA library; the setting lives in a runtime DB no compose file owns and is guarded against drift by `cwa-ingest-automerge-guard`.

## Containers

| Service | Image (pinned) | Ports |
|---|---|---|
| `calibre-web-automated` | `ghcr.io/new-usemame/calibre-web-nextgen:v4.0.7@sha256:89899edd457562e54767ced2499bce563533b2b47b14467822b127ee83072557` | `8083:8083` |

## Volumes

| Service | Volume |
|---|---|
| `calibre-web-automated` | `/volume1/docker/calibre-web-automated/config:/config` |
| `calibre-web-automated` | `/volume1/docker/calibre-web-automated/ingest:/cwa-book-ingest` |
| `calibre-web-automated` | `/volume1/books:/calibre-library` |

## Troubleshooting

- **After a redeploy, the flaky CIFS inotify watcher is unexpectedly active (NETWORK_SHARE_MODE came up true).** — The compose file (live and repo mirror) declares the live-correct NETWORK_SHARE_MODE=false since fix-38; if the watcher is active, someone edited it back. Verify with: ssh nas then `sudo /usr/local/bin/docker inspect calibre-web-automated --format '{{range .Config.Env}}{{println .}}{{end}}' | grep NETWORK_SHARE_MODE`, and restore `false` in /volume1/docker/calibre-web-automated/docker-compose.yml + the repo mirror.
- **An ebook sits in the ingest folder and is never imported into the library.** — Because the inotify watcher is off (NETWORK_SHARE_MODE=false), ingest relies on Library Refresh. Click Library Refresh in the CWA navbar (or wait for the scheduled refresh). Confirm the file landed in `/volume1/docker/calibre-web-automated/ingest` (owner btabaska:users) and is a completed file, not a partial download.
- **Kobo sync fails to authenticate or drops on a large library.** — Kobo uses per-device CWA users and the store-passthrough must stay ON (it carries the OAuth flow) — do not disable it. For big libraries, use SYNC_ITEM_LIMIT to batch. Kobo sync is only safe on v4.0.7+ (CVE-2026-7713 fixed); if ever falling back to crocodilestick/...:v4.0.6, disable Kobo sync.
- **Never accidentally publish CWA on a raw public :8083.** — Keep :8083 LAN/Tailscale-only. Access is via LAN http://192.168.10.4:8083 or Tailscale; the public https://books.tabaska.us is proxied, not a direct port exposure.
- **Author/series views split on the Kobo (same author listed twice), duplicate titles, or unwanted foreign-language editions appear after bulk grabs.** — Bulk grabs import whatever author-string and edition the source carried ('Colfer, Eoin' vs 'Eoin Colfer', 'George R.R. Martin' vs 'George R. R. Martin', FR/RO/ES editions). Clean up with calibredb inside the container (run as abc so file ownership stays 1026:100): `sudo /usr/local/bin/docker exec -u abc calibre-web-automated calibredb set_metadata --with-library /calibre-library --field authors:"Canonical Name" <id>` merges an identity (calibre moves the dirs itself); export-then-remove unwanted editions with `calibredb export` + `calibredb remove --permanent`. ALWAYS `cp /volume1/books/metadata.db` somewhere first. The daily `cwa-library-author-split` / `cwa-library-covers` checks catch the class recurring; root-cause prevention for foreign editions is Readarr edition pinning (anyEditionOk=false), and for straight re-import duplicates it is `auto_ingest_automerge=overwrite` (media-08) — note automerge matches title+author EXACTLY, so punctuation variants (curly vs straight apostrophe) still slip through to the detection checks.

## Operations

```bash
# NAS stack — manage via DSM Container Manager (project: calibre-web-automated)
# or over SSH (sudo required): cd /volume1/docker/calibre-web-automated && sudo docker compose ps
```

Update procedure: [Runbooks → Update images](../runbooks/update-images.md). Full add/change loop: [Runbooks → Add a service](../runbooks/add-a-service.md).

*Generated by `scripts/docs/gen-wiki-services.py` — do not edit by hand; edit the compose file and regenerate.*
