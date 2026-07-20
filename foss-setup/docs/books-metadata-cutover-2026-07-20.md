# Books metadata cutover — Goodreads-mode Readarr → Bookshelf + rreading-glasses:hardcover

**Program doc for tasks `bmig-01`…`bmig-06` (track `books-cutover`). Worked one task per
session via `/build-next`.** Written 2026-07-20 from a live diagnosis session; the evidence
below was reproduced that day. Owner decisions already made (do NOT re-litigate in-session):

- **Decision: full pivot** to Bookshelf (maintained Readarr fork) + rreading-glasses in
  Hardcover mode. Goodreads mode is the root cause, not a tuning problem.
- **Timing: pre-approved to run any time, outside the 4–7AM window** ("It can happen right
  now outside maintenance" — owner, 2026-07-20). No task in this track needs a window gate;
  the parallel-run design keeps the live pipeline working until bmig-05 cutover.
- **The libreseerr author-gate patch is in scope** (bmig-04) — clean metadata alone does not
  remove the wrong-book failure mode.

## Why (findings C1–C5, all reproduced 2026-07-20)

The 2026-07-20 request batch (~10 books, 15:47–15:56 UTC) produced wrong books and
permanently-stuck requests. Root cause is three stacked layers, all downstream of
`rreading-glasses --upstream=www.goodreads.com` (a verbatim Goodreads scraper, no curation).

- **C1 — wrong-record binding.** `book/lookup?term=Pride and Prejudice Jane Austen` returns
  5 results and the real novel is NOT one of them (an omnibus + fanfic "variations" + *Pride,
  Prejudice, and Peril* by Katie Oliver, which matches on its SERIES name "A Jane Austen Tea
  Society Mystery"). libreseerr log 11:55:05: first candidate tried = the Katie Oliver book,
  POST /book 201 → readarr record 692 under the wrong author, grabbed + imported into CWA.
- **C2 — junk canonical metadata poisons tracker search.** Record titles/authors become MAM
  AND-search terms. Proven zero-result queries: "J.R.R. Tolkien The Hobbit, or There and Back
  Again" (long-form Goodreads canonical title) → 0; author `Emily 1818-1848 Bronte&#776;`
  (life-dates + unescaped HTML entity scrape artifact) → 0; omnibus record "Kushiel's
  Legacy: Kushiel's Dart / …" → unmatchable.
- **C3 — pen names invisible.** `term=Feed Seanan McGuire` → 0 results (Goodreads lists it
  under Mira Grant) → title-only fallback → M.T. Anderson's *Feed* wins on exact title.
  Same class: *Blackout* → Connie Willis; *Countdown* → Deborah Wiles. Hardcover models the
  Mira Grant ↔ Seanan McGuire alias.
- **C4 — libreseerr candidate walker has no author check.** `_attempt_add` (local patch
  2026-07-12, `/opt/stacks/libreseerr/app.py`) ranks by title-ish score then adds the first
  candidate Readarr accepts, stamping the *requested* author onto authorless candidates.
  Silent wrong-book instead of loud failure.
- **C5 — collateral in the live libraries.** Wrong readarr records: 692 (*Pride, Prejudice,
  and Peril*/Katie Oliver), 564 (*Captain Wentworth's Persuasion*/Regina Jeffers), 684
  (*Countdown*/Deborah Wiles), 687 (*Blackout*/Connie Willis — grabbed, queue "completed"),
  691 (*Feed*/M.T. Anderson — imported), 683 LOTR record grabbed a companion book ("Into the
  Heart of Middle-Earth"). Wrong books already in CWA (`/volume1/books`): *Feed* (79,
  M. T. Anderson), *Pride, Prejudice, and Peril* (80), *Prada and Prejudice* (Katie Oliver;
  verify calibre id in-session). Stuck-forever requests in
  `/opt/stacks/libreseerr/data/requests.json`: Return of the King (630), Wuthering Heights
  (702), Pride and Prejudice (692), Rolling in the Deep (685), Countdown (684), Kushiel's
  Legacy (554), The Lord of the Rings (683), Fellowship (600), The Hobbit (555), Persuasion
  (564), Rotten Romans (280).

Upstream facts (verified 2026-07-20): Readarr is retired (dead official metadata);
**Bookshelf** is the maintained fork, pre-wired for rreading-glasses in Goodreads OR
Hardcover mode; rreading-glasses Hardcover mode = `hardcover` Docker tag +
`--hardcover-auth="Bearer <token>"`, **requires a fresh install** (different id namespace —
existing Goodreads-mode library records/cache do not carry over), token **expires every
Jan 1** (needs a monitoring tripwire). libreseerr already ships a `BookshelfClient`.

## Architecture target

```
libreseerr (mini)  ──BookshelfClient──▶  bookshelf (NAS :8790)
                                            │ metadata
                                            ▼
                              rreading-glasses-hc (NAS :8789, hardcover tag)
                                            │
                                   rreading-glasses-db (existing postgres 17,
                                   NEW database `rreading_glasses_hc`)
bookshelf ──search──▶ prowlarr (MAM/IPT/Zenith) ──▶ deluge@betty ──▶ import
         ──Connect: readarr-copy-to-cwa-ingest.sh──▶ CWA ingest (unchanged)
```

Old path (readarr :8787 + rreading-glasses :8788 goodreads) keeps running untouched until
bmig-05 decommission. Same `/readarr-library` root folder and library files — Bookshelf
adopts the existing files, nothing re-downloads.

## Task map (each = one `/build-next` session)

### bmig-01 — Hardcover key + parallel hardcover metadata instance
Ask the owner (AskUserQuestion) to create the Hardcover account + API token
(hardcover.app → Settings → Hardcover API, copy INCLUDING the "Bearer " prefix) and paste it
into the session; store at vault `books.hardcover_api_token` (merge, never blind-assign —
see vault-edit-hazard). Deploy `rreading-glasses-hc` in the NAS media-automation stack:
`blampe/rreading-glasses:hardcover` **pinned by digest** (`docker buildx imagetools inspect`
per the existing rreading-glasses pin comment), port 8789:8788, own postgres DATABASE
(`rreading_glasses_hc`) in the existing `rreading-glasses-db` container (create via
`CREATE DATABASE`; the DS920+ has no RAM for a second postgres), `mem_limit: 128m` like the
sibling. Acceptance (the poison corpus, direct against :8789): search "Pride and Prejudice
Jane Austen" returns the canonical Austen work in the top results; Wuthering Heights work
carries a clean "Emily Brontë" author; "Feed" resolves the Mira Grant work with the
Seanan McGuire alias visible. Codify compose + `.env.example`; wiki service enrichment;
liveness check only (full check migration is bmig-06).

> **done 2026-07-20** — token at vault `books.hardcover_api_token`; `rreading-glasses-hc`
> live on :8789 (DB `rreading_glasses_hc` in the shared postgres). **Deviation:** the
> published `:hardcover` image is broken since ~07-18 (Hardcover caps GraphQL at 5
> top-level queries, image batches 25 → 403 `top_level_limit_exceeded`; upstream #574).
> Owner-approved temporary local build `local/rreading-glasses:hardcover-batch5-a2939b6`
> (upstream main `a2939b6` + one-line batch patch, built on the mini) — swap back per
> task `books-hc-upstream-swap`. Poison corpus passed: canonical Austen work rank 2;
> clean "Emily Brontë"; Feed → Mira Grant with the Seanan McGuire alias in the author
> description. Old readarr path verified untouched. Liveness check
> `nas-rreading-glasses-hc` deployed + green; coverage manifest updated. NOTE for
> bmig-02/03: Hardcover's ~60 req/min quota makes cold-cache operations slow — background
> author refreshes saturate it for minutes after each new author is touched; pace bulk
> migration accordingly.

### bmig-02 — Bookshelf deployed in parallel, wired to hardcover metadata
Add `bookshelf` to the media-automation compose (image: the Bookshelf project's official
registry — resolve current image/tag in-session and DIGEST-PIN; young-fork supply-chain
rules from fix-38/I68 apply: record the digest + add tag-drift awareness in bmig-06), config
`/volume1/docker/bookshelf`, port 8790, metadata source → `http://rreading-glasses-hc:8788`.
Configure to parity with readarr: root folder `/readarr-library` (same binds), quality
profile "EPUB Preferred" (upgradeAllowed, cutoff EPUB, PDF disallowed — books-format-guard
parity), metadata profile, release profile foreign-language blocklist (clone readarr profile
id=1 terms — B2 guard), download client Deluge on betty (host/port/label identical to
readarr's; remote path mapping `/home/hd34/btabaska/files/` → `/seedbox/`), Connect custom
script `readarr-copy-to-cwa-ingest.sh` (same bind mounts: `/readarr-library`,
`/cwa-book-ingest`, script dir; On Import + On Upgrade). Register as a Prowlarr APPLICATION
(fullSync; expect MAM/IPT/Zenith to sync). API key → vault `arr_api_keys.bookshelf`.
Acceptance: system status green, 3 indexers synced, an interactive search on a known-good
title returns MAM candidates, Connect test fires (log line in the script's logfile).
DO NOT enable any RSS/auto-add that would race the still-live readarr.

> **done 2026-07-20** — bookshelf live on :8790 (`ghcr.io/pennydreadful/bookshelf:hardcover-v0.4.20.129`
> @sha256:388eecc9…, == rolling `hardcover` that day; LinuxServer-style image, `METADATA_URL`
> env → `http://rreading-glasses-hc:8788`). Full readarr parity wired via API clone: EPUB
> Preferred QP, 5-term foreign blocklist, Deluge@betty, `/seedbox` mapping, CWA Connect script
> (Test fired, fork keeps `readarr_*` env vars), root folder, Standard metadata profile; UI
> login = readarr's own Users row copied (Forms auth). Prowlarr app registered (Readarr type —
> no Bookshelf type exists), 3 indexers synced. API key → vault `arr_api_keys.bookshelf`.
> Acceptance: health `[]`, poison lookup returns canonical Austen work (clean `austen, jane`,
> C1/C2 fixed at the metadata layer), interactive search bookId=24 → 24 releases (20 MAM).
> `nas-bookshelf` check + coverage entry deployed, green. **Deviations:** (1) owner-approved
> DEDICATED Deluge category `bookshelf`/`bookshelf-imported` (not "identical to readarr's") —
> shared category made bookshelf track readarr's stuck torrents and would double-import after
> bmig-03; bmig-05's seedbox label-script step must cover `bookshelf`/`bookshelf-imported`.
> (2) Root-folder POST auto-triggered a disk scan that adopted 3 authors/15 books uncontrolled
> during a Hardcover quota storm (dup "Eoin Colfer" author) — records deleted (files untouched),
> library reset to empty; **bmig-03 must expect this rescan behavior and pace one author at a
> time**. Also learned: hc searches 403 (`top_level_search_limit_exceeded`) whenever they batch
> with author-refresh queries — searches only work while refreshes are quiet. One unmonitored
> Jane Austen author (0 files) left in bookshelf as a warm-cache acceptance artifact.

### bmig-03 — Library migration (authors + existing files, no re-downloads)
Enumerate the old readarr inventory (`/api/v1/book`, files>0 — ~65 books/~20 authors; also
capture monitored-no-file wanted list). For each author: add to Bookshelf via hardcover
lookup (expect CLEAN author identities — no `(2)`/`(4)` suffix dirs, no life-date names).
For each book-with-file: match the hardcover work/edition (ISBN first, title fallback),
then Bookshelf ManualImport against the existing file path — byte-size is ground truth for
file↔record identity (readarr-api-quirks); do NOT let Bookshelf rename/move during adoption
(files are already record-title-named from the readarr era). ManualImport quirks that will
recur: needs `languages` (NOT NULL) + `foreignEditionId`, and does NOT fire Connect — CWA
already has these books, so no hand-staging needed. Acceptance: Bookshelf book-with-file
count == old readarr count, spot-check 5 titles map to the right files by size, zero
cross-wired records (books-pipeline-lost-imports logic run against Bookshelf), CWA book
count unchanged (no duplicate ingest — automerge guard from media-08 is the backstop).

> **done 2026-07-20** — library migrated: 19/19 files adopted IN PLACE (paths + sizes +
> mtimes byte-identical to the pre-migration snapshot; manifest committed at
> `docs/books-cutover-bmig03-manifest.json`). Live readarr count was 21 bookfiles (the
> plan's ~65 was an over-estimate); 2 deliberately NOT migrated = C5 wrong-books *Feed*
> (M.T. Anderson, readarr 691) and *Prada and Prejudice* (Katie Oliver, readarr 693 —
> **addendum to the C5 record list for bmig-05**). 6 authors added unmonitored
> (monitor=none, no search — readarr race impossible): Colfer 125883 **and dup identity
> 149453** (Plugged lives there; Bookshelf accepted a second author on the same on-disk
> path), Martin 78661, Tolkien 132049, Carey 154705, McGuire 185792, Mira Grant 106983.
> All 19 work ids verified against Hardcover GraphQL — zero cross-wired records; the
> per-author scan DID cross-wire 2 files mid-quota-storm (Avatar→Dart, Blessing→Kiss),
> fixed via ManualImport `replaceExistingFiles=true`. Wanted list (13 = C5 stuck set +
> *Deadline*) snapshotted in the manifest for bmig-05. CWA before==after: 65 books, max
> id 80, automerge + dup-titles guards green. **Learned, matters for bmig-04/05/06:**
> (1) **Bookshelf ManualImport DOES fire the CWA Connect script** (unlike readarr) — the
> 9 hand-imported files re-ingested and automerge=overwrite absorbed all of them in
> place; (2) rg-hc records can carry junk *edition* titles from Hardcover data (Airman
> arrived as "Foreclosure Self-Defense for Dummies", Kiss as "Namaah's Kiss" typo) — fix
> = pin the right edition via book PUT + re-align the file with ManualImport; POST /book
> 500s ("Sequence contains no matching element") unless `editions[]` carries a
> foreignEditionId that exists in rg's list — the lookup's own `foreignEditionId` always
> works; (3) the ported books-pipeline-lost-imports (bmig-06) must tolerate edition-title
> variants ("Artemis Fowl and the..." vs CWA "Artemis Fowl: The...") — normalized
> containment alone false-flags. Also fixed in-session: bookshelf `config.xml` was
> world-readable (fix-23 class, nas-secret-file-perms went crit) → chmod 600, check green.

### bmig-04 — libreseerr: Bookshelf backend + author-gate + ISBN-first + fail-loudly
Patch `/opt/stacks/libreseerr/` (bind-mounted app.py + the client; mirror to
`foss-setup/configs/docker-stack/stacks/libreseerr/`): (a) **author-verification gate** in
`_attempt_add` — a candidate is only eligible if its OWN looked-up author token-matches the
requested author (`_norm_name` both sides); NEVER stamp the requested author onto an
authorless candidate; (b) **ISBN-first** — the OL search doc usually carries isbn_13; prefer
`isbn:` lookup before term search; (c) exhausted/no-eligible-candidates →
`PermanentRequestError` + ntfy `books` topic (existing NTFY_TOKEN path), never add-the-next-
thing; (d) switch the configured backend to Bookshelf (`BookshelfClient`, :8790, new API
key). Recreate the container (arbiter quirk: recreate, not restart, if compose env changed).
Acceptance = the failure corpus end-to-end through the UI/API: request "Pride and Prejudice"
(Austen), "Feed" + "Blackout" + "Countdown" (Seanan McGuire), "The Hobbit", "Wuthering
Heights", "The Lord of the Rings" — each must bind the CORRECT record (paste record
title+author for each) or fail loudly with an ntfy push; zero silent wrong-books. gunicorn
--timeout 300 + READARR_TIMEOUT=60 survive the patch (fix-48 B9 regression risk).

> **done 2026-07-20** — libreseerr cut over to Bookshelf :8790 (`data/config.json`, key
> vault `arr_api_keys.bookshelf`); patch set now app.py + readarr.py + **bookshelf.py**
> (BookshelfClient = ReadarrClient subclass shadowing the image's unpatched client — one
> implementation keeps fix-25/46/48 guards). Author gate live in `_attempt_add` AND
> `adopt_library_book`; Bookshelf's /book list + /book/lookup omit the author object, so
> candidate authors are recovered from `authorTitle` and record authors via
> authorId→/author — the requested author is NEVER stamped. Pen names pass only when both
> hardcover bios name each other (Mira Grant ↔ Seanan McGuire ✓; blocks parody-bio
> false-positives like Grahame-Smith name-dropping Austen). ISBN-first actually fixed: OL
> search.json stopped returning `isbn` by default — explicit `fields=` added; **isbn hits
> are title-gated too** (Wuthering isbn resolved to the correct hc work but its junk
> Vietnamese edition "TH'inh gio hu" — pinning it = tracker-unsearchable, bmig-03 class).
> No-eligible → PermanentRequestError + ntfy `books` (POSTs verified 200). Acceptance
> corpus: P&P→24/Austen, Feed→98/Mira Grant, Blackout→100, Countdown→110 (novella),
> Hobbit→70, LOTR→65 — all correct records; 4 already imported end-to-end (CWA ids 87-90);
> Wuthering Heights = LOUD author-gate error + ntfy (hardcover has no clean-titled
> candidate; note rg-hc lookups return 0/junk during quota storms — bmig-01 herd behavior
> reconfirmed, a refresh took 4m27s of 429s). Zero silent wrong-books. Reconciler loudly
> dangled all 11 pre-cutover stuck requests (expected — bmig-05 re-drives them).
> request-layer-audit.py reads the backend from libreseerr's config.json now + skips
> pre-cutover requests (`legacy_skipped`). Checks green: libreseerr-request-path-guards,
> -request-stuck, -request-rot. gunicorn --timeout 300 + READARR_TIMEOUT=60 intact.
> **Discovery for bmig-05 (old-path collateral, NOT touched — parallel-run rule):** old
> readarr's scheduled search grabbed ~6 FOREIGN GRRM editions 19:32-19:35Z (FRE/SPA/ROM:
> Le trône de fer ×3+, La bataille des rois, Urzeala tronurilor, Festín de cuervos) and
> its Connect ingested them into CWA (ids 83-86+) — add these to the C5 CWA/readarr
> cleanup list; books-language-guard should be flagging them.

### bmig-05 — Collateral cleanup, request re-drive, old-path decommission
Cleanup (archive-before-delete: tarball/export BEFORE any rm, verify the archive exists):
delete the C5 wrong records from the old readarr AND make sure they were not migrated into
Bookshelf in bmig-03; CWA: export-then-`calibredb remove --permanent` the wrong books
(*Feed* M.T. Anderson, *Pride Prejudice and Peril*, *Prada and Prejudice*; run as `-u abc`,
cp metadata.db first — cwa-calibredb-quirks); cancel/remove the wrong queue item (Connie
Willis Blackout) and the companion-book LOTR grab + its file if imported. Re-drive the C5
stuck request list through the new path (delete + re-create requests in libreseerr, or
repair `readarr_book_id` bindings to the correct Bookshelf records); each lands correct-or-
loud per bmig-04 behavior. Then decommission the old path: stop+remove `readarr` +
`rreading-glasses` (goodreads) containers, archive `/volume1/docker/readarr` config +
drop the old `rreading-glasses` postgres DATABASE (keep the container — hc uses it),
remove the readarr APPLICATION from Prowlarr, homepage tile readarr→bookshelf, Uptime-Kuma
"NAS Readarr"→"NAS Bookshelf", check seedbox deluge label scripts
(`configs/host/seedbox/deluge-relabel-imported.py`, `deluge-reaper.py`,
`deluge-preimport-stuck.py`, README) for readarr-label assumptions — the label Bookshelf
uses must stay covered; `unpackerr.conf` readarr section → bookshelf (this file is also
sec-10's cleartext-key finding — do not make it worse; reference env/vault per unpackerr's
supported config). Compose + .env.example + repo mirrors updated (anti-drift).

### bmig-06 — Monitoring/checks migration + docs + program close
Port every readarr-coupled check to Bookshelf endpoints/keys (inventory from 2026-07-20):
`checks.d/reading.yaml` — readarr-foreign-records, readarr-foreign-grab-history,
books-language-guard, books-pipeline-lost-imports, readarr-import-deadends,
books-format-guard, readarr-cwa-copy-drops; `checks.d/nas-services.yaml` — nas-readarr (+
add nas-bookshelf, nas-rreading-glasses-hc); `checks.d/media.yaml` — libreseerr-request-rot
et al; `checks.d/seedbox.yaml` readarr references; `verification/bin/arr-grab-audit.py`,
`request-layer-audit.py`, `unpackerr-poll-advancing.py`, `skills/media-triage.md`.
`/etc/verification/env`: add BOOKSHELF_API_KEY (mode 640 root:btabaska — the known silent-
blank hazard). NEW checks: (a) `hardcover-token-valid` — authenticated query against
rreading-glasses-hc upstream; must start failing loudly BEFORE the Jan-1 token expiry (warn
from Dec 15); (b) `request-author-parity` (C1/C4 class regression) — every non-error
libreseerr request's bound record author must token-match the requested author; (c)
`metadata-search-canary` (C2 class) — lookup "Pride and Prejudice Jane Austen" via Bookshelf
returns the canonical work in the top 3. Coverage manifest `nas.containers`: +bookshelf,
+rreading-glasses-hc, −readarr, −rreading-glasses (the 100%-coverage tripwire). Wiki:
enrichment entries (bookshelf new, readarr marked retired/removed, rreading-glasses updated
to hc), books runbooks repointed, this doc linked from the quality-gate doc (H15 family) and
the books-stack scan doc. Close the program: all bmig tasks done in progress.json, regen,
one commit, publish-deploy.

## Rollback

Until bmig-05 the old path is untouched — rollback = point libreseerr back at readarr
(:8787) and stop the new containers. After bmig-05: restore the readarr config dir from
the archive tarball + `docker compose up readarr` + re-add the Prowlarr application; the
old rreading-glasses postgres database is dropped only after the bmig-06 checks are green
(archive a `pg_dump` first in bmig-05 regardless).

## Standing constraints (apply to every session)

- Parallel-run discipline: nothing may break the live readarr pipeline before bmig-05.
- One task = one commit + `publish-deploy.sh`; `git pull` first (concurrent sessions).
- Secrets by vault key path only; never in chat/commits/docs.
- NAS: no docker socket for the ssh user — `printf '%s\n' "$PW" | ssh nas 'sudo -S …'`
  with vault `sudo.nas_password`; no scp — `ssh nas 'cat > path'`.
- Digest-pin every new image (fix-38/I68 practice).
- End-to-end verification means the consumer end: a request in libreseerr landing the right
  epub in CWA — not container liveness.
