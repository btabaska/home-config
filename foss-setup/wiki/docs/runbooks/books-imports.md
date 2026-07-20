# Books — import completion & file↔record correctness

**Cluster:** Readarr (nas :8787) → Connect script → CWA ingest → Calibre `/volume1/books` → Kobo.
**Origin:** books-stack deep scan 2026-07-19/20, findings **B4/B5/B6/B7** (`fix-47`).
**Checks:** `books-pipeline-lost-imports`, `readarr-import-deadends`, `books-format-guard`
(in `checks.d/reading.yaml`, host mini, ntfy topic `verification`).

## What happened (2026-07-18 pack import)

A `Kushiel's Legacy 1-8` series-pack import cross-wired English epubs into wrong (and
French-titled) records — Readarr's free-matching filed *Kushiel's Justice* under the
French "La Justice" record, *Kushiel's Avatar* under "La Grâce" (= *Kushiel's Mercy*'s
French edition), *Naamah's Curse* under a misspelled "Namaah's Kiss" record, and
*Kushiel's Scion* under "Kushiel's Chosen". Net effect: **Kushiel's Mercy** and
**Naamah's Kiss** were never imported anywhere — Readarr *looked* satisfied (records had
files) while Calibre/Kobo never received the books. Two multi-format releases imported
**PDF over EPUB** because their epubs had been stolen by the wrong records.

Repair (2026-07-20): 6 bad bookfiles deleted (4 cross-wired + 2 PDFs), correct epubs
re-imported via the ManualImport command with **explicit** `bookId`/`editionId`/
`foreignEditionId` per file (never trust the auto-matcher for packs), record 262 pinned
to the properly-spelled English "Naamah's Kiss" edition, Mercy + Kiss hand-staged into
CWA ingest (see gotcha below). Six 2026-06-28 dead-end titles re-monitored + re-searched.
All ebook authors moved to the **EPUB Preferred** quality profile (upgrade to EPUB
cutoff, PDF disallowed).

## Standing gotchas

- **Readarr renames files to the record title** — after a cross-wired import the
  filename *agrees* with the wrong record, so filename↔title scans can't detect it.
  The only honest probe is cross-layer: what Readarr claims vs what Calibre has
  (`books-pipeline-lost-imports`).
- **ManualImport does not fire the Connect script** (`readarr_addedbookpaths` is not
  populated for manual imports). After any ManualImport, copy the imported file(s)
  from `/volume1/docker/readarr/library/...` into
  `/volume1/docker/calibre-web-automated/ingest/` yourself, or the book never reaches
  Calibre/Kobo.
- **Custom-script Connect handlers cannot hook import failures**
  (`supportsOnImportFailure=false`) — the `readarr-import-deadends` check IS the alert
  path for grab→import dead-ends.
- **ManualImport payload quirks:** each file needs `foreignEditionId` (else NRE in
  `EnsureEditionAdded`) *and* `languages` (else silent constraint failure); use
  `importMode: "copy"` from the seedbox mount so seeding is preserved.
- Leftover mobi/lit/pdf **siblings on `/seedbox/books` are intentional** — the mount is
  the seed store; only the best EPUB per book is imported. Don't "clean them up" on the
  seedbox side; it breaks seeding.

## If `books-pipeline-lost-imports` fails

A book Readarr thinks is on disk never reached Calibre. Either the import was
cross-wired (wrong record holds the file) or the Connect copy was dropped.

1. Find the book in Readarr; check its bookfile path and **size** against the source
   release on `/volume1/mounts/seedbox-files/books/` — byte-size is the ground truth
   for which content a file really is.
2. Wrong content on the record → `DELETE /api/v1/bookfile/{id}` then ManualImport the
   right file with explicit ids (see gotchas).
3. Right content, Calibre just missing it → copy the file into the CWA ingest dir and
   watch `cwa_import` (the Connect drop class: apostrophe bug 2026-07-13, manual
   imports, script disabled).

## If `readarr-import-deadends` fails

A grab finished downloading but Readarr refused the import (usually "match is not close
enough: X% vs 80%") and the book has no file and nothing queued. The download may still
be on the mount — check `/volume1/mounts/seedbox-files/books/` before re-grabbing, and
import it via ManualImport with explicit ids. If the content is gone, re-search. Do
**not** just unmonitor the book — that is exactly the silent rot this check exists to
stop (six titles rotted that way from 2026-06-28 until fix-47).

## If `books-format-guard` fails

Someone/something recreated a PDF-tolerant path: the "EPUB Preferred" profile drifted
(upgrade off, cutoff below EPUB, PDF re-allowed) or a new author landed on another
profile. Restore the profile settings or move the author
(`PUT /api/v1/author/editor {"authorIds":[...],"qualityProfileId":<EPUB Preferred>}`).
The "Spoken" profile is exempt (audiobooks).

## Watch item (deliberate, not yet a task)

Recurring `SQLiteException: database is locked` Readarr task errors were seen through
2026-07-19 (incl. one failed `RefreshMonitoredDownloads`). None occurred during the
fix-47 repair session. If they recur, escalate to a new finding — do not fold into this
runbook's checks.
