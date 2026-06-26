# Camera SD → SSD → Immich import (immich-go)

**Phase 2.** How to get photos off a mirrorless camera's SD card into **Immich**
on the NAS. Unlike a phone (which auto-uploads to Immich), a **camera card has no
auto-backup** — you must copy the card off and import it deliberately. This doc
covers the workflow, installing **immich-go**, getting an API key, and the
**pbak** alternative. The import step itself is scripted in
[`immich-go-import.sh`](./immich-go-import.sh).

Docs: https://github.com/simulot/immich-go

---

## The workflow: SD → SSD → Immich

```
[camera SD card]  --copy-->  [SSD: dated ingest folder]  --immich-go-->  [Immich on NAS]
   originals                  your safety copy (keep!)        library + dedup
```

1. **SD → SSD (copy off first).** Insert the card and copy everything to a dated
   folder on a working SSD, e.g. `/mnt/ssd/ingest/2026-06-26/`. This is your
   originals safety copy — do this BEFORE touching Immich and before reformatting
   the card. A plain `rsync -a /media/<card>/DCIM/ /mnt/ssd/ingest/2026-06-26/`
   works; verify the copy completed before erasing the card.
2. **SSD → Immich (import).** Run the script against the copied folder:

   ```bash
   IMMICH_SERVER=https://photos.example.com \
   IMMICH_API_KEY=xxxxxxxx \
   CARD_PATH=/mnt/ssd/ingest/2026-06-26 \
     ./immich-go-import.sh
   ```

   It calls `immich-go upload from-folder --manage-raw-jpeg StackCoverJPG …`, so a
   **RAW+JPEG pair** shot together is **stacked as one asset** instead of two
   duplicates. Re-running is safe — immich-go dedups by **checksum** server-side,
   so already-uploaded photos are skipped.
3. **Keep the SSD copy** until you've confirmed everything is in Immich (and
   Immich itself is backed up — its `UPLOAD_LOCATION` is Tier-1 data, see
   `configs/nas/immich/`). Only then reformat the card.

> Tip: prefer a dated folder per card/shoot. It keeps imports idempotent and makes
> it obvious what's been ingested.

---

## Installing immich-go (release binary)

immich-go is a single static Go binary — no runtime deps. Grab the latest release
for your platform from the releases page and put it on your `PATH`:

```bash
# Linux x86_64 example — check the releases page for the current version/URL:
#   https://github.com/simulot/immich-go/releases
curl -L -o /tmp/immich-go.tar.gz \
  https://github.com/simulot/immich-go/releases/latest/download/immich-go_Linux_x86_64.tar.gz
tar -xzf /tmp/immich-go.tar.gz -C /tmp immich-go
sudo install -m 0755 /tmp/immich-go /usr/local/bin/immich-go
immich-go version
```

(macOS/Windows builds are on the same releases page. On macOS you can also
`brew install immich-go` if a tap is available.)

---

## Getting an Immich API key

1. Log into the Immich web UI.
2. **Account Settings → API Keys → New API Key**, name it (e.g. `immich-go`),
   create it, and copy the value (shown once).
3. Pass it as `IMMICH_API_KEY` to the script (or export it). Treat it like a
   password — it can upload to and read your library.

`IMMICH_SERVER` is the base URL of your Immich instance — your Caddy domain
(`https://photos.example.com`) or the direct LAN address (`http://<nas-ip>:2283`).

---

## Alternative: pbak (photographer's wrapper)

If you want a more opinionated, photographer-focused ingest, **pbak** wraps the
same SD → SSD → Immich idea with extra safety/organization:

- **EXIF date-sort** the copy off the card into a tidy date-based folder tree.
- **SHA-256 dedup** so you never copy/import the same frame twice across cards/shoots.
- **Integrity checks** (verify hashes after copy) so a flaky card/reader can't
  silently corrupt originals.
- Hands the organized copy to **immich-go** for the actual Immich upload.

Use plain `immich-go-import.sh` for the simple case; reach for **pbak** when you're
ingesting many cards and want EXIF-sorted, hash-verified originals on the SSD
before they ever hit Immich.
