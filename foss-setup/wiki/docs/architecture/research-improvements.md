# Research — improvement areas

> Design/research survey of four homelab improvement areas (self-hosted web hosting, FOSS desktop suite, retro save-sync/RetroAchievements, public *arr trackers) — now the source of truth for their rationale, options, and decisions.

_Source: `research.md` · migrated + validated 2026-07-14._

**Status:** Research + planning, **integrated into the roadmap 2026-07-14** (operator decisions). Where each area landed is recorded in `foss-setup/docs/research-integration.md`; the live tracker (`foss-setup/docs/index.html` `taskData` + `foss-setup/docs/progress.json`) is the task source of truth. Summary of the integration:

- **§1 Caddy hosting → `docker-14` CLOSED as delivered** (static + dynamic + NAS-by-IP + auto-Tailscale all live; the optional **Coolify PaaS half was DROPPED** — non-starter on the 8 GB mini). Stale `maintainerr`/`deptrack` vhosts cleaned + the runbook `import` fixed, all live.
- **§2 FOSS suite → 4 tracked tasks to build later** — `foss-01` Vaultwarden data cutover, `foss-02` suite packaging, `foss-03` Syncthing hub, `foss-04` Ente Auth + YubiKey.
- **§3 Retro → hygiene done live** (RomM pinned + functional health probe) **+ tracked build** — `retro-08` RetroAchievements dashboard, `game-12` save-sync (un-deferred).
- **§4 Trackers → FULL path chosen** — `seed-11` public indexers, `seed-12` Bitmagnet, `seed-13` Whisparr — **pending per-tracker liveness spot-check**.

**Provenance / trust caveats:**

- Current-state facts came from a repo scout of `foss-setup/**` and a 2026-07-14 live-verification pass; they are reliable.
- External 2026 facts came from a fan-out web-research pass. The **retro / RomM** facts are corroborated across three independent briefings (high confidence). The **Caddy/PaaS** and **FOSS app** facts had a fact-check pass applied.
- The **adversarial per-tracker verification pass did NOT complete** (session token limit). The tracker table in §4 is from research agents + operator knowledge, not a second skeptical check. **Spot-check each tracker's domain / status / Prowlarr definition before adding.**

**Key repo files referenced throughout:**

- Caddy edge: `foss-setup/configs/docker-stack/stacks/caddy/caddy/Caddyfile`
- Add-a-service runbook: `foss-setup/wiki/docs/runbooks/add-a-service.md`
- Service catalog: `foss-setup/configs/docker-stack/service-catalog.yaml`
- Rollout tracker: `foss-setup/docs/progress.json`, `foss-setup/docs/index.html`
- RomM stack: `foss-setup/configs/docker-stack/stacks/romm/compose.yaml`
- *arr stack: `foss-setup/configs/nas/media-automation/docker-compose.yml`
- Rig baseline installer: `foss-setup/scripts/setup/cachyos-desktop-baseline.sh`
- FOSS narrative (partly stale): `foss-setup-plan-2.md`. The raw research docs (`docs/research/*`, incl. the ethos and devices notes) were retired 2026-07-14 — this page + `research-integration.md` are their synthesis; the durable house/device context lives at `reference/home-assistant/home-context.md` and the full audit at `operations/audit-2026-07.md` (raw docs remain in git history).

Each section is self-contained: *verified current state* (with repo file references) → *gap* → *recommendation* → *concrete steps/snippets* → *effort* → *open decisions*. Version-sensitive external facts (tracker liveness especially) drift fast — re-verify before executing.

---

## 1. Basic web hosting behind Caddy

**Verdict: this capability already exists and runs in production** — and as of 2026-07-14 `docker-14` is **CLOSED as delivered**. Adding an app is following an existing runbook, not net-new work.

### Verified current state

- **Caddy is LIVE on the `mini`** (Mac mini → Ubuntu Server 22.04, **8 GB soldered RAM = hard ceiling**, ~38 containers, `192.168.10.2`). Custom `xcaddy` image with the `caddy-dns/cloudflare` module.
- Fronts ~40 services at `https://<name>.tabaska.us` with **real Let's Encrypt wildcard certs via Cloudflare DNS-01** (snippet `(local_tls)` in the Caddyfile — despite the name these are publicly-trusted LE certs; nothing is port-forwarded except game ports).
- Both AdGuard instances wildcard-rewrite `*.tabaska.us` → mini IP, so **every service resolves on the LAN AND over Tailscale** with a valid cert automatically.
- **A static file-server already runs in production:** `wiki.tabaska.us` uses `root * /srv/wiki; file_server` (`Caddyfile` ~lines 352–356), bind-mounted from `/opt/stacks/wiki/site`.
- Documented process exists: `foss-setup/wiki/docs/runbooks/add-a-service.md` (9-step checklist; the 100%-coverage tripwire fails the sweep on any un-manifested container).
- **NAS = Synology DS920+, DSM 7.x (7.4 current as of June 2026), Container Manager (Docker), 20 GB RAM.** Deliberately **NOT** in the ansible/config-as-code loop (DSM resets system files on update). Caddy fronts NAS services **by IP** (`{$NAS_IP}`), not container name.

