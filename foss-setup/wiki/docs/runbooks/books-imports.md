# Books — import completion & file↔record correctness

**Cluster:** Bookshelf (nas :8790) → Connect script → CWA ingest → Calibre `/volume1/books` → Kobo.
**Origin:** books-stack deep scan 2026-07-19/20, findings **B4/B5/B6/B7** (`fix-47`);
ported to the Bookshelf stack in `bmig-06` (books cutover,
program doc `foss-setup/docs/books-metadata-cutover-2026-07-20.md`).
**Checks:** `books-pipeline-lost-imports`, `bookshelf-import-deadends`, `books-format-guard`,
`bookshelf-cwa-copy-drops` (in `checks.d/reading.yaml` + `media.yaml`, host mini, ntfy
topic `verification`).

## What happened (2026-07-18 pack import, readarr era)

A `Kushiel's Legacy 1-8` series-pack import cross-wired English epubs into wrong (and
French-titled) records — the arr's free-matching filed *Kushiel's Justice* under the
French "La Justice" record, *Kushiel's Avatar* under "La Grâce", *Naamah's Curse* under a
misspelled "Namaah's Kiss" record, and *Kushiel's Scion* under "Kushiel's Chosen". Net
effect: **Kushiel's Mercy** and **Naamah's Kiss** were never imported anywhere — the arr
*looked* satisfied (records had files) while Calibre/Kobo never received the books. Two
multi-format releases imported **PDF over EPUB**. The class recurred in miniature during
the bmig-03 migration (2 files cross-wired mid-quota-storm) and bmig-05 (obfuscated scene
epubs stacking onto one record) — byte-size verification caught both.

## Standing gotchas (Bookshelf)

- **The arr renames files to the record title** — after a cross-wired import the
  filename *agrees* with the wrong record, so filename↔title scans can't detect it.
  The only honest probe is cross-layer: what Bookshelf claims vs what Calibre has
  (`books-pipeline-lost-imports`). Matching is stopword-tolerant (hardcover edition
  titles vary: "Artemis Fowl and the …" vs CWA "Artemis Fowl: The …").
- **Bookshelf ManualImport DOES fire the Connect script** (unlike readarr — learned
  bmig-03): hand-imports re-ingest into CWA, and `auto_ingest_automerge=overwrite`
  absorbs them. No hand-staging needed; the media-08 automerge guard is the backstop.
- **Custom-script Connect handlers cannot hook import failures**
  (`supportsOnImportFailure=false`) — the `bookshelf-import-deadends` check IS the alert
  path for grab→import dead-ends.
- **ManualImport payload quirks:** each file needs `foreignEditionId` (else NRE in
  `EnsureEditionAdded` — and it must be an id rreading-glasses-hc knows; the lookup's own
  `foreignEditionId` always works) *and* `languages` (else silent constraint failure);
  use `importMode: "copy"` from the seedbox mount so seeding is preserved.
- **`deleteFiles=true` does not delete files on this NAS** (readarr AND bookshelf,
  learned bmig-05) — after any record/file delete, verify on disk and `rm` manually.
- Leftover mobi/lit/pdf **siblings on `/seedbox/books` are intentional** — the mount is
  the seed store; only the best EPUB per book is imported. Don't "clean them up" on the
  seedbox side; it breaks seeding.

## If `books-pipeline-lost-imports` fails

A book Bookshelf thinks is on disk never reached Calibre. Either the import was
cross-wired (wrong record holds the file), the Connect copy was dropped, or the CWA-side
copy was deliberately removed (owner curation — see the bmig-06 Kushiel's Avatar case:
the "epub" claim was real but the owner had replaced it with a PDF set; resolution was
deleting the bookfile record, not re-ingesting).

1. Find the book in Bookshelf; check its bookfile path and **size** against the source
   release on `/volume1/mounts/seedbox-files/books/` — byte-size is the ground truth
   for which content a file really is.
2. Wrong content on the record → `DELETE /api/v1/bookfile/{id}` then ManualImport the
   right file with explicit ids (see gotchas).
3. Right content, Calibre just missing it → copy the file into the CWA ingest dir
   (`/volume1/docker/calibre-web-automated/ingest/`) and confirm it lands; if it
   *vanishes after ingest*, check whether another session/the owner is curating the
   library before re-adding.

## If `bookshelf-import-deadends` fails

A grab finished downloading but Bookshelf refused the import (usually "match is not close
enough: X% vs 80%", or retail release names failing arr parsing — the bmig-05 LOTR
trilogy case) and the book has no file and nothing queued. The download may still be on
the mount — check `/volume1/mounts/seedbox-files/books/` before re-grabbing, and import
it via ManualImport with explicit ids. If the content is gone, re-search. Do **not**
just unmonitor the book — that is exactly the silent rot this check exists to stop.

## If `books-format-guard` fails

Someone/something recreated a PDF-tolerant path: the "EPUB Preferred" profile drifted
(upgrade off, cutoff below EPUB, PDF re-allowed) or a new author landed on another
profile. This fired for real in bmig-06: Bookshelf's stock "eBook" profile (id 1) was
the libreseerr request default and collected 2 authors — the profile is now deleted,
the root-folder default is EPUB Preferred, and the patched `bookshelf.py`
`get_quality_profiles` orders EPUB Preferred first so the UI default stays correct even
if an upgrade recreates stock profiles. Restore the profile settings or move the author
(`PUT /api/v1/author/editor {"authorIds":[...],"qualityProfileId":<EPUB Preferred>}`).
The "Spoken" profile is exempt (audiobooks).

## If `bookshelf-cwa-copy-drops` fails

The Connect script (`readarr-copy-to-cwa-ingest.sh` — pre-bmig filename, registered in
Bookshelf's Connect config) logged a path-resolution error: a requested book never
reached CWA. Log: `/volume1/docker/bookshelf/config/logs/readarr-copy-to-cwa-ingest.log`.
The historical cause was `xargs` stripping apostrophes (fixed 2026-07-13); any new error
means a new path shape — fix the script in `configs/nas/` and mirror live.
