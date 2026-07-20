# Reading / CWA — Kobo sync, fork image, library hygiene

Runbook for the `reading.yaml` verification checks (task `fix-38`, quality-gate findings
M35 / L47 / I68, resolved 2026-07-18). The service itself is documented on the
[calibre-web-automated service page](../services/calibre-web-automated.md); this page is
what to do when a `cwa-*` check fires.

## Background — why these checks exist

The 2026-07-16 audit found the reading cluster **green but drifted**:

- **M35** — Kobo store passthrough (`config_kobo_proxy` in `app.db`) had silently flipped
  back to `1` after being documented as intentionally disabled on 2026-07-09. Decision
  2026-07-18: **ENABLED is the intent** (it carries the Kobo OAuth flow; the kobo2 sync
  stall that motivated the disable never recurred). The vault note `cwa.store_passthrough`
  is the paired documentation — the two must move together.
- **I68** — CWA runs the community fork `ghcr.io/new-usemame/calibre-web-nextgen:v4.0.7`
  (only source of the CVE-2026-7713 Kobo auth-token IDOR fix; upstream
  `crocodilestick/calibre-web-automated` is stalled at v4.0.6). The account is young and
  pseudonymous, so the compose file pins the image **by sha256 digest** — the tag alone is
  mutable and must never be trusted.
- **L47** — bulk grabs had split author identities (`Colfer, Eoin` vs `Eoin Colfer`,
  `George R.R. Martin` vs `George R. R. Martin`), imported a duplicate + 6 foreign-language
  ASOIAF editions, and left one book coverless. Cleaned 2026-07-18 (removed books exported
  to `/volume1/docker/calibre-web-automated/fix38-removed-books/` on the NAS before
  deletion — includes the 739 MB illustrated *A Game of Thrones*). On its first run the
  new dup-titles check caught **4 fresh duplicates** created 2026-07-17/18 by re-driven
  Readarr requests re-importing already-present titles — the class recurs, keep the check.

- **media-08** (fix-26/H15 follow-through, closed 2026-07-20) — every Readarr
  re-import/upgrade of a book CWA already had minted a **duplicate library entry**
  ("Naamah's Curse (62)" beside (58); the 2026-07-18 Connect re-fire repeated it, ids
  63/65/67/68 hand-deleted). Root cause: the readarr→CWA Connect script copies
  unconditionally (it *cannot* dedupe — the readarr container can't see the CWA
  library), and CWA's `auto_ingest_automerge` was `new_record`. Fix: `overwrite` —
  calibredb merges same-title+author imports into the existing record, so Readarr
  quality upgrades propagate and book ids stay stable for Kobo sync/shelves.
  Verified 2026-07-20: re-ingesting an existing epub left book count and max id
  unchanged and bumped the record's `last_modified` instead of creating a new row.

## Check-by-check response

### `cwa-kobo-sync-consumer` — a device's sync call failed
The real consumer path: both per-device sync URLs (vault `cwa.kobo_api_endpoint_admin`,
`cwa.kobo2_api_endpoint`) must return 200 + parseable JSON via the proxied
`books.tabaska.us` route. On failure: is the container up (`nas-cwa` check, direct
`http://192.168.10.4:8083` = 302)? A 502 with a healthy container = caddy → NAS path;
see the [reverse-proxy runbook](reverse-proxy.md). A 401/403 = the sync token or CWA user
changed — re-derive the endpoint from the device's `api_endpoint` setting and update the
vault + `/etc/verification/env` on the mini together.

### `cwa-kobo-proxy-intent` — the passthrough flag flipped
Not an outage: live `app.db` no longer matches documented intent (`proxy=1 sync=1`).
Decide which side is right, then change **both** the flag (`config_kobo_proxy` in
`/volume1/docker/calibre-web-automated/config/app.db` + container restart) and the vault
note `cwa.store_passthrough` — and this check's `expect` if the intent itself changed.
Never leave them contradicting; that silent contradiction *was* finding M35.

