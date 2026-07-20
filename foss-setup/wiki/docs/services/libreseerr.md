# libreseerr

Libreseerr — book request portal (Readarr / Bookshelf / LazyLibrarian)

| | |
|---|---|
| **Host** | [mini](../hosts/mini.md) |
| **URL** | https://libreseerr.tabaska.us |
| **Source** | `foss-setup/configs/docker-stack/stacks/libreseerr/compose.yaml` |
| **Notes** | Book request portal (feeds Readarr). Container port 5000. |
| **Upstream docs** | <https://github.com/zamnzim/Libreseerr> |

## About

Libreseerr is the book-request portal in Brandon's *arr media stack — the ebook/audiobook counterpart to Seerr (movies/TV) and MusicSeerr (music) — running as a single `ghcr.io/zamnzim/libreseerr` container on the Mac mini (`/opt/stacks/libreseerr`), exposed on `8789:5000` over the external `edge` (Caddy/Tailscale) network at https://libreseerr.tabaska.us. It fronts Readarr on the NAS (`http://192.168.10.4:8787`) to turn user book requests into monitored+searched Readarr additions, and pulls discovery/browse data from OpenLibrary. Two files are bind-mounted read-only as a local patch — `./app.py` and `./readarr.py` — that re-rank the Readarr/rreading-glasses lookup candidates (upstream blindly picks `readarr_books[0]`, which is often a junk user-uploaded ALL-CAPS edition with a phantom author ID that 404s → Readarr 400 / stuck book) so the canonical edition wins, then retry-until-accepted; the same patched app.py also runs a background status reconciler (fix-26) that keeps the request dashboard truthful against Readarr instead of only refreshing on UI opens. The image is pinned by MANIFEST digest (`820134e4`), not by local image ID, because upstream publishes no version tags and garbage-collects old digests.

## Containers

| Service | Image (pinned) | Ports |
|---|---|---|
| `libreseerr` | `ghcr.io/zamnzim/libreseerr@sha256:820134e44279c964ddf54090ab45b444a28e7f562256baaadf20fffaf36911f3` | `8789:5000` |

## Volumes

| Service | Volume |
|---|---|
| `libreseerr` | `./data:/app/data` |
| `libreseerr` | `./app.py:/app/app.py:ro` |
| `libreseerr` | `./readarr.py:/app/readarr.py:ro` |

## Environment (`.env`)

Variable names from `.env.example` — real values live in `.env` on the host, sourced from the vault (never committed):

- `TZ`
- `SECRET_KEY`
- `NTFY_TOKEN`

## Troubleshooting

