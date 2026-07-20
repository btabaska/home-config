# Books-stack deep scan — 2026-07-19/20

Read-only investigation of the end-to-end ebook pipeline after the failed 2026-07-18 end-to-end
test (`ebook-06`). Four parallel evidence passes: Libreseerr (mini), Readarr (NAS), seedbox/deluge
+ transport, CWA/Kobo (NAS). **No live state was changed during the scan.**

Pipeline under test:
`Libreseerr (mini :8789) → Readarr (nas :8787) → Deluge (seedbox, label readarr) →
rclone SFTP mount /volume1/mounts/seedbox-files → Readarr import → /readarr-library →
Connect script → /cwa-book-ingest → CWA → /volume1/books → Kobo web sync`

Work items: **`fix-46`** (B1–B3), **`fix-47`** (B4–B7), **`fix-48`** (B8–B12). Reported symptoms →
findings: "downloads French versions" → B1/B2/B3 (+B4 for English files *filed as* French);
"books didn't reach Kobo sync" → B4/B5 (+ historical H-A/H-B below, already fixed); "dozens of
errored requests in Libreseerr" → B8/B9/B10/B11 (13 of 18 requests errored, 2 stuck forever).

Reference state at scan time: Readarr 0.4.18.2805, 432 books / 11 monitored / 2 monitored-no-file,
queue empty, `/health` empty, 0 downloadFailed all-time. Libreseerr container up, live files ==
repo (zero drift), reconciler running at 900 s. Deluge: 391 torrents, 9 readarr-labeled, all
finished + relabeled `readarr-imported`. Mount healthy (watchdog ok-marker fresh, fail-count 0).
CWA: ingest dir empty/idle, 68/68 `cwa_import` rows successful, Kobo device kobo2 synced 54/54
current books (last check-in 2026-07-19 22:53 UTC).

---

## Cluster 1 — French / wrong-edition class (`fix-46`)

