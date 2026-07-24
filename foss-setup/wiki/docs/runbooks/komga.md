# Komga (comics + manga reader)

Runbook for the `komga-libraries-consumer` verification check and general operation of Komga
on the NAS. Service page: [komga](../services/komga.md).

- **Host:** NAS (Synology DS920+, `192.168.10.4`), DSM Container Manager, project `komga`
- **URL:** <https://komga.tabaska.us> (LAN `http://192.168.10.4:25600`)
- **Compose:** live `/volume1/docker/komga/docker-compose.yml`; repo mirror `foss-setup/configs/nas/komga/`
- **Image:** `gotson/komga:1.25.0` (digest-pinned `@sha256:c4f9885f…`)
- **Runs as:** `1026:100` (btabaska:users), non-root; JVM heap capped `-Xmx1g` via `JAVA_TOOL_OPTIONS`
- **Libraries:** `Comics` → `/data/Comics`, `Manga` → `/data/Manga` (`/data` = `/volume1/comics`)
- **Secrets:** vault `komga.{admin_email,admin_password}`, `homepage_widgets.{komga_user,komga_pass}`; runner env `KOMGA_USER`/`KOMGA_PASS`

Komga has **no default account** — the first-run admin was created via the claim API
(`POST /api/v1/claim` with `X-Komga-Email`/`X-Komga-Password` headers). The server is now
claimed (`GET /api/v1/claim` → `{"isClaimed":true}`), so that flow won't run again.

## The consumer check

`komga-libraries-consumer` (in `verification/checks.d/reading.yaml`, helper
`verification/bin/komga-serves.py`) authenticates with the admin username/password (from the
runner env, never argv) and asserts: both the **Comics** and **Manga** libraries exist, **≥1
series** is indexed, a real **page streams** (HTTP 200 image bytes), and the **OPDS catalog**
responds. It is a consumer probe, not an `/actuator/health` 200 — it fails on changed/revoked
credentials (401), a deleted library, an empty/broken scan, or page-streaming being broken.

Green looks like: `KOMGA_OK libraries=2 series=<n> books=<m> page=200 opds=200`.

## Alert: check is red

1. **Is the container up?** `ssh nas` then `sudo /usr/local/bin/docker ps --filter name=komga`.
   Komga is a Spring-Boot JVM app — a cold start on the NAS J4125 takes ~2 minutes; the API
   refuses (HTTP 000) until `Started ApplicationKt` appears in
   `sudo /usr/local/bin/docker logs komga`.
2. **Do the credentials still work?** From the mini runner:
   `curl -s -u "$KOMGA_USER:$KOMGA_PASS" http://192.168.10.4:25600/api/v1/libraries`.
   A `401` means the admin password changed — update **both** vault
   `komga.admin_password` / `homepage_widgets.komga_pass`, the mini `/etc/verification/env`
   `KOMGA_PASS`, and the homepage stack `.env` `HOMEPAGE_VAR_KOMGA_PASS` (restart homepage).
3. **`missing-libraries`?** A library was deleted or renamed. Recreate it pointing at
   `/data/Comics` or `/data/Manga` (Server Settings > Libraries > Add), then scan.
4. **`series=0` / a dropped CBZ never appears?** Komga groups by folder — one folder per series
   under `/data/Comics` (or `/data/Manga`), CBZ/CBR files inside. Drop as
   `/volume1/comics/Comics/<Series>/<Issue>.cbz`, `sudo chown -R 1026:100 /volume1/comics`, then
   trigger a scan: `POST /api/v1/libraries/<id>/scan` (basic auth) or Libraries > (⋮) > Scan
   library files. Confirm the mount inside the container:
   `sudo /usr/local/bin/docker exec komga ls /data/Comics /data/Manga`.

## Libraries & paths

- `Comics` → `/data/Comics` — manually-acquired CBZ/CBR packs (IPT / GetComics).
- `Manga` → `/data/Manga` — the drop target that **read-18 (Suwayomi)** fills with volume CBZ.
- Both under `/volume1/comics`, owned `1026:100`; Komga runs as `1026:100` so SMB-dropped and
  Komga-written (thumbnails) files stay co-owned. Komga only reads the comics; its DB +
  thumbnails live in `/volume1/docker/komga/config`.

## Homepage tile

The `komga` widget uses a **username + password** (the admin email + password), not an API key
— vault `homepage_widgets.komga_user` / `komga_pass` → `.env` `HOMEPAGE_VAR_KOMGA_USER` /
`HOMEPAGE_VAR_KOMGA_PASS`. `url` is `http://192.168.10.4:25600` (raw NAS IP — Homepage runs on
the mini). After an `.env` change, restart the homepage container.

## Adding more users

The server is claimed; create additional users (read-only, per-person) in the UI under Server
Settings > Users, or `POST /api/v1/users` as admin. Roles like `KOREADER_SYNC`, `KOBO_SYNC`,
`PAGE_STREAMING`, `FILE_DOWNLOAD` gate per-client features.

## Upgrades

```
ssh -t nas 'cd /volume1/docker/komga && sudo /usr/local/bin/docker compose pull && sudo /usr/local/bin/docker compose up -d'
```

Then bump the tag+digest in `foss-setup/configs/nas/komga/docker-compose.yml` to match what was
pulled and commit (repo↔live anti-drift).

## Suwayomi — manga acquisition pipeline (read-18)

Komga's **Manga** library is fed by **Suwayomi** (Tachidesk) on the rig (stack
`configs/host/rig/suwayomi/`, `manga.tabaska.us`; like the other rig services it has no
generated service page — its detailed docs live in the compose header + service-enrichment).
The chain is:

```
Suwayomi (rig :4567)  ->  CBZ to /mnt/nas-manga (CIFS, rw)  ->  NAS /volume1/manga  ->  Komga /manga
```

The `suwayomi-feeds-komga` verification check (`warn`) walks this whole chain: Suwayomi's API
answers, the rig mount is writable, and Komga's Manga library has ≥1 indexed series.

**Manga library moved off `/volume1/comics`.** `/volume1/comics` is a plain directory DSM won't
export over SMB, so the rig can't write to it. read-18 created a dedicated **`manga` DSM shared
folder** (`/volume1/manga`) and re-homed Komga's Manga library onto `/manga` (compose bind
`- /volume1/manga:/manga`). Comics stays on `/volume1/comics`.

**If manga stop flowing** (check FAILs / new chapters don't appear):

1. Mount down? On the rig: `sudo mount /mnt/nas-manga && docker restart suwayomi`
   (persistent `_netdev,nofail` fstab entry; a boot-skipped `nofail` mount won't auto-retry).
   Verify: `ssh rig 'mountpoint -q /mnt/nas-manga && touch /mnt/nas-manga/.t && rm /mnt/nas-manga/.t && echo OK'`.
2. NAS ACL: `btabaska` needs full control on the share — `synoacltool -get /volume1/manga`
   should list `user:btabaska:allow:rwx…`.
3. CBZ on NAS but not in Komga? Force a scan: `POST /api/v1/libraries/<manga-lib-id>/scan`.

Full API recipes (install source, search, add, download) are in the Suwayomi compose header
(`configs/host/rig/suwayomi/compose.yaml`) and its `service-enrichment.yaml` troubleshoot entries.
