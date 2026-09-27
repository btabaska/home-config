# Kobo Forma sync failure — RCA + fix log (2026-09-27)

**Symptom:** Kobo Forma (192.168.10.183, fw 4.38.23697) failed every sync with
"Sync Failed. No Internet access." while the Kobo Sage (192.168.10.140, same fw)
synced fine against the identical CWA pipeline (books.tabaska.us → NAS :8083).

**Validation:** 9-agent workflow 2026-09-27 (read-only; live probes verified zero
DB delta): Caddy 46h-log forensics, in-container architecture check, app.db/metadata.db
forensics, patched `kobo.py` source review, NAS IO-history + kernel-log correlation,
edge/DNS rule-out + web research, live concurrency/egress/sync probes, 2 adversarial
skeptics. All F1–F10 findings and chain steps adjudicated; competing hypotheses
(store-proxy egress hang, Hardcover egress, rate limiter, SQLite lock contention,
idle-disk-slow code path, fw add-device 404, edge/DNS) individually refuted.

## Root cause (validated)

1. **Trigger:** the "S3 Backup enc" Hyper Backup ran **daily at 19:10 EDT**
   (~4.3h data phase + compaction/integrity to ~01:10; NOT Saturday-only as the
   08-23 audit assumed). Its writes froze /volume1 wide: kernel hung-task traces
   show dockerd/python3/postgres blocked >120s in `btrfs_commit_transaction`/fsync;
   100% of btrfs commit-trans warnings over 2 months land in local hours 19–22.
   Memory pressure co-factor (443MB free, 6.5GB swap; DSM "volume low performance
   due to insufficient memory" 2m42s after backup start).
2. **Amplifier:** CWA is ONE gevent WSGIServer process with **zero monkey-patching**
   — any blocked syscall stalls ALL requests (proved 3/3: a 5ms trivial request
   fired mid-sync completes within 0.9–1.6ms of the in-flight request finishing;
   cps.py main thread in D-state during stalls, ~260ms CPU per multi-second request).
   In-window even trivial endpoints (profile, initialization) hit ~29.9s; Uptime-Kuma's
   6.5ms-median books GET / hit 42–220s while every other vhost stayed <50ms.
3. **Client:** the Kobo aborts at ~30s (43/53 of the Forma's status-0s at 29.0–30.5s;
   Caddy status 0 = client hung up, Caddy has no proxy timeout; corroborated by CWA
   issue #1112) and shows the misleading "No Internet access" message, then retry-storms.
4. **Device asymmetry = schedule, not weight:** the Forma syncs evenings 19–23h EDT
   (inside the backup window) and failed; the Sage synced 17:14–18:34 EDT (ended 36
   min before backup start) and succeeded. The Forma itself synced in 1–2s at 16:29
   EDT both observed days. Residual: ~13% of Forma aborts are instant sub-second
   disconnects (device/Wi-Fi flake, Deviceos 4.1.15) — minor, device-side.
5. **Stranded book:** `add_synced_books` commits per-book *before* the client receives
   the response (kobo.py:307), so an aborted sync strands books permanently (the
   non-shelf sync branch filters solely by `notin_(kobo_synced_books)` — no timestamp
   re-inclusion). Book 115 (Practical Magic) was stranded for user 3 (kobo2).

## Fixes applied 2026-09-27 (~11:00 EDT)

1. **Backup rescheduled** — `.task` edits + `synoschedtask --sync` + crond restart
   (crontab verified regenerated): id=11 daily 19:10 → **01:10**; id=12 integrity
   Sat 21:10 → **Sat 08:10**. Mirrors + procedure: `configs/nas/hyperbackup/`.
   One-off ~30h backup gap (Sat 19:10 run → Mon 01:10 run) accepted.
2. **Stranded row deleted** (L1 procedure) — `app.db` backed up to
   `app.db.bak-kobo115-20260927` (sqlite `.backup`, 202-row sanity check), then
   `DELETE FROM kobo_synced_books WHERE id=239 AND user_id=3 AND book_id=115` (1 row).
   Eligibility re-computed read-only: user 3 is now offered exactly
   `[(115, 'Practical Magic')]`.
3. **Cover added to book 115** — it had NO cover at all (`has_cover=0`, the only
   book of 90; its cover endpoint served the static 8549B `generic_cover.svg`).
   Extracted the epub's embedded cover via `ebook-meta --get-cover`, set with
   `calibredb set_metadata --field cover:` (as `abc`). Verified: `has_cover=1`,
   `cover.jpg` 23,675B on disk, cover endpoint now returns `image/jpeg`.

**NOT done (deliberate):** no probe of `/v1/library/sync` with the kobo2 token after
the row delete — a sync GET *mutates* state and would re-strand book 115. The
re-delivery must come from the device itself.

## Verification still owed

- **Device-side:** sync the Forma any evening ≥19:30 EDT — expect success and
  Practical Magic appearing. If the row re-appears in `kobo_synced_books` but the
  book still doesn't display, the device has tombstoned the UUID → L2 procedure
  (change `books.uuid`, see memory `cwa-kobo-sync-quirks`).
- **`media-14` (tracker):** the daily `cwa-kobo-sync-consumer` check is a no-op —
  the env URLs are bare `/kobo/<token>` roots hitting TopLevelEndpoint (`{}` in
  0.07s); the sync path has never been monitored. Fix needs a dedicated monitor
  user/token (real device tokens must never probe sync) + a latency assertion.

## Open follow-ups surfaced by the RCA (not actioned)

- Hyper Backup logs `completes with result [1]` at `[err]` level nightly — chronic
  completing-with-errors, uninvestigated.
- Synology disk-latency collection (`/var/log/disk-latency/.SYNODISKLATENCYDB`)
  silently stopped 2026-09-22 — no per-interval disk metrics since.
- NAS memory pressure (6.5GB swap in use) worsens the backup-window IO stalls.
- Forma device flake (instant sub-second disconnects, old Deviceos 4.1.15) —
  device-side, worth a firmware/Wi-Fi look if failures persist off-window.
- Structural hardening (optional): CWA multi-worker / offloading long handlers so
  one slow request can't serialize the service; plain monkey-patching would NOT
  fix disk-IO blocking.
