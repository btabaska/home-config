# research.md → roadmap integration

How the 4 areas of `research.md` were reconciled into the plan on **2026-07-14**
(operator decisions, grounded against the live fleet first). New tasks are tracked
here (the companion-doc pattern, like `hardware-shopping-list.md`) rather than
hand-edited into the 223-task `index.html`; `progress.json` carries the state
changes to *existing* tasks.

## ✅ Done live this session (hygiene / decided)
- **RomM pinned** `:latest` → `:4.9.2` (`configs/docker-stack/stacks/romm/compose.yaml`, redeployed) — stops a surprise jump onto the 5.0 redesign/beta (sync API changed).
- **RomM functional health probe** `romm-serving` added (`checks.d/mini-services.yaml`, warn) — heartbeat + version, proves it SERVES not just runs. Was container-presence only.
- **Stale Caddyfile vhosts removed** — `maintainerr` (removed 2026-07-08) + `deptrack` (Dependency-Track retired 2026-07-09); Caddy validated + reloaded live (vault/romm still 200).
- **Runbook fix** — `add-a-service.md` Caddy snippet `import cloudflare_tls` → `import local_tls` (matches the live file).
- **`docker-14` CLOSED as delivered** (`progress.json`) — static + dynamic + NAS-by-IP + auto-Tailscale Caddy hosting are all live; the **Coolify PaaS half was DROPPED** (bundled Traefik fights Caddy for 80/443 + idles ~1 GB → non-starter on the 8 GB mini, which sits at ~343 MB free). Dokploy noted for a future *dedicated* box only.
- **`game-12` un-deferred** — the Ludusavi+Syncthing save-sync folds into the new Syncthing-hub task below.
- **research.md corrected** — Immich `v3.x`→`v2.7.5`; RomM `./assets` IS already in the mini restic→B2 backup (its "single point of loss" / hygiene-win-#3 was stale — the gap is cross-device *sync*, not backup).

## 📋 New tasks — tracked, build later (per decisions)

### §2 FOSS desktop suite (decision: add all as tracked tasks)
| ID | Title | Track | Effort | Notes |
|---|---|---|---|---|
| `foss-01` | Bitwarden → Vaultwarden **data cutover** (point clients at `vault.tabaska.us`) | security | 1–2 h | Server is LIVE; the data migration was an untracked phantom ("Task 06"). Add `rbw` CLI on rig. |
| `foss-02` | Package the FOSS desktop suite — `cachyos-desktop-suite.sh` + macOS `Brewfile` (chezmoi-tracked) | desktop | ~½ day | Extends `glue-02`; the app list in research.md §2 (confirm before codifying; rig runs proprietary VS Code → swap to VSCodium or accept exception). |
| `foss-03` | Syncthing v2 hub on NAS + mini node (local-first file sync) | desktop | ~½ day | Replaces Proton Drive; the shared dependency for `game-12` retro save-sync. Mind the mini's ~350 MB-free ceiling — hub belongs on the NAS. |
| `foss-04` | Ente Auth adoption + YubiKey enrollment (Authy migration) | security | 1–2 h | Relates to `sec-01` (which is broad 2FA); Authy has no export → manual re-enroll. |

_Also parked (file if/when the suite is packaged): self-host adds behind Caddy — Stirling-PDF, LibreTranslate, PicoShare, self-hosted Firefox Sync._

### §3 Retro (decision: hygiene now + track the build)
| ID | Title | Track | Effort | Notes |
|---|---|---|---|---|
| `retro-08` | RomM **RetroAchievements dashboard** (view-only unlock %/hardcore stats) | retro | ~15 min | Needs the operator's RetroAchievements **username** + `RA_API_ENABLED=true`. Earning RA requires standalone RA-capable cores (make the rig the primary RA device). |
| `game-12` | Save-sync — **Syncthing hub (Layer 2)** covering the rig + save-states | gaming | ~½ day | Un-deferred. Rides `foss-03`. Steam-Deck native layer (`decky-romm-sync`) is gated on `retro-07` (no handheld owned). |

### §4 Public trackers (decision: FULL — indexers + Bitmagnet + Whisparr)
> ⚠️ **Gate:** research.md's per-tracker liveness/definition verification did **not** complete. Spot-check each tracker's domain + Prowlarr definition **before adding**.

| ID | Title | Track | Effort | Notes |
|---|---|---|---|---|
| `seed-11` | Public-indexer coverage layer in Prowlarr | seed | ~30–45 min | Fix the verified "IPT ~0 TV grabs" gap first with **EZTV + The Pirate Bay** (no Cloudflare solver), then **Nyaa + SubsPlease** (anime; enable Sonarr anime mode). Keep TRaSH/recyclarr gating tight. |
| `seed-12` | Bitmagnet self-hosted DHT crawler on NAS (rate-limit-proof hedge) | seed | ~1 h + runbook | No query cap, no Cloudflare, nothing to seize. Full add-a-service runbook (compose + Caddy + catalog + monitoring + coverage). |
| `seed-13` | Whisparr adult-acquisition pipeline (sukebei/XXXClub → Stash) | seed | ~an afternoon + runbook | Stash (v0.31.1) is manual today; Whisparr automates it. Small NAS container + one Caddy vhost. |

_Hygiene also worth doing with `seed-11`: consider swapping FlareSolverr → **Byparr** (same JSON API) — but that's an unverified "FlareSolverr-broken-vs-modern-CF" claim; spot-check first, low urgency._

## Full source
The verbatim research (verified current-state, snippets, per-indexer table, source URLs) stays in **`research.md`** at the repo root. This file is the reconciliation/decision layer; grounding was done by a 4-agent live-verification pass 2026-07-14.
