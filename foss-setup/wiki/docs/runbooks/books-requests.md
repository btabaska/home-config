# Books — request-path robustness (Libreseerr → Bookshelf)

**Scope:** a Libreseerr book request errors, sits in `processing`/`retrying`, or you got a
"Book request failed" ntfy push. Covers the fix-48 request-path overhaul (books-stack scan
B8–B12, 2026-07-20) and the bmig-04 author gate / backend cutover (same day).

**Where things live:** Libreseerr runs on the **mini** (`/opt/stacks/libreseerr`, port 8789),
talks to **Bookshelf** on the **NAS** (`192.168.10.4:8790`, hardcover metadata — bmig-04;
the old Readarr `:8787` path is decommissioned in bmig-05). Request state:
`/opt/stacks/libreseerr/data/requests.json`. Logs: `docker logs libreseerr`.
`app.py`/`readarr.py`/`bookshelf.py` are **local patches** volume-mounted over the image —
an image bump reverts nothing on disk but a re-pull of a changed upstream requires
re-deriving the patches (the compose file warns about this; the
`libreseerr-request-path-guards` check fires if the patch markers vanish).

## How a request flows (post fix-48 + bmig-04)

1. **Library first** — if a record with the same normalized title already exists in
   Bookshelf **and its author passes the author gate**, it is *adopted*: monitored +
   `BookSearch` triggered, no `POST /book`. (The metadata lookup often ranks junk
   user-uploaded editions above — or instead of — the canonical work; *The Return of the
   King* failed this way while the real record sat in the library unmonitored. Bookshelf's
   `/book` list omits the embedded author, so the record's author is resolved via
   `authorId` against `/author` before comparing — never assumed.)
2. **Metadata lookup, ISBN first** — the OL search doc's `isbn_13` (requested explicitly
   via `fields=`; OL's default search fields dropped `isbn`) is looked up as `isbn:` before
   any term search; term search (`title author`, then bare `title`) is the fallback.
   Candidates are ranked (canonical over junk) and tried until the backend accepts one —
   but only candidates that pass the **bmig-04 eligibility gates**:
   * **title**: normalized exact or prefix match — right-author wrong-title ("Hex in the
     City" for "Feed") is still a wrong book. ISBN hits are gated too: hardcover works
     carry junk edition titles (an OL isbn for *Wuthering Heights* resolved to the correct
     work but its Vietnamese edition — pinning it would make the record
     tracker-unsearchable, the bmig-03 junk-edition class); a mismatched isbn edition
     falls through to term search.
   * **author**: the candidate's OWN author (recovered from `authorTitle` when the lookup
     omits the author object) must token-match the requested author, or be a
     provider-documented pen name — the two hardcover author bios must name each other in
     **both** directions (Mira Grant ↔ Seanan McGuire pass; a parody author whose bio
     name-drops Jane Austen does not). The requested author is **never** stamped onto an
     authorless candidate — that was the C4 bug that silently bound *Pride, Prejudice, and
     Peril* (Katie Oliver) to a Jane Austen request.
   No eligible candidate → **permanent error + ntfy**, never add-the-next-thing.
3. **No match at all** → **permanent error + ntfy**. The pre-fix code POSTed the Open Library
   work id (`OL…W`) as `foreignBookId`, which the backend validates against its metadata
   id namespace — a guaranteed `400 "A book with this ID was not found"` (7 of the 13
   07-18 failures). OL ids must never reach `POST /book`.
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
| `retrying` | transient backend failure, auto-retry pending (n/5 in the error field) | none unless Bookshelf is actually down |
| `downloading` | in the Deluge queue | none |
| `error` | terminal; the error text says why and ntfy already told you | see below |
| `completed` | file present in Bookshelf | — |

## When you get a failure push

- **"not found in the backend metadata provider (Hardcover)"** — the work isn't in
  hardcover's catalog. Add it manually in Bookshelf (or via CWA upload) if you own it; the
  request cannot succeed automatically.
- **"No eligible metadata candidate … refusing to add a different book (author gate)"** —
  every lookup candidate failed the title/author gates (the rejected list is in the error
  text). If OL and hardcover spell the author differently, re-request under hardcover's
  spelling; a pen name passes only when both hardcover bios reference each other.
- **"Backend rejected every eligible candidate"** — the gated candidates all 400'd on add
  (junk editions). Check whether the canonical record exists in Bookshelf under a variant
  title; adopt-by-library only matches normalized-equal titles.
- **"No download source found after N searches"** — indexers have no release. Normal for
  obscure titles; re-request later or source manually.
- **"Gave up after 5 attempts"** — Bookshelf was unreachable/slow for over an hour. Check
  Bookshelf on the NAS, then re-request. (Hardcover-quota storms during author refreshes
  surface this way too — rreading-glasses-hc 403s searches while refreshes run.)
- **"Backend book record no longer exists (dangling request)"** on a request from before
  2026-07-20 — expected once after the bmig-04 cutover: pre-cutover requests reference old
  readarr book ids that don't exist in Bookshelf. bmig-05 re-drives them.

## Verification

- `libreseerr-request-stuck` (fix-48 B10/B12): fails if any non-terminal request has had no
  activity for 48 h — the reconciler dead-ended or died.
- `libreseerr-request-path-guards` (fix-48 B8/B9/B11): fails if a known failure signature
  resurfaces in recent errors or any guard is missing (patched `app.py`/`readarr.py`,
  gunicorn `--timeout`, ntfy token).
- `libreseerr-request-rot` (fix-26): stored statuses vs backend truth (dangling /
  falsely-completed). Audits against the backend named in libreseerr's own
  `data/config.json`; requests created before the bmig-04 cutover are counted as
  `legacy_skipped` until bmig-05 cleans them.

## Note: the 6-hourly "Invalid request Validation failed" bursts in Readarr's log

Investigated during fix-48 and **not** Libreseerr: each warning pairs with *"Query
successful, but no results in the configured categories were returned from your indexer"* —
they come from Readarr's own scheduled RSS-sync/missing-search hitting an indexer category
mismatch, and are harmless noise unless a wanted book stops matching entirely.