### `cwa-image-digest-pinned` — pin missing or runtime mismatch
The compose image line must end `@sha256:<64 hex>` and the running container must have
been created from exactly that reference. Empty `running=` usually means the NAS sudo
call failed (check `NAS_SUDO_PASSWORD` in `/etc/verification/env`, mode `root:btabaska 640`
— a `root:root 600` env file silently blanks every secret for ad-hoc CLI runs). A genuine
mismatch means someone edited compose or recreated the container off-pin: re-pin from the
running image's `RepoDigests`, `docker compose up -d`, and mirror the compose change to
`foss-setup/configs/nas/calibre-web-automated/`.

### `cwa-ghcr-tag-digest-drift` — the fork's tag was re-pointed
The tamper tripwire: ghcr's `v4.0.7` tag no longer resolves to the vetted digest. The
pinned container is still safe (that's the point of the pin) — but treat the re-point as
a supply-chain event: inspect the fork repo/account activity before trusting anything new
from it, and prefer migrating to upstream if `cwa-upstream-cve-catchup` also fires.
`TAG_CHECK_ERROR` = ghcr/API unreachable, retry before acting.

### `cwa-upstream-cve-catchup` — good news, not an outage
Upstream `crocodilestick/calibre-web-automated` published a release ≥ 4.0.7: the reason
for running the fork has expired. Plan a migration back to the trusted upstream image
(digest-pinned again), then retire the two fork-trust checks above.

### `cwa-library-author-split` / `cwa-library-dup-titles` / `cwa-library-covers`
Library hygiene regressed — usually right after bulk grabs or re-driven old requests.
Fix with `calibredb` inside the container (procedure with exact commands is on the
[service page](../services/calibre-web-automated.md) under troubleshooting): back up
`/volume1/books/metadata.db`, then merge authors with `set_metadata --field authors:`,
export-then-`remove --permanent` duplicate/unwanted editions, and set missing covers with
`ebook-meta --get-cover` + `set_metadata --field cover:`. Root-cause prevention for
foreign/duplicate editions is Readarr edition pinning (`anyEditionOk=false`).

### `cwa-ingest-automerge-guard` — the dedupe setting drifted
Not an outage: `auto_ingest_automerge` in
`/volume1/docker/calibre-web-automated/config/cwa.db` (table `cwa_settings`) is no
longer `overwrite`, or duplicate detection / the after-import scan was switched off.
This setting lives in a **runtime DB no compose file owns**, so this check is the
anti-drift codification — a CWA image bump or a click in Admin → CWA Settings can
revert it silently, and with `new_record` every Readarr re-import/upgrade mints a
user-facing duplicate again (the media-08 class). Restore via the CWA admin UI or
`sqlite3 …/cwa.db "UPDATE cwa_settings SET auto_ingest_automerge='overwrite'"` (takes
effect next ingest, no restart needed — the ingest processor re-reads settings per
run). If the *intent* ever changes, change this check's `expect` in the same commit.
Caveat automerge can't cover: punctuation-variant titles/authors (curly vs straight
apostrophe) dodge calibredb's exact match — that residue is what
`cwa-library-dup-titles` / `cwa-library-author-split` still catch.

## Standing state (2026-07-18)

| thing | value |
|---|---|
| image | `ghcr.io/new-usemame/calibre-web-nextgen:v4.0.7@sha256:89899edd…` (digest-pinned) |
| `config_kobo_proxy` | `1` — ENABLED is documented intent (vault `cwa.store_passthrough`) |
| `NETWORK_SHARE_MODE` | `false` in live compose **and** repo mirror (reconciled fix-38) |
| `auto_ingest_automerge` | `overwrite` in `cwa.db` since 2026-07-20 (media-08; guarded by `cwa-ingest-automerge-guard`) |
| library | 65 books (2026-07-20), single author identities, all covers present |
| removed-book stash | NAS `/volume1/docker/calibre-web-automated/fix38-removed-books/` (~1.5 GB, purgeable) |
| pre-cleanup DB backups | same dir, `metadata.db.pre-fix38` + `app.db.pre-fix38` in `fix38-backups/` |
