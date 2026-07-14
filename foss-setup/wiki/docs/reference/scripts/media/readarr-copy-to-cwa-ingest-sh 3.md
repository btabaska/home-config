# `readarr-copy-to-cwa-ingest.sh`

> Readarr Connect custom script — copy imported books to CWA ingest (Option A).

**Path:** `foss-setup/scripts/media/readarr-copy-to-cwa-ingest.sh` · **Category:** [Media pipeline](index.md) · **Type:** Bash

## What it does

```text
 Readarr Connect custom script — copy imported books to CWA ingest (Option A).
 Readarr keeps files in /readarr-library; CWA ingests copies from /cwa-book-ingest.
 Triggers: Connect → On Import, On Upgrade (not On Grab — paths do not exist yet).
 Env: readarr_addedbookpaths (| separated), readarr_eventtype (Test on dry-run).

 2026-07-13 BUGFIX (apostrophe drop): the old whitespace trim
   BOOK_PATH="$(echo "$BOOK_PATH" | xargs)"
 used xargs, which does shell-quote processing and CORRUPTS any path containing
 an apostrophe/quote — the NAS busybox xargs strips it ("Kushiel's Chosen" ->
 "Kushiels Chosen"), so the -f test failed and the book was silently dropped;
 every apostrophe title (all the Kushiel's/Naamah's books) never reached CWA
 while "Miranda and Caliban" (no apostrophe) did. Fixed with a pure-bash trim.
 Added a normalized-basename fallback search so ANY residual path-mangling still
 resolves the real file instead of dropping the book.
```

## Environment / variables referenced

`BOOK_ARRAY`, `BOOK_PATH`, `BOOK_PATHS`, `DEST_BOOK`, `DEST_DIR`, `LOGFILE`, `RAW`, `SRC_ROOT`

## See also

- [`flac-to-alac-inplace.sh`](flac-to-alac-inplace-sh.md)
- [`immich-go-import.sh`](immich-go-import-sh.md)
- [`install-ipod-tools-cachyos.sh`](install-ipod-tools-cachyos-sh.md)
- [`install-slskd-native.sh`](install-slskd-native-sh.md)
- [`nas-music-to-alac-mirror.sh`](nas-music-to-alac-mirror-sh.md)
- [`rclone-manual-copy.sh`](rclone-manual-copy-sh.md)
- [`rclone-seedbox-mount.sh`](rclone-seedbox-mount-sh.md)
- [`rclone-seedbox-watchdog.sh`](rclone-seedbox-watchdog-sh.md)
- [`seedbox-sync.sh`](seedbox-sync-sh.md)
- [`verify-tailscale-seedbox.sh`](verify-tailscale-seedbox-sh.md)
- [`window-maint-unpackerr-rclone.sh`](window-maint-unpackerr-rclone-sh.md)
- [Media pipeline scripts](index.md) · [All scripts](../index.md)