- **Book request fails with a 400 or gets "stuck" (never lands in Readarr); Readarr rejects the phantom author with a 404.** — This is the junk-edition bug: upstream picks readarr_books[0] which can be a garbage rreading-glasses/Goodreads user edition. It is fixed by the bind-mounted ./app.py + ./readarr.py patch (candidate re-ranking + retry-until-accepted). Confirm both files are still mounted read-only in compose.yaml and present in the container; the ranking logic lives around app.py line ~1017.
- **After an image bump, book requests regress to 400s / junk editions again.** — The patch lives ONLY in the bind-mounted app.py/readarr.py, not in the upstream image. Every image bump can ship a new app.py signature — re-derive (re-apply) the local patch against the new upstream app.py before recreating. Marker comments in the code: "local patch (libreseerr-diagnosis 2026-07-12); re-derive on image bump" and "local patch (fix-25)" (the `_ensure_author_monitored` author-monitoring fix in readarr.py — without it requested books vanish from wanted/missing and are never re-searched).
- **A request sits 'processing 0%' forever with zero Readarr history — the first search found nothing and nothing ever retries it.** — Quality-gate H6/H16 (fix-25, 2026-07-17): upstream added authors with addOptions.monitor="none", which also sets author.monitored=False, and Readarr's wanted/missing EXCLUDES books whose author is unmonitored — so a no-result first search was permanent. The bind-mounted readarr.py now forces author.monitored=True on every add/match path (books stay selectively monitored; monitorNewItems stays "none"). The `arr-orphan-monitor-flags` verification check fires if the flag combination ever reappears; the request itself completes as soon as an indexer has the book.
- **`docker compose pull` fails with "manifest unknown", or `up -d` won't start after an app.py edit.** — Do NOT pin the local image ID (the 2026-07-09 audit mistakenly pinned ID c2dbf74a, which is not pullable — corrected 2026-07-12 to manifest digest 820134e4). Keep the sha256 MANIFEST digest in compose.yaml. To recreate offline after an app.py change without pulling: `ssh mini 'cd /opt/stacks/libreseerr && docker compose up -d --pull never'`.
- **Container won't start, complaining SECRET_KEY is unset.** — `SECRET_KEY` is required (compose uses `${SECRET_KEY:?...}`). It must exist in /opt/stacks/libreseerr/.env on the mini (sourced from the vault). Generate once with `openssl rand -hex 32` — a stable value keeps sessions from invalidating on restart.
- **Requests are accepted in Libreseerr but nothing downloads.** — Libreseerr only hands off to Readarr on the NAS (http://192.168.10.4:8787). Check Readarr itself — confirm the book is monitored and searched, and that the indexer/download-client chain is healthy. Verify connectivity from the mini container: logs should show `GET /api/v1/book HTTP/1.1 200`.
- **Dashboard shows a request 'processing 0%' days after the book was imported, or 'completed 100%' for a book that is not actually in the library.** — Quality-gate H15/M36 (fix-26, 2026-07-17). Upstream only reconciled statuses when the UI POSTed /api/requests/refresh, and swallowed every exception — so the dashboard rotted whenever nobody had the page open. The bind-mounted app.py now runs a background reconciler (marker: "Background request reconciler (M36)"): one gunicorn worker (fcntl-lock winner on data/.reconciler.lock) re-checks every non-terminal request against Readarr every RECONCILE_INTERVAL seconds (default 900) and logs failures instead of swallowing them. It also detects two rot states and marks the request 'error' with an explanation: the Readarr book was deleted after the request (dangling), or the book is unmonitored with no file (nothing will ever search for it). The false-'completed' shape came from a junk-edition mis-import: Readarr matched a "Naamah's Curse" grab to a misspelled duplicate Goodreads edition record — if a book keeps reverting to a junk edition on author refresh, pin the correct edition in Readarr by monitoring it and setting the book's anyEditionOk=false (API: PUT /api/v1/book/{id} with editions[] + "anyEditionOk": false); refresh then keeps the choice. Hourly tripwires: `libreseerr-request-rot` and `seerr-request-rot` in verification/checks.d/media.yaml compare stored request statuses against live backend truth and alert to ntfy if the dashboards lie again.
- **A request errors immediately (400 "A book with this ID was not found" / timeout / "Could not find author"), sits in 'retrying', or you received a "Book request failed" ntfy push.** — Books-stack scan B8–B12 (fix-48, 2026-07-20) — see the [request-path runbook](../runbooks/books-requests.md). The bind-mounted app.py/readarr.py now: adopt an existing library record before any lookup (canonical work often already present while the lookup returns only junk editions); never POST an Open Library id as foreignBookId (permanent error + ntfy instead); run Readarr lookups with READARR_TIMEOUT=60s under gunicorn --timeout 300 (the 15s hard-code + 30s worker default caused the 07-18 burst failures); match author names unicode/HTML-entity/date-insensitively (Emily Brontë); auto-retry transient failures 5x via the reconciler and re-trigger BookSearch every ≥6h up to 4x for monitored-no-file books before failing loudly. Every terminal failure pushes to ntfy topic `books` (token: vault ntfy.libreseerr_token, NTFY_TOKEN in .env). Tripwires: `libreseerr-request-stuck` and `libreseerr-request-path-guards` in verification/checks.d/reading.yaml.

## Operations

```bash
ssh mini 'cd /opt/stacks/libreseerr && docker compose ps'
ssh mini 'cd /opt/stacks/libreseerr && docker compose logs --tail 50'
ssh mini 'cd /opt/stacks/libreseerr && docker compose pull && docker compose up -d'
```

Update procedure: [Runbooks → Update images](../runbooks/update-images.md). Full add/change loop: [Runbooks → Add a service](../runbooks/add-a-service.md).

*Generated by `scripts/docs/gen-wiki-services.py` — do not edit by hand; edit the compose file and regenerate.*
