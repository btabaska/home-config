# Books — request-path robustness (Libreseerr → Readarr)

**Scope:** a Libreseerr book request errors, sits in `processing`/`retrying`, or you got a
"Book request failed" ntfy push. Covers the fix-48 request-path overhaul (books-stack scan
B8–B12, 2026-07-20).

**Where things live:** Libreseerr runs on the **mini** (`/opt/stacks/libreseerr`, port 8789),
talks to Readarr on the **NAS** (`192.168.10.4:8787`). Request state:
`/opt/stacks/libreseerr/data/requests.json`. Logs: `docker logs libreseerr`.
`app.py`/`readarr.py` are **local patches** volume-mounted over the image — an image bump
reverts nothing on disk but a re-pull of a changed upstream requires re-deriving the patches
(the compose file warns about this; the `libreseerr-request-path-guards` check fires if the
patch markers vanish).

## How a request flows (post fix-48)

1. **Library first** — if a record with the same normalized title+author already exists in
   Readarr, it is *adopted*: monitored + `BookSearch` triggered, no `POST /book`. (The
   metadata lookup often ranks junk user-uploaded editions above — or instead of — the
   canonical work; *The Return of the King* failed this way while the real record sat in the
   library unmonitored.)
2. **Metadata lookup** — ISBN, then `title author`, then bare `title`. Candidates are ranked
   (canonical over junk) and tried until Readarr accepts one.
3. **No match at all** → **permanent error + ntfy**. The pre-fix code POSTed the Open Library
   work id (`OL…W`) as `foreignBookId`, which Readarr validates as a GoodreadsId — a
   guaranteed `400 "A book with this ID was not found"` (7 of the 13 07-18 failures).
   OL ids must never reach `POST /book`.
4. **Transient failure** (timeout / connection error / backend 5xx) → status **`retrying`**;
   the background reconciler (every 15 min) re-attempts up to **5×**, then terminal error +
   ntfy. Lookup timeout is `READARR_TIMEOUT` (60 s; the old hard-coded 15 s caused 4 of the
   13 failures under burst load). Gunicorn runs with `--timeout 300` — without it the 30 s
   default kills the worker mid-add (HTTP 500 with a `WORKER TIMEOUT` in the log).
5. **Added but nothing found** — a monitored, fileless, not-queued book gets its search
   re-triggered by the reconciler every **≥6 h up to 4 attempts**, then terminal error +
   ntfy. (Pre-fix this state matched *no* reconciler branch: *The Rotten Romans* sat
   `processing` for 6 days.)
6. Every **terminal** failure pushes to ntfy topic **`books`** (token
   `ntfy.libreseerr_token` in the vault, `NTFY_TOKEN` in `/opt/stacks/libreseerr/.env`).
   Subscribe to `books` in the ntfy app to receive them.

Author matching is unicode-robust: names are HTML-unescaped, NFKD-decomposed, stripped of
combining marks and numeric tokens ("Emily Brontë" with a combining diaeresis, and
rreading-glasses' `Emily 1818-1848 Bronte&#776;`, both match plain "Emily Bronte").

## Statuses on the request board

| status | meaning | action |
|--------|---------|--------|
| `processing` | added; searching or waiting for the queue | none — reconciler drives it |
| `retrying` | transient backend failure, auto-retry pending (n/5 in the error field) | none unless Readarr is actually down |
| `downloading` | in the Deluge queue | none |
| `error` | terminal; the error text says why and ntfy already told you | see below |
| `completed` | file present in Readarr | — |

## When you get a failure push

- **"not found in the backend metadata provider"** — the work isn't in rreading-glasses/
  Goodreads. Add it manually in Readarr (or via CWA upload) if you own it; the request
  cannot succeed automatically.
- **"Backend rejected every metadata candidate"** — lookup returned only junk editions and
  every add 400'd. Check whether the canonical record exists in Readarr under a variant
  title; adopt-by-library only matches normalized-equal titles.
- **"No download source found after N searches"** — indexers have no release. Normal for
  obscure titles; re-request later or source manually.
- **"Gave up after 5 attempts"** — Readarr was unreachable/slow for over an hour. Check
  Readarr on the NAS, then re-request.

## Verification

- `libreseerr-request-stuck` (fix-48 B10/B12): fails if any non-terminal request has had no
  activity for 48 h — the reconciler dead-ended or died.
- `libreseerr-request-path-guards` (fix-48 B8/B9/B11): fails if a known failure signature
  resurfaces in recent errors or any guard is missing (patched `app.py`/`readarr.py`,
  gunicorn `--timeout`, ntfy token).
- `libreseerr-request-rot` (fix-26): stored statuses vs Readarr truth (dangling /
  falsely-completed).

## Note: the 6-hourly "Invalid request Validation failed" bursts in Readarr's log

Investigated during fix-48 and **not** Libreseerr: each warning pairs with *"Query
successful, but no results in the configured categories were returned from your indexer"* —
they come from Readarr's own scheduled RSS-sync/missing-search hitting an indexer category
mismatch, and are harmless noise unless a wanted book stops matching entirely.
