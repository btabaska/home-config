# Meme Review

Self-hosted app for a small household to send each other stacks of images and
react to them one at a time, iMessage-tapback style. Built from the Claude Design
prototype (`Meme Review.dc.html`) and the build spec in **[HANDOFF.md](./HANDOFF.md)**
(imported below for reference).

- **Server** — Node + [Hono](https://hono.dev), SQLite via Node's built-in
  `node:sqlite` (no native build step). Serves the API and the static SPA.
- **Client** — Vite + React SPA, faithful to the prototype and the Nocturne
  design tokens (`web/src/nocturne.css`).
- **Realtime** — SSE at `/api/stream`; both people watching a drop see reactions
  land live, and achievement unlocks pop in.
- **Immich** — optional browse source (asset IDs referenced, thumbnails proxied
  server-side so the API key never reaches the browser). Local upload is the
  fallback and works with Immich disabled.

## Quick start

```bash
cd meme-review
cp .env.example .env            # edit SESSION_SECRET (and Immich, optionally)
npm install
npm run seed                    # demo users + drops (handles: you / sam, pw: meme)
npm run dev                     # server :8787 + Vite client :5173
```

Open <http://localhost:5173>, sign in as **you** / **meme**. Drop #6 (from Sam)
is waiting to be reviewed; the older drops populate History, Stats and Badges.

### Production (single process)

```bash
npm run build                   # bundles the SPA to ./dist
npm start                       # Node serves API + SPA on :8787
```

Put Caddy in front with the provided **[Caddyfile](./Caddyfile)** for HTTPS on the
LAN (needed for PWA install + clipboard). Point `root` at this repo's `dist/`.

## Configuration (`.env`)

| var | meaning |
| --- | --- |
| `PORT` | API + static port (default 8787) |
| `DATA_DIR` | SQLite DB, uploads, and Immich thumbnail cache (default `./data`) |
| `SESSION_SECRET` | session cookie secret — set a long random string |
| `COOKIE_SECURE` | `true` behind HTTPS |
| `IMMICH_BASE_URL` / `IMMICH_API_KEY` / `IMMICH_DEFAULT_ALBUM_ID` | optional; also settable at runtime in Settings |
| `GUEST_REACTIONS` | `members` (default) or `guests` |

## Data model & API

Full schema and route list live in **[HANDOFF.md](./HANDOFF.md)** §3–§5. The DB is a
single SQLite file (`data/meme-review.sqlite`, WAL) — easy to back up.

### Screens (all wired to the API)

Inbox · Compose (Immich/Upload) · Review deck · Summary · Sender grid · History ·
Stats · Achievements · Settings · Activity · Login.

### Achievement engine (`server/src/achievements.ts`)

Definitions live in code; unlocks live in the DB. All eight v1 rules from
HANDOFF §6 are evaluated against the event stream after every event
(`boomerang`, `mega_drop`, `evergreen`, `skull_merchant`, `novelist`,
`same_brain`, `speedrun`), plus an hourly sweep for the one time-based rule
(`left_on_read`). Unlocks emit `achievement.unlocked` over SSE → the popup.

## Notes / deviations from the spec

- **Passwords** use Node's `scrypt` (salted, timing-safe) rather than argon2id,
  to avoid a native dependency. Swap in argon2 if you prefer.
- **Image sizes** — originals are never re-encoded. Uploads are served as-is for
  every size; Immich renditions are proxied and disk-cached (`data/cache`).
  Drop in `sharp` if you want true local thumbnailing.
- **GIFs** — searched from a local `data/gifs` folder (HANDOFF §9's self-hosted
  option). Swap `server/src/routes/gifs.ts` for a provider proxy if wanted.
- **Notifications** are deliberately out of scope — the share link is the
  notification (HANDOFF §7).

## Homelab deployment sketch

This drops cleanly onto the `mini` Docker host or runs as a systemd unit; put it
behind Caddy at `memes.tabaska.us` and point `IMMICH_BASE_URL` at the NAS Immich.
Back up `data/meme-review.sqlite` with the existing restic job.
