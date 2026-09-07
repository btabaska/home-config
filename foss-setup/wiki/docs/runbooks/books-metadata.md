# Books — hardcover metadata health (token expiry + search canary)

**Cluster:** rreading-glasses-hc (nas :8789, `hardcover` mode) → shared
`rreading-glasses-db` postgres (database `rreading_glasses_hc`) → Bookshelf (nas :8790).
**Origin:** books metadata cutover `bmig-01`…`bmig-06`
(program doc `foss-setup/docs/books-metadata-cutover-2026-07-20.md`) — the goodreads-era
provider and its database are gone (dropped in bmig-06; pgdump archived at
`nas:/volume1/archive/books-cutover-bmig05/rreading-glasses-goodreads-db.pgdump`).
**Checks:** `hardcover-token-valid`, `metadata-search-canary` (in `checks.d/reading.yaml`,
host mini), `nas-rreading-glasses-hc` + `nas-bookshelf` liveness (in
`checks.d/nas-services.yaml`), and the Shelfmark pair
`shelfmark-mam-path-ready` + `shelfmark-search-consumer` (host nas, in
`checks.d/reading.yaml`).

## Shelfmark (search frontend, nas :8084 / shelfmark.tabaska.us)

- **2026-09-06 provider incident:** every search returned "No results found"
  while the container was healthy. The Hardcover token in
  `/volume1/docker/shelfmark/shelfmark.env` was a valid JWT (exp 2027-07-20,
  correctly `Bearer`-prefixed — shelfmark strips/re-adds the prefix) but the
  **Hardcover account behind it is inactive** → API returns
  `401 {"error":"invalid_token","error_description":"User account is not active"}`
  on every GraphQL call. `METADATA_PROVIDER` is hardcoded per deployment with
  no auto-fallback, so the UI silently showed empty results.
- **Fix applied 2026-09-06:** `METADATA_PROVIDER=openlibrary` +
  `OPENLIBRARY_ENABLED=true` in `shelfmark.env` (keyless provider;
  `HARDCOVER_ENABLED=true` kept). Env change ⇒ **recreate**, not restart:
  `docker compose up -d --force-recreate shelfmark` in
  `/volume1/docker/shelfmark` (`--pull never` if the pull hangs).
  Verified: `/api/metadata/search?query=the cat in the hat` → 40 books,
  "The Cat in the Hat" first.
- **Flip back to Hardcover:** log into hardcover.app (account must be ACTIVE),
  Settings → Hardcover API → copy the token **including the leading `Bearer `
  prefix** → vault `books.hardcover_api_token` → env `METADATA_PROVIDER=hardcover`
  + `OPENLIBRARY_ENABLED=false` → recreate (above) → re-run
  `shelfmark-search-consumer`.
- **If `shelfmark-search-consumer` fails:** `books=0` = provider credential
  dead or provider unselected (check `shelfmark.env` `METADATA_PROVIDER` +
  `<PROVIDER>_ENABLED`, then `docker logs shelfmark | grep -iE "hardcover|401"`);
  `books>0 hit=0` = provider reachable but returning wrong results (language
  filter / provider regression).

## If `hardcover-token-valid` fails

- **`HC_TOKEN_EXPIRING days_left=N`** — Hardcover API tokens expire every **Jan 1**;
  the check warns from ~17 days out (≈ Dec 15). Renew BEFORE Jan 1 or book metadata
  refreshes/searches silently go stale (rg-hc keeps serving its warm postgres cache, so
  the outage would otherwise surface weeks later as rot):
  1. Log into hardcover.app → Settings → Hardcover API → copy the token
     **including the leading `Bearer ` prefix**.
  2. Vault: update `books.hardcover_api_token` (merge-edit, never blind-assign —
     see vault-edit-hazard).
  3. NAS: update `HARDCOVER_API_TOKEN` in `/volume1/docker/media-automation/.env`,
     then `docker compose up -d rreading-glasses-hc` (recreate, env changed).
  4. Mini: update `HARDCOVER_API_TOKEN` in `/etc/verification/env`
     (mode 640 root:btabaska).
  5. Re-run the check; confirm `HC_TOKEN_OK days_left≈365`.
- **`HC_TOKEN_INVALID`** — the token died early (revoked/account issue). Same renewal
  path. Note Hardcover's ~60 req/min account quota: while rg-hc author refreshes are
  storming, API calls can 429/403 — the check retries once, but re-run it after a quiet
  minute before believing a hard failure.
- **`HC_TOKEN_ERROR`** — env var missing from `/etc/verification/env` or the token is
  not a JWT; fix the env line (the silent-blank 640-perms hazard applies).

## If `metadata-search-canary` fails

The exact C2-class lookup that broke the goodreads era: `book/lookup` for
"Pride and Prejudice Jane Austen" via Bookshelf must contain the canonical Austen work
in its result set (rank is deliberately NOT asserted — Bookshelf's lookup ordering is
nondeterministic; measured rank 1/7/4 across three identical back-to-back calls,
2026-07-20 — and libreseerr re-ranks candidates through its own title+author gates).

- `CANARY_MISS results=0` or tiny junk-only sets usually mean a Hardcover **quota
  storm** (background author refreshes batch-starve searches; bmig-01/02 behavior) or
  the token died (check `hardcover-token-valid` first). Wait for refreshes to go quiet
  (`docker logs rreading-glasses-hc` on nas shows the refresh queue) and re-run.
- Persistent miss with a healthy token = metadata regression in rg-hc or its local
  image — see the pinned local build note (`local/rreading-glasses:hardcover-batch5-*`,
  task `books-hc-upstream-swap` tracks moving back to upstream once #574 ships).

## Postgres / database facts

- The shared `rreading-glasses-db` (postgres:17.6) now holds ONLY
  `rreading_glasses_hc` (+ system DBs). Superuser role is `rreading-glasses`
  (NOT `postgres`): `docker exec rreading-glasses-db psql -U rreading-glasses -d rreading_glasses_hc`.
- The goodreads database was dropped 2026-07-20 (bmig-06) after all ported checks ran
  green. Restore path if ever needed:
  `docker run --rm -v /volume1/archive/books-cutover-bmig05:/a:ro postgres:17.6 pg_restore -l /a/rreading-glasses-goodreads-db.pgdump`
  (TOC), then `pg_restore -d <db>` against the container — but the goodreads-era stack
  (readarr + rreading-glasses) is decommissioned; a restore only makes sense alongside
  the bmig-05 rollback plan in the program doc.
- Compose healthcheck + `POSTGRES_DB`/`RG_DB_NAME` default to `rreading_glasses_hc`
  since bmig-06 — a fresh datadir inits straight to the hc database.
