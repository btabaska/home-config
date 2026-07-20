# Books — language & edition correctness

**Cluster:** Readarr (nas :8787) + Libreseerr (mini :8789) + rreading-glasses metadata.
**Origin:** books-stack deep scan 2026-07-19/20, findings **B1/B2/B3** (`fix-46`).
**Checks:** `readarr-foreign-records`, `readarr-foreign-grab-history`, `books-language-guard`
(in `checks.d/reading.yaml`, host mini, ntfy topic `verification`).

## Why this class exists

rreading-glasses (the Goodreads-proxy metadata source) serves foreign editions/works as
canonical Readarr book records **and stamps them `language=eng`** — the French Kushiel
editions carried an English language tag. That means Readarr's metadata-profile
`allowedLanguages` filter can *never* catch them; the profile stays at `eng, null` on
purpose (operator decision 2026-07-20: tightening to `eng` risks dropping legit untagged
editions). The reliable detectors are **title patterns** (library) and **release-name
markers** (grab history), and the real protections are grab-time and add-time guards:

1. **Release profile id=1** in Readarr — "must not contain" regex terms blocking
   `FRENCH/FRE/VF/SPA/ESP/ROM/ITA/GER/POR/…` markers and `Tome N`. Slash-wrapped
   regex terms were verified enforced live on 2026-07-20 (rejection reason
   "Contains these ignored terms").
2. **Libreseerr edition pinning** — `readarr.py` sends `anyEditionOk: False` so every
   request pins the exact edition the user picked (repo:
   `configs/docker-stack/stacks/libreseerr/readarr.py`, live: mini
   `/opt/stacks/libreseerr/readarr.py`; keep them identical).

## If `readarr-foreign-records` fails

A foreign-titled record entered the library again (pattern: French/Spanish articles at
title start, `Tome N`, `, TN`). On nas:

```
curl -H "X-Api-Key: $READARR_API_KEY" http://localhost:8787/api/v1/book | jq '.[] | select(...)'
```

- If it is a foreign **edition of a wanted work**: pin the English edition instead of
  deleting — `GET /api/v1/edition?bookId=N`, then `PUT /api/v1/book/N` with the full
  edition list (`monitored` flipped to the English edition) and `anyEditionOk: false`.
  The bulk `/book` endpoint omits editions; use the `/edition` endpoint.
- If it is a foreign **work** (unwanted): `DELETE /api/v1/book/N?deleteFiles=false`.
- False positive (an English title matching the pattern, e.g. "El Paso …"): extend the
  regex in `checks.d/reading.yaml` with a whitelist alternation — repo first, then
  `sudo tee` to mini `/opt/verification/checks.d/` (plain scp fails, root-owned).

## If `readarr-foreign-grab-history` fails

A foreign release was actually grabbed after 2026-07-20 — the grab-time guard has a
hole. Get the release name from the check output, find which term set missed it, add a
term to release profile id=1 (`PUT /api/v1/releaseprofile/1`, terms are `/regex/i`
slash-wrapped, case-insensitive). Then remove the wrongly-grabbed book/file and re-search.

## If `books-language-guard` fails

Output says which guard is gone: `rp=RP_MISSING` → release profile id=1 was deleted or
disabled, recreate it (terms above; it lives only in Readarr's DB, no compose file owns
it). `pin=0` → `/opt/stacks/libreseerr/readarr.py` drifted from the repo copy — redeploy
from `configs/docker-stack/stacks/libreseerr/` and `docker compose restart libreseerr`.

## History

- 2026-06-28: auto-search on French records grabbed 6 genuinely foreign releases
  (`[FRE]`/`[SPA]`/`[ROM]`, MyAnonamouse); purged by fix-38.
- 2026-07-20 (`fix-46`): 8 foreign records deleted (ids 138/139/150/166/167/175/194/201),
  records 261/263 repaired by pinning English editions (*Kushiel's Justice* /
  *Kushiel's Mercy*), release profile + `anyEditionOk=False` deployed. File↔record
  re-linking of the 2026-07-18 pack import is `fix-47` (B4–B7).