### Corrections folded in (2026-07-14)

- **`docker-14` is now DONE**, not "planned/unstarted." Static + dynamic + NAS-by-IP + auto-Tailscale Caddy hosting are all live; the optional **Coolify PaaS half was DROPPED** (see recommendation below).
- The **stale Caddyfile blocks were cleaned live** — `maintainerr` (removed 2026-07-08) and `deptrack` (Dependency-Track retired 2026-07-09) vhosts removed; Caddy validated + reloaded (vault/romm still 200).
- The **runbook snippet was corrected live** — `add-a-service.md` now says `import local_tls` (was `import cloudflare_tls`), matching the live file.

### Gap

None, really — `docker-14` was ~90% satisfied by the existing pattern and is now closed. The only decision it raised was the optional Coolify PaaS layer (dropped, below).

### Recommendation & concrete steps

**(a) Static HTML / SPA app — ~10–20 min, ~0 RAM.**

```caddyfile
myapp.{$DOMAIN} {
    import local_tls          # live Caddyfile uses local_tls (NOT the runbook's old cloudflare_tls)
    root * /srv/myapp
    file_server
    try_files {path} /index.html   # SPA fallback for React/Vue/Svelte routers
}
```

Bind-mount the content into the Caddy container the same way `/srv/wiki` is mounted (see caddy `compose.yaml`), then `docker compose up -d`. No AdGuard change needed. Prefer a throwaway `nginx:alpine` / `caddy:2-alpine` container instead only if the app has its own build lifecycle you want versioned separately, or you don't want its files inside the security-sensitive edge container.

**(b) Dynamic containerized web service — ~30–60 min** (most of it is catalog/homepage/wiki/monitoring hygiene, not the app):

```yaml
# configs/docker-stack/stacks/myapp/compose.yaml
services:
  myapp:
    image: org/myapp:1.2.3        # pin exact tag; Diun watches it
    container_name: myapp
    restart: unless-stopped
    networks: [edge]              # lets Caddy proxy by container name
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
networks:
  edge: { external: true }
```

```caddyfile
myapp.{$DOMAIN} { import local_tls; reverse_proxy myapp:8080 }
```

Then complete the runbook: `.env.example`, service-catalog entry, homepage tile, `gen-wiki-services.py` + `build-wiki.sh`, Uptime-Kuma monitor + `checks.d/` probe + add the container to `verification/coverage/mini.containers`, commit + `compose up`.

**Where to run it — the 8 GB mini ceiling is the deciding factor** (a live check on 2026-07-14 showed only ~200 MB free on the mini):

| Put it on the **mini** if… | Put it on the **NAS** (20 GB) if… |
|---|---|
| Light (tens–hundreds MB), static, or small Go/Rust binary | Heavier (Java/big Node/ML), bundles its own Postgres/Redis |
| Wants container-name routing + auto-DNS for free | **Data-adjacent** (next to media/photos/docs on the NAS) |

`free -m` on the mini before adding anything. **Default anything non-trivial to the NAS**, deployed via Container Manager, fronted by IP:

```caddyfile
myapp.{$DOMAIN} { import local_tls; reverse_proxy {$NAS_IP}:PORT }
```

Coverage manifest for NAS containers is `verification/coverage/nas.containers`.