> **RESOLVED 2026-07-20 (fix-46).** 8 unmonitored foreign records deleted (138/139/150/
> 166/167/175/194/201 — 2 more than the scan found: 150 "La má del rei", 167 "Le Bûcher
> d'un roi"); 261/263 repaired by pinning their English editions (*Kushiel's Justice* /
> *Kushiel's Mercy*, `anyEditionOk=false`) — delete+re-add was rejected because
> rreading-glasses would likely re-serve the French edition as canonical. Release
> profile id=1 now blocks foreign markers at grab time (regex enforcement verified
> live); libreseerr sends `anyEditionOk: False` on every add. Root-cause addendum:
> rreading-glasses stamps foreign editions `language=eng`, so `allowedLanguages` can
> never catch this class — kept at `eng, null` by operator decision. Checks
> `readarr-foreign-records` / `readarr-foreign-grab-history` / `books-language-guard`
> green. Runbook: `wiki/docs/runbooks/books-language.md`. Left for fix-47: file 69
> (261's epub) + file 66 (263's misfiled *Kushiel's Avatar* content) still linked to
> the unmonitored French editions — re-link via ManualImport during the B4 repair.

### B1 (high, nas) — French/foreign edition records enter the Readarr library as canonical books

rreading-glasses (Goodreads-proxy metadata) supplies foreign editions/works as book records.
Live library today contains French-titled records: ids **138** "L'invincible forteresse", **139**
"L'ombre maléfique", **166** "La bataille des rois", **175** "Le trône de fer", and — **monitored**
— **261** "La Justice de Kushiel: Imriel, T2", **263** "La Grâce de Kushiel: Imriel, T3".
The only language control in the whole chain is metadata profile id=1 "Standard"
`allowedLanguages: "eng, null"` — applied at metadata refresh, and `null` admits any edition with
no language tag; it demonstrably did not keep these out.

Consequence (2026-06-28, evidence in `/api/v1/history`): auto-search ran on the French titles and
*correctly* grabbed 6 genuinely foreign releases from MyAnonamouse — `Le trône de fer [FRE]`,
`La Bataille des rois [FRE]`, `L'ombre maléfique [FRE]`, `L'invincible forteresse [FRE]`,
`Festín de cuervos [SPA]`, `Urzeala tronurilor [ROM]` — imported, later purged from the library by
the fix-38 cleanup (exports in `/volume1/docker/calibre-web-automated/fix38-removed-books/`).

- Evidence: `GET /api/v1/book` (foreign-titled records above), `GET /api/v1/history?pageSize=200`
  (the 6 foreign grabs), `GET /api/v1/metadataprofile` (allowedLanguages).

### B2 (high, nas) — Zero grab-time language guard

`GET /api/v1/releaseprofile` → `[]`. No must-not-contain terms exist, so nothing blocks
`FRE/FRENCH/VF/SPA/ROM/Tome` releases at decision time, and Readarr's quality model has no
language dimension (all foreign grabs scored as plain "EPUB"). Indexers: MyAnonamouse (served all
6 foreign grabs), IPTorrents, Zenith — all via Prowlarr, no language filtering there either.

### B3 (high, mini) — Libreseerr hard-codes `anyEditionOk: True` on every add

`configs/docker-stack/stacks/libreseerr/readarr.py` line 269 (live == repo) sets
`"anyEditionOk": True` in the `POST /api/v1/book` payload; all 16 recent `Adding book:` log
payloads carry it. Per `readarr-api-quirks` (edition pinning requires `anyEditionOk=false`), every
book requested through Libreseerr is un-pinned, letting Readarr match/file **any** edition of the
work — the enabler for both foreign-release grabs (B1) and wrong-edition filing (B4).

---

## Cluster 2 — Import completion & file↔record correctness (`fix-47`)

> **RESOLVED 2026-07-20 (fix-47).** B4: 4 cross-wired bookfiles deleted (66 Avatar-content
> on Mercy, 70 Curse-content on "Namaah's Kiss", 67 Scion-content on Chosen, 69 Justice on
> the French edition) + correct epubs re-imported via ManualImport with explicit
> bookId/editionId/foreignEditionId; the 2 lost books recovered end-to-end — **Kushiel's
> Mercy (70)** and **Naamah's Kiss (71)** now in Calibre (ManualImport does NOT fire the
> Connect script; hand-staged into CWA ingest). Record 262 pinned to the properly-spelled
> English "Naamah's Kiss" edition (5659537); omnibus 554 unmonitored; leftover Portuguese
> record 303 deleted. B5: importable epubs drained; remaining `/seedbox/books` files are
> intentional mobi/lit/pdf seed-store siblings (operator decision — do not delete, seeding).
> B6: all 6 titles **recovered end-to-end** — re-monitored, re-searched (grabs landed in
> minutes), hit the same 80 % matcher wall again (proving the class), then force-imported
> via explicit ManualImport (queue drained via downloadId) and staged into CWA;
> dead-ends now page via `readarr-import-deadends` (48 h window — custom-script Connect
> cannot hook OnImportFailure). B7: PDFs for Scion/Blessing replaced with the release epubs;
> all ebook authors moved to profile "EPUB Preferred" (upgradeAllowed, cutoff EPUB, PDF
> disallowed), guarded by `books-format-guard`. Cross-wiring class check:
> `books-pipeline-lost-imports` (Readarr-claims vs Calibre-has — filenames can't detect it,
> Readarr renames to the record title). db-locked SQLite task errors: none during the repair;
> left as a watch item. Runbook: `wiki/docs/runbooks/books-imports.md`.

### B4 (high, nas) — 2026-07-18 series-pack import cross-wired files into wrong/French records; 2 books lost

During the `Kushiel's Legacy series 1-8` pack import (12:47–12:48 EDT), Readarr filed English
files under wrong records (byte-size matching against the pack proves the cross-wiring):

- `Kushiel's Justice.epub` (767 093 B) → record **"La Justice de Kushiel - Imriel, T2"**
- `Kushiel's Avatar.epub` (834 146 B) → record **"La Grâce de Kushiel - Imriel, T3"** (= *Kushiel's
  Mercy*'s French edition)
- `Naamah's Curse.epub` (659 782 B) → record **"Namaah's Kiss"** (misspelled record; twice)
- `Kushiel's Scion.epub` → record "Kushiel's Chosen"

Net loss: **Kushiel's Mercy** and **Naamah's Kiss** were never imported anywhere — content sits
ready in `/volume1/mounts/seedbox-files/books/Jacqueline Carey/Kushiel's Mercy (152)/` and
`Naamah's Kiss (154)/`, absent from `/volume1/books` (Calibre) and therefore from Kobo.

### B5 (medium, nas) — 36 leftover files in `/seedbox/books` awaiting import, incl. live wrong-matches

`GET /api/v1/manualimport?folder=/seedbox/books&filterExistingFiles=true` → 36 files. Rejection
classes: "Book match is not close enough: X % vs 80 %" (10), "Not an upgrade for existing book
file(s)" (7), "Has the same filesize as existing file" (8), no rejection (11). Live wrong-match
examples in the scan: `Rosemary and Rue….epub` → *"What If... Wanda Maximoff and Peter Parker Were
Siblings?"*; `Kushiel's Mercy.epub` → *"La Grâce de Kushiel: Imriel, T3"*.

### B6 (medium, nas) — Grabbed-then-abandoned: 6 titles died at the 80 % match threshold and were unmonitored

2026-06-28 `bookImportIncomplete` (6): The World of Ice & Fire (68.6 %/44.4 %), Highfire (66.3 %),
Plugged (60.7 %), The Atlantis Complex (79.8 %/73.1 %), Airman (60.2 %), Tuf Voyaging
(60.2 %/53.9 %) — all now `monitored=false, files=0`. The grab was wasted and the dead-end is
silent (Connect notification has `onImportFailure=false`; no alert fires for this class).

### B7 (low, nas) — Multi-format releases import PDF over EPUB

Readarr picked **PDF** for Naamah's Blessing and Kushiel's Scion although the releases contained
EPUB (quality-profile format ordering). Also noted here for the record: recurring
`SQLiteException: database is locked` task errors through 2026-07-19 (incl. one failed
`RefreshMonitoredDownloads`) — watch during fix-47; escalate if it recurs after remediation.

---

## Cluster 3 — Libreseerr request-path defects (`fix-48`)

> **RESOLVED 2026-07-20 (fix-48).** All 15 broken requests re-driven end-to-end through the
> fixed path: 0 errors on the board (6 completed incl. Parasite/Deadline/Blackout with files
> landed, rest `processing` with live searches). B8: the OL-id fallback is gone —
> no-metadata-match now raises `PermanentRequestError` (clear message + ntfy), and a new
> **library-first adoption** path rescues requests whose canonical record already exists
> while the lookup returns only junk (*The Return of the King*: record 630 sat unmonitored;
> every lookup hit was a "Custom Rebind by ValBinds" 400). B9: `READARR_TIMEOUT=60`
> (env-tunable) — which surfaced a second latent bug, gunicorn's 30 s sync-worker default
> killing long adds mid-flight (`WORKER TIMEOUT` → 500), fixed with `--timeout 300` in the
> compose command; all exceptions now logged, never stored silently. B10: new reconciler
> branch re-triggers `BookSearch` every ≥6 h up to 4 attempts for monitored-no-file-not-
> queued, then terminal-errors loudly (*The Rotten Romans* re-searched live,
> `search_attempts=2`). B11: `_norm_name` HTML-unescapes + NFKD-strips + drops numeric
> tokens — the real metadata form was `Emily 1818-1848 Bronte&#776;` (dates + HTML-entity
> combining mark), worse than the scan knew; *Wuthering Heights* added as record 702. B12:
> transient failures (timeout/connect/5xx) get status `retrying`, reconciler re-attempts 5×;
> every terminal failure pushes to ntfy topic `books` (token minted, vault
> `ntfy.libreseerr_token`; delivery verified live). **6-hourly burst identified — NOT B8:**
> each `Invalid request Validation failed` pairs with "no results in the configured
> categories … from your indexer" — Readarr's own scheduled RSS-sync/missing-search hitting
> an indexer category mismatch; harmless noise. Checks `libreseerr-request-stuck` +
> `libreseerr-request-path-guards` (reading.yaml) green. Runbook:
> `wiki/docs/runbooks/books-requests.md`.

13 of 18 requests errored, 2 stuck `processing` — all in the 2026-07-18 16:42–16:52 UTC burst
(state: `/opt/stacks/libreseerr/data/requests.json`).

### B8 (high, mini) — Open Library fallback POSTs `OL…W` IDs as `foreignBookId` → Readarr 400/500 (7 of 13 errors)

When no Readarr lookup match exists, `app.py` builds `foreignBookId` from the Open Library id.
Readarr validates it as a GoodreadsId: 12 logged
`POST /book failed (400): "A book with this ID was not found", attemptedValue: "OL15168494W"`,
6 requests errored this way (Feed, Deadline, Parasite, Blackout, Countdown, The Return of the
King), plus 1 × 500 `AddSkyhookData … Sequence contains no matching element` (Rolling in the
Deep) — same root cause, different Readarr code path. Also matches the 6-hourly
`ReadarrErrorPipeline|Invalid request Validation failed` bursts seen in Readarr's log (02:56,
08:57, 14:58, 20:58 …) — identify/confirm the caller during fix-48.

### B9 (medium, mini) — 15 s read timeout on Readarr calls; timeout errors stored but never logged

4 requests (The Lord of the Rings, The Fellowship of the Ring, The Hobbit, Persuasion) errored
`HTTPConnectionPool(host='192.168.10.4', port=8787): Read timed out. (read timeout=15)` — Readarr
lookup latency under burst load exceeds the hard-coded 15 s. Only 1 of the 4 produced any log
line; the exception is stored into requests.json silently (troubleshooting blind spot).

### B10 (medium, mini) — Reconciler has no terminal/retry path for "monitored, no file, not in queue"

`app.py:_reconcile_requests` resolves queue-matches, 404-dangling, file-present, and
unmonitored-no-file — but a monitored book that never entered the queue matches no branch, so the
request stays `processing` forever: *The Rotten Romans* (book 280, stuck 6 days), *Kushiel's
Legacy* omnibus (book 554) — exactly Readarr's 2 wanted/missing. Compounding: the add payload sets
`searchForMissingBooks: False` and nothing ever re-triggers a failed one-shot `BookSearch`.

### B11 (low, mini) — Unicode author-name mismatch kills requests

"Emily Brontë" arrives with a combining diaeresis (`e` + U+0308); author matching in
`readarr.py:_ensure_author` compares raw lowercase strings, 6 candidates rejected in a row →
request errored `Could not find author 'Emily Brontë' in Readarr metadata`. Needs NFC
normalization / diacritic-insensitive comparison.

### B12 (low, mini) — One-shot request model: Readarr-declined adds are terminal errors with no retry/re-queue

All Cluster-3 failures share a shape: one attempt at request time, stored error, no retry, no
operator surfacing beyond the requests tab. A transient Readarr timeout (B9) permanently errors a
request that would succeed seconds later.

---

## Historical context (already fixed or intentional — verified during the scan, NOT tasks)

- **H-A** 2026-06-28: Readarr's root folder *was* `/cwa-book-ingest` — CWA consumed imports out
  from under Readarr → 52 `bookFileDeleted reason=MissingFromDisk` (54 of 69 all-time imports have
  `importedPath` under `/cwa-book-ingest/`). Fixed by `ebook-01/03` (root → `/readarr-library`);
  the 15 imports since target the library. Explains the June wave of "downloaded but vanished".
- **H-B** pre-2026-07-13: Connect-script `xargs` trim stripped apostrophes — every
  Kushiel's/Naamah's title silently never reached CWA (6 ERRORs in
  `readarr-copy-to-cwa-ingest.log.bak-apostrophe-bug-2026-07-13`). Fixed 2026-07-13; 9/9 SUCCESS
  since. Explains the July wave of "imported but never showed on Kobo".
- **H-C** The missing-from-Kobo titles that *did* import on 07-18 were deliberately removed hours
  later by the fix-38 cleanup (dup re-imports + foreign ASOIAF; exports preserved in
  `fix38-removed-books/`), and *Naamah's Curse* (id 58) was archived for the kobo2 user 07-18
  17:24 — user-action, not sync failure.
- **Cleared of suspicion:** Deluge/seedbox (9/9 finished, relabeled, zero stuck), rclone
  mount/transport (listing matches seedbox exactly), remote path mapping, CWA ingest/import (68/68
  success, 1–2 min latency), Kobo sync layer (54/54 synced, whole-library mode, tokens valid).
  The "Import failed, path does not exist" clusters (06-28, 07-12) were transfer-lag retries that
  self-resolved.
