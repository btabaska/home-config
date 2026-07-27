# meme-review

Meme Review — self-hosted image-reaction app (imported from a Claude Design

| | |
|---|---|
| **Host** | [mini](../hosts/mini.md) |
| **URL** | https://memes.tabaska.us |
| **Source** | `foss-setup/configs/docker-stack/stacks/meme-review/compose.yaml` |
| **Notes** | Self-hosted image-reaction app (meme-review-01) — send stacks of images and react to them one at a time, iMessage-tapback style. Hono + built-in node:sqlite server + Vite/React SPA; SSE realtime; 8-rule achievement engine; optional Immich browse source with local-upload fallback. Imported from a Claude Design prototype (Meme Review.dc.html + HANDOFF.md). LAN/tailnet only. |

## About

A self-hosted app for a two-person household to send each other stacks of
images and react to them one at a time, iMessage-tapback style — imported
from a Claude Design prototype (`Meme Review.dc.html` + `HANDOFF.md`) and
built end-to-end by `meme-review-01`. It lives on `mini` at
`/opt/stacks/meme-review/` (mirrored to
`foss-setup/configs/docker-stack/stacks/meme-review/`) and is fronted by
Caddy at https://memes.tabaska.us (real Let's Encrypt cert via DNS-01;
LAN/tailnet only — the `*.tabaska.us` AdGuard rewrite resolves it internally,
Cloudflare holds no A record). One container, **no native build step**: a
Node 24 image runs a **Hono** API + the built **Vite/React** SPA from the
same process, with SQLite via Node's built-in `node:sqlite` module and the
server running the TypeScript directly through `tsx`. It publishes no host
port — it joins the shared `edge` Docker network and Caddy reaches it by
container name (`meme-review:8787`). All state (SQLite DB, uploads, and the
Immich thumbnail cache) lives in the bind-mounted `./data`, which sits under
`/opt/stacks` and is therefore covered by the existing restic backup job.
The core loop: compose a **drop** (browse **Immich** albums — asset IDs
referenced, thumbnails proxied server-side so the API key never reaches the
browser — or fall back to local upload) → share its link → the recipient
swipes one image at a time with an always-visible reaction bar (emoji /
sticker / GIF / text reply, multiple per person, toggling removes) →
reactions and threads persist and never close. All eleven prototype screens
are wired (Inbox, Compose, Review deck, Summary, Sender grid, History, Stats,
Achievements, Settings, Activity, plus first-run/Login). **SSE** at
`/api/stream` makes reactions, threads and achievement unlocks land live for
both people. An **8-rule achievement engine** (`server/src/achievements.ts`)
— Boomerang, Mega Meme Drop, Evergreen, Skull Merchant, Novelist, Same Brain,
Speedrun, plus an hourly Left-on-Read sweep — evaluates the event stream and
unlocks pop over SSE. Auth is a session cookie (scrypt-hashed passwords, not
argon2, to avoid a native dep); the deploy ships with **no accounts** —
first visit to `memes.tabaska.us` shows a create-owner form, then the second
household member is added in Settings. Immich is optional and off by default
(upload-only); connect it anytime from the in-app Settings screen. Three
consumer-end verification checks (`meme-review.yaml`) probe the app *through*
Caddy — `/api/health`, the served SPA (not the "not built yet" fallback), and
a 401 on unauthenticated `/api/drops` — so a broken proxy, an unbuilt SPA, or
a dead API layer is caught rather than a bare "container running".

## Containers

| Service | Image (pinned) | Ports |
|---|---|---|
| `meme-review` | `(built from ./Dockerfile)` | — |

## Volumes

| Service | Volume |
|---|---|
| `meme-review` | `./data:/data` |

## Environment (`.env`)

Variable names from `.env.example` — real values live in `.env` on the host, sourced from the vault (never committed):

- `PORT`
- `DATA_DIR`
- `SESSION_SECRET`
- `COOKIE_SECURE`
- `IMMICH_BASE_URL`
- `IMMICH_API_KEY`
- `IMMICH_DEFAULT_ALBUM_ID`
- `GUEST_REACTIONS`

## Troubleshooting

- **memes.tabaska.us shows the plain-text "web client isn't built yet" message
instead of the app.** — The container is up but `dist/` is missing — the image build's `npm run
build` (Vite) didn't run or was wiped. Rebuild: `cd /opt/stacks/meme-review
&& docker compose up -d --build`. The `meme-review-spa-served` check catches
this (it asserts the `<title>Meme Review</title>` of the built SPA).
- **Can't sign in / no accounts exist on a fresh deploy.** — By design there are no seeded accounts. Open https://memes.tabaska.us and
the Login screen shows a "First run — create the owner account" form (driven
by `/api/config` `needsSetup:true`). After creating the owner, add the
second member from the in-app **Settings → Household → Add member**. To
reset entirely, stop the stack and delete `./data/meme-review.sqlite*`.
- **Immich albums are empty in Compose ("Immich not connected").** — Immich is optional and off by default (upload-only). Connect it in the app
at **Settings → Immich** (server URL + API key), or set `IMMICH_BASE_URL` /
`IMMICH_API_KEY` in `/opt/stacks/meme-review/.env` and `docker compose up
-d`. Thumbnails are always proxied through the server, so the key stays off
the browser.

## Operations

```bash
ssh mini 'cd /opt/stacks/meme-review && docker compose ps'
ssh mini 'cd /opt/stacks/meme-review && docker compose logs --tail 50'
ssh mini 'cd /opt/stacks/meme-review && docker compose pull && docker compose up -d'
```

Update procedure: [Runbooks → Update images](../runbooks/update-images.md). Full add/change loop: [Runbooks → Add a service](../runbooks/add-a-service.md).

*Generated by `scripts/docs/gen-wiki-services.py` — do not edit by hand; edit the compose file and regenerate.*