**Synology-on-NAS specifically:** **use Container Manager, skip Web Station.** Web Station (DSM 7.4) still only does nginx/Apache + PHP with a poor rewrite story, and it lives outside your repo + monitoring. Don't run a reverse proxy *on* the NAS (DSM's own nginx holds 80/443/5000/5001) — the off-box Caddy hitting `NAS_IP:port` never collides. (PHP 8.3/8.4 are now installable DSM packages, but this doesn't change the recommendation.)

**Tailscale:** already covered for free — any new `myapp.tabaska.us` is reachable over the tailnet with a valid cert the moment the vhost exists; no `tailscale serve` needed. `tailscale funnel` is the only added capability = expose ONE app to someone NOT on the tailnet (Funnel = public internet, ports 443/8443/10000 only). **Never Funnel a data-bearing or admin app** — the tailnet trust boundary is gone; security collapses to that app's own auth.

**Coolify was DROPPED from `docker-14` (decided 2026-07-14).** It bundles its own Traefik that fights Caddy for 80/443 and idles at ~0.5–1.2 GB before deploying anything — a non-starter on the mini (which sits at a few hundred MB free). The compose+vhost runbook already gives git-tracked "one-click-ish" deploys with zero extra proxy overhead. (If a PaaS is ever wanted on a future *dedicated* box, Dokploy is the lightest — but not here.)

### Effort

Static: ~15 min. Dynamic on mini or NAS: ~30–60 min. Tailscale exposure: 0 (automatic). `docker-14` is delivered.

### Open decisions

- *(Resolved 2026-07-14)* Rescope `docker-14` (drop the Coolify half) → **done, closed as delivered.**
- *(Resolved 2026-07-14)* Clean up the stale `maintainerr`/`deptrack` Caddyfile blocks → **done live.**

---

## 2. Open-source-first desktop software suite

**Verdict:** most *decisions* are already made and several are live. The real gap is **packaging** — there is no single "install my whole FOSS desktop by default" manifest for the rig, and none for the MacBook. Tracked as `foss-01`…`foss-04` (build later).

### Verified current state

- **Rig = CachyOS (Arch), i7-12700K / RTX 3090 Ti / 64 GB, on 24/7** — daily-driver + gaming + local LLM stack (separate `local-ai-tooling` repo) + game servers. Installs via `pacman` + AUR (`paru`) + Flatpak + chezmoi dotfiles. `ansible-pull` runs for *maintenance* but does **not** install desktop apps.
- Only desktop installer today: `foss-setup/scripts/setup/cachyos-desktop-baseline.sh` = browser (Firefox / optional LibreWolf / Zen) + LibreOffice + sets Kagi default. Everything else is scattered per-task `pacman -S`. **No unified suite, no macOS Brewfile.**
- **Already LIVE:** Vaultwarden on mini (`vault.tabaska.us`, v1.36.0); Immich on NAS (**v2.7.5** — corrected 2026-07-14; the earlier "v3.x" was drift, Immich is on the 2.x line).
- **Already decided in research (not yet done):** 2FA = **Ente Auth + YubiKey** (tracked `foss-04`, relates to broad-2FA `sec-01`); local-first files = **Syncthing v2 hub on NAS** (+ mini node, iOS = Synctrain), tracked `foss-03`. **Nextcloud was considered and RETIRED**; Seafile not adopted.
- **Kept (deliberate):** Protonmail, Kagi, iOS, iMessage (no FOSS fix), Obsidian + paid Sync.
- **Pending cutovers:** Bitwarden data → Vaultwarden (tracked `foss-01`; the old "Task 06" was an untracked phantom — server is LIVE, only the data migration remains); Authy → Ente Auth (`foss-04`, Authy has no export → manual re-enroll); Proton Drive → Syncthing hub (`foss-03`).
- `foss-setup-plan-2.md` is partly stale (still says "stay on Bitwarden," still lists Nextcloud) — trust the research docs + wiki over it.

### Locked-in list, reconciled

| Item | Status | Action |
|---|---|---|
| Protonmail | Keep | FOSS client: **Thunderbird + Proton Mail Bridge** (GPLv3, local IMAP/SMTP). Proton's own desktop app is closed-source (Linux still beta). |
| Kagi | Keep | **Kagi browser extension** to lock default; **Orion** (by Kagi) best iOS browser (iOS forces WebKit). |
| iOS / iMessage | Keep (stuck) | No FOSS iMessage fix. **Signal** for non-Apple contacts; optional SimpleX / Matrix (Element). |
| Obsidian + Sync | Keep | **Quartz v5** to publish the vault as a static site (host behind Caddy per §1). Logseq can read the same vault as a pure-FOSS escape hatch. |
| Bitwarden → **Vaultwarden** | Server LIVE | **PENDING data cutover (`foss-01`).** Point official Bitwarden desktop/extension/iOS at the self-hosted URL; add `rbw` (Rust CLI) on rig. |
| Authy → **Ente Auth** | Decided, not done | **PENDING (`foss-04`).** Manual re-enroll (no Authy export). Register a **YubiKey** as the FIDO2 factor on the Ente account + crown-jewel logins. |
| Immich | LIVE on NAS (v2.7.5) | Desktop tooling: `immich-go` (import), `immich-cli` (scripted upload). One-time iCloud backfill: `icloudpd` → `immich-go`. |
| Proton Drive → local-first | Syncthing decided | **PENDING (`foss-03`).** Syncthing v2 hub on NAS + mini node + **Synctrain** on iOS. Add **PicoShare** (share links, the one thing Syncthing lacks) + **LocalSend** (AirDrop gap). |

### The suite (verified maintained + cross-platform in 2026)

Deliverable (`foss-02`): a new `cachyos-desktop-suite.sh` (extending the baseline) + a macOS `Brewfile`, both tracked in chezmoi like existing baselines.

**CachyOS / Arch:**

```bash
# --- Browsers (Gecko trio + one Chromium for the ~5% that break) ---
paru -S librewolf-bin zen-browser-bin brave-bin        # AUR hygiene: -bin only (lookalike RAT pkgs were pulled from AUR in 2025)
sudo pacman -S firefox                                  # compat baseline; only one in the official repo
# --- Passwords / 2FA (point at live Vaultwarden) ---
sudo pacman -S bitwarden rbw; paru -S ente-auth-bin
flatpak install flathub com.yubico.yubioath; sudo pacman -S pcsclite yubikey-manager; sudo systemctl enable --now pcscd
# --- Mail / messaging ---
sudo pacman -S thunderbird protonmail-bridge signal-desktop
flatpak install flathub chat.simplex.simplex im.riot.Riot   # SimpleX + Element (Matrix)
# --- Files / sync / share ---
sudo pacman -S syncthing; paru -S syncthingtray-qt6 localsend-bin
# --- Media clients (fit Navidrome / Miniflux / Plex / CWA) ---
sudo pacman -S mpv vlc calibre; paru -S supersonic-desktop
flatpak install flathub io.gitlab.news_flash.NewsFlash com.github.johnfactotum.Foliate
# --- Photos desktop (complements Immich; do NOT point both at the same tree destructively) ---
sudo pacman -S digikam darktable immich-go; paru -S immich-cli icloudpd
# --- Office / PDF ---
sudo pacman -S libreoffice-fresh okular xournalpp pdfarranger pandoc typst
# --- Creative "batteries" ---
sudo pacman -S gimp krita inkscape blender kdenlive obs-studio audacity flameshot
paru -S gpu-screen-recorder                              # ShadowPlay-style NVENC replay on the 3090 Ti
# --- Dev / power-user base ---
sudo pacman -S ghostty zellij neovim lazygit lazydocker starship ripgrep fd bat eza fzf zoxide yazi
paru -S vscodium-bin                                     # or: sudo pacman -S code (Code-OSS). Rig runs proprietary VS Code today → swap to VSCodium or accept the exception.
```

**macOS `Brewfile`:**

```ruby
cask "librewolf"; cask "zen"; cask "brave-browser"; cask "orion"
cask "bitwarden"; cask "ente-auth"; cask "yubico-authenticator"; brew "rbw"
cask "thunderbird"; cask "proton-mail-bridge"; cask "signal"; cask "simplex"; cask "element"
cask "syncthing-app"; cask "localsend"
brew "mpv"; cask "iina"; cask "vlc"; cask "calibre"; brew "immich-go"; brew "icloudpd"
cask "netnewswire"                          # NewsFlash is Linux-only; NetNewsWire covers Mac+iOS via Miniflux's Google-Reader API
cask "libreoffice"; cask "xournal++"; brew "pandoc"; brew "typst"
cask "gimp"; cask "krita"; cask "inkscape"; cask "blender"; cask "kdenlive"; cask "obs"; cask "audacity"
cask "ghostty"; cask "vscodium"
brew "zellij", "neovim", "lazygit", "lazydocker", "starship", "ripgrep", "fd", "bat", "eza", "fzf", "zoxide", "yazi"
```

**Self-host adds** (containers on mini/NAS behind Caddy per §1; parked — file when the suite is packaged):

- **Stirling-PDF** — self-hosted Acrobat replacement (50+ tools). Biggest single quality-of-life win.
- **LibreTranslate** — self-hosted offline DeepL/Google Translate.
- **PicoShare** — public share links (fills Syncthing's one gap).
- **Self-hosted Firefox Sync** (`syncstorage-rs`) — sync the Gecko trio without Mozilla.
- Optional: **SearXNG** (Kagi-independent fallback), a **YouTube frontend** (Invidious/Piped self-host + FreeTube desktop).

### Highest-value NEW additions from the ethical-software canon

(ResetEra thread is bot-blocked, but switching.software / PrivacyGuides / european-alternatives.eu give the same canon.)

1. Stirling-PDF · 2. LibreTranslate · 3. Organic Maps / OsmAnd (iPhone) · 4. YouTube frontend (Invidious/Piped + FreeTube) · 5. Self-hosted Firefox Sync.

### Effort

~half a day (`foss-02`) to write `cachyos-desktop-suite.sh` + `Brewfile` and wire into chezmoi. The 3 pending cutovers (`foss-01`, `foss-04`, `foss-03`) are separate, mostly-manual sessions.

### Open decisions

- Confirm the app list before it's codified (any you'd drop/add?).
- Do the pending cutovers now or defer? (The Syncthing hub `foss-03` also unlocks retro save-sync in §3.)
- macOS: Homebrew Brewfile confirmed as the mechanism? (No repo-managed Mac bundle exists today.)

### Notes / weaker spots (be honest)

- Immich has no native desktop client (web/PWA only) — desktop tooling is CLI/import only.
- `decky`-style launchers: Ueli (cross-platform) vs KRunner (KDE-native, already on the rig).
- JMP (Jellyfin Media Player) repo was archived March 2026 — fine but unmaintained; prefer mpv-based clients.
- Goldwarden (GTK Bitwarden client) development is paused — do NOT adopt; use official clients + `rbw`.

---

## 3. Retro ROMs: save-sync, RetroAchievements & multi-device play

**Verdict:** the "something on the Mini" is **RomM, and it's live**. The server isn't the gap — the gaps are (a) unpinned image + no functional health check *(both FIXED live 2026-07-14)*, (b) **saves aren't synced** off the mini, (c) **no RetroAchievements** dashboard, (d) no clean Steam Deck / Rig / 3DS play path.

### Verified current state (repo)

- **RomM LIVE on the mini** (`romm.tabaska.us`, `mini:8998`, image `rommapp/romm` **now pinned `:4.9.2`** — live-confirmed 2026-07-14 — `mariadb:11` sidecar). Tasks `retro-01`/`retro-02` done.
- ROMs on the NAS `games` CIFS share at `/mnt/share/Games/romm/roms/<platform>/` (BIOS in `bios/`). Saves/states stored LOCALLY on the mini at `./assets:/romm/assets`. **Correction 2026-07-14:** the `./assets` saves folder **IS already covered by the mini restic→B2 job**, so it is backed up off-box — the old hygiene-win-#3 ("back up `./assets`") is effectively DONE. The remaining gap is cross-device **sync**, not backup.
- Metadata via IGDB + Hasheous. Bundled EmulatorJS web player (no separate EmulatorJS deploy).
- **Verification** was container-presence only (`verification/coverage/mini.containers` lists `romm` + `romm-db`); a **functional health probe `romm-serving`** (heartbeat + version, warn) was **added live 2026-07-14** (`checks.d/mini-services.yaml`).
- Roadmap: `game-12` (save-sync via **Ludusavi + Syncthing**) was **un-deferred 2026-07-14** and now folds into the Syncthing-hub task (`foss-03`). RetroAchievements is now tracked as `retro-08` (view-only dashboard). `game-14` (launcher + library) remains deferred. The Steam-Deck native layer is gated on `retro-07` (no handheld owned — deferred).

### Corrected external facts (agreed across 3 independent 2026 briefings — high confidence)

- RomM stable = **4.9.2**; **save-sync shipped in 4.9.0** (not "5.0-beta" — 5.0 is a frontend redesign + controller support). Sources: github.com/rommapp/romm/releases, RFC-0001 (discussion #2199).
- RomM sync engine syncs **save files (SRAM/.srm) ONLY — not save states** (states are core+version-specific; explicitly out of scope). Modes: API (mature), File-Transfer (watch a Syncthing folder), Push-Pull (SSH). Conflict resolution is fragile "most-recent-wins" by default.
- RomM **has RetroAchievements built in but VIEW-ONLY** — displays unlock %/hardcore status (nightly sync from your RA username); you **earn** achievements only in a standalone RA emulator. EmulatorJS web player cannot unlock RA (open issue EmulatorJS #1016).
- **Steam Deck client:** `decky-romm-sync` (danielcopper, v0.26.1, active; pre-1.0, manual install) — imports library as Steam shortcuts, streams ROMs on demand, save-file sync (newest-wins + manual override), **launches via RetroDECK** (not EmuDeck). Requires RomM ≥ 4.9.0.
- **Rig/desktop-Linux:** RomM has **no first-party desktop client**. Options: indie `romm-retroarch-sync` (Covin90, actively developed one-dev beta, bidirectional saves+states) OR Syncthing file-transfer.
- **3DS:** no RA (RA 3DS build has no networking), no RomM sync client. Luma3DS + hShop healthy in 2026.

### Recommended architecture — two layers

No single tool covers server + Deck + Rig + 3DS for both saves *and* states, so split:

- **Layer 1 — RomM native save-sync** for the **Steam Deck** via `decky-romm-sync` (RomM is the server of record; authoritative save-file channel).
- **Layer 2 — Syncthing, mini = always-on hub** as the universal fallback that **also carries save states** and covers the **Rig** (no native client). Point RomM's **File-Transfer sync mode** at that Syncthing folder so the Rig ties in without a dedicated client. **This is `game-12` (Ludusavi + Syncthing) — and it reuses the Syncthing hub planned for FOSS files in §2 (`foss-03`).** Ludusavi = PC-game saves only.

### Per-device playbook

- **Steam Deck (cleanest):** RetroDECK (Flatpak) + Decky Loader + `decky-romm-sync` → `https://romm.tabaska.us`. ROMs stream on demand (NAS share never touches the Deck). Set conflict policy **manual/keep-both** for titles you care about. Populate `.../romm/roms/.../bios/` so DuckStation/PCSX2 cores work for RA. *(Gated on `retro-07` — no handheld owned yet.)*
- **Rig / CachyOS (weakest leg today):** **RetroArch** as engine (+ ES-DE only for gallery UX). Point ROM dirs at the NAS mount `/mnt/share/Games/romm/roms/<platform>/` (+ `bios/`) — no copying. Saves↔RomM via `romm-retroarch-sync` OR let the Rig's RetroArch save dir ride the Layer-2 Syncthing folder. Standalone DuckStation/PCSX2/Dolphin/PPSSPP where libretro cores fall short. **Make the Rig the primary RA-earning device.**
- **Nintendo 3DS (honest: manual only):** GB/GBC/NES + native GBA (`open_agb_firm`) + native DS (TWiLight Menu++); a **New** 3DS adds SNES/Genesis via standalone ports. **No RetroAchievements, no auto save-sync** — deliberate manual `.sav` copy. Satellite for the 8/16-bit slice only.

### RetroAchievements setup (`retro-08`)

One account at retroachievements.org; log in with the same credentials inside each RA-capable emulator (RetroArch/DuckStation/PCSX2/PPSSPP/Dolphin/Flycast/BizHawk); put just the RA **username** in RomM's profile (`RA_API_ENABLED=true`) for the dashboard. **Hardcore mode blocks *loading* save states** (creating them is allowed) → hardcore RA and cross-device *state*-sync are fundamentally at odds; only save-*file* continuity coexists with hardcore. 54 platforms supported as of 2026.

### Quick hygiene wins

1. **Pin the RomM image** to a `4.9.x` tag/digest — **DONE live 2026-07-14** (`:latest` → `:4.9.2`; stops a surprise jump onto the 5.0 redesign/beta or a sync-API shift).
2. **Add a functional health probe** — **DONE live 2026-07-14** (`romm-serving`, warn): heartbeat + version, proves RomM *serves* not just runs.
3. ~~**Back up `./assets`**~~ — **already DONE** (the saves folder is in the mini restic→B2 job; Syncthing is NOT a backup). Superseded by the cross-device *sync* gap (`game-12`).

### Effort

Hygiene ~1 hr *(done)*. Deck path ~an afternoon *(gated on hardware)*. Rig + Syncthing convergence ~an afternoon. 3DS = ongoing manual.

### What won't be clean (set expectations)

Save *states* don't roam reliably (core/version-specific; RomM even has EmulatorJS state bugs #2319/#1473). The Rig has no first-party RomM client. The 3DS is a dead end for RA and sync. RomM's sync engine is young (RFC still Draft, conflict resolution fiddly).

### Open decisions

- Layer-1+2 architecture as described, or Deck-only for now?
- Deploy the indie `romm-retroarch-sync` on the Rig, or keep the Rig purely on Syncthing?
- *(Resolved 2026-07-14)* Un-defer `game-12` (Ludusavi + Syncthing) and fold it into the §2 Syncthing hub → **done.**

### Source URLs

github.com/rommapp/romm/releases · github.com/rommapp/romm/discussions/2199 (RFC-0001) · docs.romm.app/4.9.0/using/retroachievements/ · github.com/danielcopper/decky-romm-sync · github.com/Covin90/romm-retroarch-sync · grout.romm.app/usage/save-sync/ · docs.retroachievements.org/general/emulator-support-and-issues.html

---

## 4. Public trackers for the *arr stack

**Verdict:** today only **IPTorrents + MyAnonamouse** (both private). Public indexers are a **coverage/redundancy layer** to fix the documented "IPT ~0 grabs" TV gap and add anime/adult — not a replacement for the private trackers. Chosen path = **FULL:** `seed-11` public indexers + `seed-12` Bitmagnet + `seed-13` Whisparr (all pending spot-check).

### Verified current state (repo)

- **Prowlarr 2.4.0 + FlareSolverr 3.5.0** on the NAS as the indexer manager, feeding **Sonarr / Radarr / Lidarr / Readarr** (Readarr EOL, kept alive via self-hosted `rreading-glasses`).
- Downloads route through off-site seedbox **"Betty"** (Bytesized AppBox, no root) running **Deluge** (per-app labels) + **slskd** (Soulseek) → rclone SFTP mount → copied to NAS. **Magnet-only public sites are fine.**
- **Current indexers = TWO, both PRIVATE: IPTorrents (TV/movies) + MyAnonamouse (music/books).** No public trackers, no anime indexer (no nyaa).
- Adult = **Stash** on the NAS (standalone **manual** organizer, v0.31.1, NOT wired into Prowlarr/arr). **No Whisparr.**
- **Documented gap:** IPT alone returns ~0 grabs on Sonarr Search-All for a large TV backlog; "a 2nd TV indexer is the real fix" — PENDING (`seed-11`). IPT is query-capped (~600/day).
- Add flow: Prowlarr UI → Add Indexer → tag FlareSolverr on CF-protected ones → **Settings → Apps → Full Sync** auto-pushes to all arrs. Don't add indexers directly in Sonarr/Radarr.

### Two cross-cutting 2026 realities

- **FlareSolverr is increasingly broken against modern Cloudflare** (even the successor Byparr's cookie-replay fails on sites like 1337x). **Prioritize indexers that need NO Cloudflare solver.** Consider swapping FlareSolverr → **Byparr** (same JSON API, repoint URL) as hygiene — but this is an unverified "FlareSolverr-broken-vs-modern-CF" claim; spot-check first, low urgency.
- **Public trackers carry far more fakes/mislabels/low-bitrate encodes** than IPT/MAM — lean on the existing recyclarr/TRaSH Custom Formats + Release Profiles; they also rate-limit under load.

### Recommended additions by category

> ⚠️ Liveness/definition status is from research + operator knowledge, NOT the (incomplete) adversarial verification pass. **Spot-check before adding.**

| Indexer | Feeds | Access | Prowlarr | Status | Verdict |
|---|---|---|---|---|---|
| **The Pirate Bay** | Sonarr + Radarr | public | built-in (apibay) | alive | **Recommend** — best all-round, **no solver** (do NOT tag with FlareSolverr — breaks the apibay test) |
| **EZTV** | Sonarr (TV only) | public | built-in | alive | **Recommend** — cleanest single fix for the ~0-grab TV backlog; usually no solver |
| **YTS** | Radarr (movies) | public | built-in | alive | **Recommend as filler** — small well-seeded encodes; scores low under TRaSH → fallback not primary |
| **Nyaa** | Sonarr (anime) + Radarr + Lidarr | public | built-in | alive | **Recommend** — *the* fix for the missing anime indexer; no Cloudflare. Enable Sonarr anime mode |
| **SubsPlease** | Sonarr (airing anime) | public | built-in | alive | **Recommend** — clean seasonal releases, ideal for hands-off auto-grab |
| **Bitmagnet** (self-hosted) | all arrs | you host it | Generic Torznab | alive | **Recommend as a hedge** (`seed-12`) — DHT crawler on the NAS: no query cap, no Cloudflare, nothing to seize. Insurance vs IPT's ~600/day cap |
| **1337x** | Sonarr + Radarr + Readarr | public | built-in **(needs solver)** | alive | **Caution** — best public catalog but Cloudflare-gated → flaky in 2026. Nice-to-have, not load-bearing |
| **AniDex** | Sonarr (anime) | public | built-in (needs solver) | alive | **Caution** — secondary anime / English fansubs |
| **Tokyo Toshokan** | Sonarr (anime) | public | built-in | alive | **Recommend as anime fallback** — stable Nyaa backup |
| **1337x / TPB (ebooks)** | Readarr | public | as above | alive | **Recommend** — best *public* books; but **MAM already covers books privately far better** |
| **AudiobookBay** | Readarr (audio) | public | **removed from Prowlarr** | unstable | **Caution** — ABB blocks Prowlarr's UA; needs community fork/custom YAML. MAM is the better answer |
| **RuTracker** | Radarr | semi-private (free signup) | built-in (needs solver) | alive | **Caution** — excellent for remux/foreign/older films; Cyrillic, needs account + solver |
| **sukebei.nyaa.si** | Whisparr (adult) | public | built-in | alive | **Recommend (adult)** — highest-volume public adult/JAV/hentai; no Cloudflare |
| **XXXClub** | Whisparr (adult) | public | built-in | alive | **Recommend (adult)** — main public Western option |
| **PornoLab** | Whisparr (adult) | semi-private (free signup) | built-in | alive | **Caution (adult)** — deepest catalog; Russian, needs account |

**Checked and rejected (so you know they were considered):**

- **TorrentGalaxy** — effectively dead since 2025 (persistent 502s, domain churn). Skip.
- **RARBG** — shut down 2023; Prowlarr's stale entry is broken (#2595). Skip.
- **TheRARBG** — site alive/well-stocked but **no working Prowlarr definition** in 2026 → would need custom Cardigann YAML (`dreulavelle/Prowlarr-Indexers`). Context only.
- **KickassTorrents / ExtraTorrent** — clones of dead brands, low-trust. Skip or gate hard.
- **Knaben / Bitsearch** — agents disagreed on whether these ship a built-in Prowlarr definition in your 2.4.0. **Verify**; if absent, add via custom Cardigann YAML. Both are useful DHT/aggregators if addable.

### Directly closing your gaps

- **"IPT ~0 grabs" TV fix (cheapest):** add **EZTV + The Pirate Bay** first — both TV-strong and **need no Cloudflare solver** → low-maintenance. Add **Bitmagnet** as the rate-limit-proof hedge. That's the flagged "2nd TV indexer."
- **Anime (net-new):** **Nyaa + SubsPlease**; enable Sonarr's anime handling. Optionally pair with **SeaDex** (`releases.moe` via `seadexarr`) to auto-pick AB-tier "best releases" that mostly live on public Nyaa.
- **Adult (net-new pipeline):** indexers alone aren't enough — the automation piece is **Whisparr** (`seed-13`, not deployed) feeding **sukebei/XXXClub** into the existing **Stash** (manual today). Whisparr = small NAS container + one Caddy vhost (§1 pattern). If you'd rather keep Stash manual, just add the indexers for search.

### How to add

Prowlarr UI → Add Indexer → tag **FlareSolverr/Byparr** only on CF-gated ones (1337x, AniDex, RuTracker) → **Settings → Apps → Full Sync**. Keep quality gating tight via recyclarr/TRaSH Custom Formats.

### Effort

~30 min for the no-solver built-ins (TPB/EZTV/YTS/Nyaa/SubsPlease/sukebei). Bitmagnet ~1 hr container. Whisparr pipeline ~an afternoon.

### Open decisions

- Add public indexers to the existing private-only setup, or keep it lean and only add the 2nd TV indexer (EZTV/TPB)?
- Deploy Whisparr + wire Stash into automation, or keep adult acquisition manual?
- Deploy Bitmagnet as the self-hosted hedge?
- Adopt Byparr in place of FlareSolverr?

_(2026-07-14 decision: the FULL path — `seed-11` indexers + `seed-12` Bitmagnet + `seed-13` Whisparr — was chosen and tracked, pending per-tracker spot-checks.)_

### Legal/quality note

Shadow libraries (Anna's Archive / Libgen / Z-Library) are direct-download, NOT Torznab indexers — they don't feed Readarr via Prowlarr (use LazyLibrarian/standalone downloaders) and carry active 2026 legal heat. Public trackers = more fakes/mislabels; quality profiles matter more than on private trackers.

---

## 5. Cross-cutting suggested sequencing

1. **Free wins first:** RomM image-pin + health probe (§3) **— DONE live**; RomM `./assets` backup **— already covered**; add the no-solver public indexers TPB/EZTV/Nyaa (§4, `seed-11`).
2. **Finish the already-decided FOSS cutovers:** `foss-01` (Vaultwarden data), `foss-04` (Ente Auth), `foss-03` Syncthing hub (§2) — the Syncthing hub also unlocks the retro Layer-2 save-sync (`game-12`).
3. **Package the suite:** `cachyos-desktop-suite.sh` + `Brewfile` (§2, `foss-02`).
4. **Bigger builds:** Steam Deck RetroDECK path (§3, gated on `retro-07`); Whisparr pipeline (`seed-13`) + Bitmagnet (`seed-12`) (§4); self-host adds (Stirling-PDF, LibreTranslate, PicoShare, self-hosted Firefox Sync).

**Reminder:** every new container must go through the full add-a-service runbook (compose + Caddy vhost + catalog + homepage + wiki + monitoring + coverage manifest) or the 100%-coverage tripwire fails the sweep. Respect the mini's 8 GB ceiling (only a few hundred MB free) — default heavier services to the NAS.

---
[← Architecture & design](index.md)
