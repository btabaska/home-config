# Books — language & edition correctness

**Cluster:** Bookshelf (nas :8790) + Libreseerr (mini :8789) + rreading-glasses-hc metadata.
**Origin:** books-stack deep scan 2026-07-19/20, findings **B1/B2/B3** (`fix-46`); ported
to the Bookshelf stack in `bmig-06` (books cutover,
program doc `foss-setup/docs/books-metadata-cutover-2026-07-20.md`).
**Checks:** `bookshelf-foreign-records`, `bookshelf-foreign-grab-history`, `books-language-guard`
(in `checks.d/reading.yaml`, host mini, ntfy topic `verification`).

## Why this class exists

The goodreads-era metadata provider served foreign editions/works as canonical book
records **and stamped them `language=eng`** — the French Kushiel editions carried an
English language tag. Hardcover-mode metadata (rreading-glasses-hc) is much cleaner, but
author catalogs still legitimately include foreign-titled works, and provider language
metadata remains untrustworthy — the reliable detectors are **title patterns** (library,
scoped to monitored-or-has-file records; unmonitored catalog entries like Tolkien's
"LA Carta De Papa Noel" are inert) and **release-name markers** (grab history). The real
protections are grab-time and add-time guards:

1. **Release profile id=1** in Bookshelf — "must not contain" regex terms blocking
   `FRENCH/FRE/VF/SPA/ESP/ROM/ITA/GER/POR/…` markers and `Tome N` (cloned from readarr in
   bmig-02), plus the bmig-05 derivative-work terms `companion`/`coloring book`/
   `unofficial` (the LOTR auto-search re-picked a companion book). Slash-wrapped regex
   terms, case-insensitive.
2. **Libreseerr edition pinning** — the patched `ReadarrClient` base class sends
   `anyEditionOk: False` so every request pins the exact edition (repo:
   `configs/docker-stack/stacks/libreseerr/readarr.py`, live: mini
   `/opt/stacks/libreseerr/readarr.py`; `bookshelf.py` subclasses it — keep repo and
   live identical).

## If `bookshelf-foreign-records` fails

A foreign-titled record is monitored or holds a file (pattern: French/Spanish articles at
title start, `Tome N`, `, TN`). From mini:

```
curl -H "X-Api-Key: $BOOKSHELF_API_KEY" http://192.168.10.4:8790/api/v1/book | jq '.[] | select(...)'
```

- If it is a foreign **edition of a wanted work**: pin the English edition instead of
  deleting — `GET /api/v1/edition?bookId=N`, then `PUT /api/v1/book/N` with the full
  edition list (`monitored` flipped to the English edition) and `anyEditionOk: false`.
  The bulk `/book` endpoint omits editions; use the `/edition` endpoint.
- If it is a foreign **work** (unwanted): unmonitor it, or `DELETE /api/v1/book/N?deleteFiles=false`.
  (Remember: `deleteFiles=true` does NOT remove files on this NAS — verify on disk.)
- False positive (an English title matching the pattern, e.g. "El Paso …"): extend the
  regex in `checks.d/reading.yaml` with a whitelist alternation — repo first, then
  `sudo tee` to mini `/opt/verification/checks.d/` (plain scp fails, root-owned).

## If `bookshelf-foreign-grab-history` fails

A foreign release was actually grabbed after 2026-07-20 — the grab-time guard has a
hole. Get the release name from the check output, find which term set missed it, add a
term to release profile id=1 (`PUT /api/v1/releaseprofile/1`, terms are `/regex/i`
slash-wrapped, case-insensitive). Then remove the wrongly-grabbed book/file and re-search.

## If `books-language-guard` fails

Output says which guard is gone: `rp=RP_MISSING` → the enabled release profile no longer
carries the `french` + `companion` + `coloring book` term sets — it was deleted, disabled,
or trimmed; recreate/extend it (terms above; it lives only in Bookshelf's DB, no compose
file owns it). `pin=0` → `/opt/stacks/libreseerr/readarr.py` drifted from the repo copy —
redeploy from `configs/docker-stack/stacks/libreseerr/` and `docker compose restart libreseerr`.

## History

- 2026-06-28: auto-search on French records grabbed 6 genuinely foreign releases
  (`[FRE]`/`[SPA]`/`[ROM]`, MyAnonamouse); purged by fix-38.
- 2026-07-20 (`fix-46`): 8 foreign records deleted from the then-readarr library,
  2 records repaired by pinning English editions (*Kushiel's Justice* /
  *Kushiel's Mercy*), release profile + `anyEditionOk=False` deployed. File↔record
  re-linking of the 2026-07-18 pack import is `fix-47` (B4–B7).
- 2026-07-20 (`bmig-04/05`): old readarr's scheduled search grabbed ~6 foreign GRRM
  editions in its final hours (the exact B2 class) — purged in bmig-05; checks now
  point at Bookshelf, whose grab history has been clean since deploy.
- 2026-07-20 (`bmig-06`): checks ported readarr:8787 → bookshelf:8790; foreign-records
  scoped to monitored-or-has-file (hardcover author catalogs include inert
  foreign-titled works).
