# Smart-home (Home Assistant) design

> The "Home Hub" front-door website design — a static, non-technical catalogue of every home service (Watch / Listen / Read / Photos / Home / Request), grouped by task and styled like Apple.com circa 2012.
_Source: `foss-setup/docs/home-hub-design.md` · migrated + validated 2026-07-14._

!!! warning "Doc title vs content — read this first"
    Despite the section title **"Smart-home (Home Assistant) design"**, this page is the design spec for the **household front-door website ("Home Hub")** — a static catalogue that links out to every service. It is **not** the Home Assistant / smart-home platform design. Home Assistant appears here only as *one tile* in the catalogue. For the actual HA platform, see `foss-setup/wiki/docs/hosts/home-assistant.md` and the smart-home roadmap. (The mismatch is inherited from the migration assignment; content below is faithful to the real source.)

!!! note "Status: design **parked / aspirational** — not built"
    This front-door site is a **plan, not a deployed service.** `home.tabaska.us` is **currently served by the existing Homepage dashboard** (live: `home.{$DOMAIN}` → `homepage:3000` in the Caddyfile; the `home-01`..`home-04` catalogue tasks are done). Nothing in this doc has been built. Everything below is design intent unless a line explicitly says "live". If this ever ships, it either replaces Homepage as the default front door or sits beside it.

---

## Purpose

A **static website** that acts as the human-friendly front door to the home network. It is **not** a live dashboard (Homepage, Uptime Kuma, and Beszel already do that). Its one job: let a **non-technical household member** land on one page, understand *what services exist, what each one is for, and how to use it*, then click straight through to the app or its docs.

**Design language:** Apple.com circa 2012 (the Mountain Lion / iOS 6 era — Lion-silver global nav, thin gray Myriad headlines, glossy blue links with `›` chevrons, generous white space, hairline dividers). High-fidelity on desktop, simplified on mobile.

## 1. Goal & audience

**Primary user:** a member of the household who does not know (or care) what a "reverse proxy" is. They want to watch a movie, request a show, find the recipe app, or see the photos. They should never have to remember a subdomain or an IP.

**The site is the glue.** Everything is already running behind Caddy at `*.tabaska.us`. This site simply:

1. Presents every service as a friendly, captioned tile grouped by what the person is trying to *do* (Watch, Listen, Read, Photos, Home, Request…) — a pretty, bookmarkable **catalogue** of links.
2. Lets the person **pin** the services they actually use so those rise to a "Favorites" row at the very top — the catalogue learns their habits without any login.
3. Gives each service a **plain-language detail page**: what it is, when you'd use it, a 3-step "how to use it," and the buttons that matter — **Open the app**, **Request access / install the client**, **Docs**.

**The user never needs to know where anything is hosted.** No host map, no machine names, no IPs — that's deliberately hidden. (Host is kept as an internal field only, see §4.)

**Explicit non-goals:** no live metrics, no API keys, no auth, no server-side per-user state. If a service is down, that's Uptime Kuma's job, not this site's. Pinning is stored locally in the browser (`localStorage`) — no account needed. Keeping it a pure static site is what makes it "just work" and survive a rebuild.

## 2. Information architecture

```
/                         Home — Favorites row + grouped tile catalogue of every service
/s/<slug>/                Service detail page (one per service, generated)
/start/                   Getting started — first-time setup for a new person
                          (install Plex client, join Tailscale, bookmark this page)
/about/                   What this network is / who runs it / how to get help
```

Flat and shallow on purpose. Two clicks to anything: Home → a service. No hamburger mazes, no host map. The detail-page slug mirrors the service id in the data file (see §4), e.g. `/s/plex/`, `/s/immich/`, `/s/seerr/`.

**Navigation model**

- **Global nav (top):** the Apple-style silver bar. Left: a wordmark ("Home" / the household name). Center or right: links to Home · Getting started · Help. A search affordance (magnifying glass) on desktop that filters tiles client-side — optional, ship without it if time-constrained.
- **In-page jump nav on Home:** a sticky sub-row of category anchors (Favorites, Watch, Listen, Read, Photos, Home, Request) — mirrors Apple's secondary nav under the global bar.
- **Footer:** multi-column sitemap (every service grouped by category) + a fine-print line. This doubles as a full text index for anyone who prefers a list.

## 3. Page specifications

### 3.1 Home (`/`)

1. **Global nav bar** (silver gradient, hairline bottom border).
2. **Hero band** (white, tall, centered): a short friendly headline + one-line subhead, e.g. *"Everything in the house, in one place."* / *"Pick what you want to do. We'll take you there."* No giant product photo needed — a single tasteful glyph or the household monogram is enough. One primary blue link: *"See what's here ›"* (scrolls to the grid). Keep it calm and roomy, like the 2012 product landing pages.
3. **Category jump row** (sticky secondary nav).
4. **Favorites row (pinned services)** — the first section on the page, directly under the hero. Shows the tiles the person has pinned, in pin order, with the same tile design. Hidden entirely when nothing is pinned yet (so a first-time visitor isn't shown an empty shelf — instead a faint hint: *"Tap the ☆ on any app to pin it here."*). See §3.6 for the pin mechanics.
5. **Tile grid, grouped by category.** Each category is a section with a thin gradient rule + small gray section title, then a responsive grid of service tiles. **Tile =** app icon (square, rounded), service name, a one-line plain-language caption, a `Learn more ›` affordance, and a **pin control (☆ / ★)** in a corner. The tile body is a link to the detail page; a secondary "Open ↗" on hover (desktop) jumps straight to the live app; the ☆ toggles favorite without navigating.
6. **Footer sitemap.**

### 3.2 Service detail (`/s/<slug>/`) — the core template

This page is where the "understand the app's use" requirement is satisfied. One generated page per service from the data file. Sections, top to bottom:

- **Header:** large app icon, service name, the category badge, and the one-line caption.
- **Primary actions (button row):**
  - **Open <Name> ›** → `url` (the live app behind Caddy).
  - **Get access / Install client ›** → `accessUrl` (e.g. Plex app download, "request a login," Tailscale join page) — only render if present.
  - **Docs ›** → `docsUrl` (upstream docs or an internal how-to) — only render if present.
- **"What it's for"** — 2–3 sentences, plain language, zero jargon.
- **"When you'd use it"** — a short bulleted list of real situations ("You want to watch a movie on the TV," "A show you want isn't in Plex yet").
- **"How to use it"** — a numbered 3–5 step quick-start. This is the most important block; write it for someone who's never seen the app.
- **"Good to know"** — caveats in friendly terms (e.g. *"Works at home or on the road as long as you're on the family VPN," "Books only load on the home Wi-Fi or VPN"*). Pull from real constraints (Calibre-Web is LAN/VPN-only, etc.). **Keep these user-facing only — never mention which machine it runs on.**
- **Pin control** — a "★ Pin to favorites" / "★ Pinned" toggle near the action buttons, so a service can be pinned from its detail page too (same state as the Home tiles).
- **Related services** — 2–4 tiles (e.g. Plex ↔ Seerr ↔ Tautulli).

### 3.3 Pinning / Favorites (the one piece of interactivity)

The only dynamic behavior on the site. Pure client-side, no backend, progressive enhancement.

- **Storage:** an array of pinned service `id`s in `localStorage` (key e.g. `homehub:favorites`). Persists across visits and app restarts on that browser/device. No sync between devices — intentionally simple.
- **Pin control:** the ☆/★ on each tile and on each detail page toggles the id in that array.
- **Rendering:** on page load, a small inline script reads the array and (a) shows/populates the **Favorites** row at the top in pin order, and (b) sets the ★ filled-state on matching tiles. Optionally lift the "active" state on pinned tiles in the grid too.
- **Ordering:** Favorites appear in the order they were pinned (most-recent last, or top — pick one; document it). A future nicety (not v1): drag to reorder.
- **No-JS fallback:** if JavaScript is off, the Favorites row simply doesn't appear and every tile/link still works — the catalogue degrades gracefully.
- **Reset:** a tiny "Clear favorites" text link in the footer or at the end of the Favorites row.

### 3.4 Getting started (`/start/`)

Linear checklist for onboarding a new household member: bookmark this page, install the Plex app on your phone/TV, join the family VPN (Tailscale), how to request a movie, where to ask for help. Written as numbered steps with the same blue `›` link style.

### 3.5 About / Help (`/about/`)

One screen: what this network is, the "set-and-forget" philosophy in one friendly paragraph, and how to get help (who to message; link to ntfy/status page for the technical owner only). Keep it warm and short.

## 4. Content model — one data file is the source of truth

**Decision (made for maintainability):** the entire site is generated from a single structured data file, `src/data/services.yaml` (or `.json`). The author edits one file; Home, all detail pages, the footer sitemap, and the host map are generated from it. This mirrors the existing `gethomepage` config and is the easiest thing to keep in sync and to rebuild after a disk dies.

**Seeding:** pre-populate it from two files already in the repo — `foss-setup/configs/docker-stack/stacks/homepage/config/services.yaml` (names, icons, hrefs, captions) and `foss-setup/configs/docker-stack/stacks/caddy/caddy/Caddyfile` (the canonical subdomain → service routing). The plain-language "how to use it" prose is the only genuinely new writing required.

### 4.1 Schema (per service)

```yaml
- id: plex                    # → slug /s/plex/, stable key
  name: Plex
  category: watch             # one of the categories in §4.2
  icon: plex.png              # reuse Homepage's icon set (selfh.st / dashboard-icons)
  caption: Movies & TV, ready to play
  url: https://plex.tabaska.us        # the live app (behind Caddy)
  accessUrl: https://www.plex.tv/apps-devices/   # install client / request access (optional)
  docsUrl: https://support.plex.tv/                # docs / how-to (optional)
  host: nas                   # INTERNAL ONLY — never rendered to the user; kept so the
                              #   maintainer can find things. Do not surface in any page.
  audience: everyone          # everyone | adults | admin  (drives visibility/sorting)
  whatItsFor: >
    Your movie and TV library, streamed to the TV, phone, or laptop.
  whenToUse:
    - You want to watch something on the big TV.
    - You're travelling and want a movie on your phone.
  howToUse:
    - Open the Plex app on your device (or tap "Open Plex" above).
    - Sign in with the family account.
    - Pick something and press play.
  goodToKnow:
    - Works at home and away as long as you're signed in.
  related: [seerr, tautulli, immich]
```

Fields `accessUrl`, `docsUrl`, `goodToKnow`, `related` are optional and only render when present. `host` is metadata for the maintainer only and is **never shown to the user**. Everything else is required so a tile/detail page is never half-empty.

### 4.2 Categories (the "what do you want to do" grouping)

`watch` · `listen` · `read` · `photos` · `home` (smart home / household apps) · `request` (Seerr / MusicSeerr) · `admin` (technical, shown lower / on a toggle). These are user-task buckets, deliberately *not* the technical groupings ("Media stack," "Observability") used in the Homepage config.

### 4.3 Service catalog (draft — **verify against the live Caddyfile before generating**)

Domain is `tabaska.us`. The `host` column is **internal metadata for the maintainer only** (never shown on the site); it's listed here only so the catalog is easy to keep straight. **nas** = DS920+, **mini** = Mac mini/Ubuntu, **seedbox** = off-site (betty), **rig** = CachyOS, **ha** = Home Assistant Green box.

!!! warning "Catalog validated 2026-07-14 against the live Caddyfile + `progress.json` — several rows are stale"
    The original draft below was written 2026-07-07. Since then the roadmap has been pruned. Rows to fix before generating anything:

    - **LiteLLM (`llm`)** — host is **rig, not mini**. `llm.{$DOMAIN}` proxies to `{$RIG_IP}:4000`. "LiteLLM on mini" is a **phantom**; the whole AI stack (LiteLLM / Ollama / OpenWebUI / mcpo) is **rig-only** and lives in a separate `local-ai-tooling` repo. `ollama`, `ai` (OpenWebUI), and `mcpo` subdomains likewise proxy to `{$RIG_IP}`.
    - **Dependency-Track (`deptrack`)** — **FULLY RETIRED** (2026-07-11, user decision): 3 NAS containers removed, Kuma monitor + Caddy vhost + Homepage tile + manifest entries all deleted. **Drop this row.**
    - **Tdarr (`tdarr`)** — **not deployed / disabled**; the `tdarr.{$DOMAIN}` block is commented out in the Caddyfile (":8265 unreachable"). Also the source draft mislabels its host as `rig` — it was a NAS candidate. **Drop or mark not-deployed.**
    - **Maintainerr (`maintainerr`)** — stack dir deleted; **no live Caddy vhost** (stale vhost removed). Still appears in the Homepage config but is not routed. **Drop this row.**
    - **Frigate (`frigate`)** — **NOT DEPLOYED** (kept as a future plan only); the `frigate.{$DOMAIN}` block is commented out (":8971 unreachable"). Mark as planned, not live.
    - **Stash** (`stash` → NAS `:9999`, "Private") exists live but is **absent from this draft** — the draft is not exhaustive; the Homepage config / Caddyfile are the real inventory.

    Live-verified subdomains still correct as drafted: `plex, immich, books (calibre-web), music (navidrome), seerr, musicseerr, rss (miniflux), recipes (mealie), paperless, wallabag, ha (home-assistant, HA REST 200 live), ntfy, tautulli, pinchflat, sonarr, radarr, lidarr, dns (adguard), health (healthchecks), dockge, git (forgejo), status (beszel), uptime (uptime-kuma)`.

| id | Name | Category | URL (subdomain) | host *(internal)* | Plain-language caption | Validation note |
|---|---|---|---|---|---|---|
| plex | Plex | watch | plex | nas | Movies & TV, ready to play | ✅ live |
| immich | Immich | photos | immich | nas | All the family photos | ✅ live |
| calibre-web | Calibre-Web | read | books | nas | The ebook library *(home/VPN only)* | ✅ live |
| navidrome | Navidrome | listen | music | mini | Stream your music collection | ✅ live (mini container; music files mounted from NAS) |
| seerr | Seerr (Overseerr) | request | seerr | mini | Ask for a movie or show | ✅ live |
| musicseerr | MusicSeerr | request | musicseerr | mini | Ask for an album | ✅ live |
| miniflux | Miniflux | read | rss | mini | Your news & blog reader | ✅ live |
| mealie | Mealie | home | recipes | mini | Recipes & meal planning | ✅ live |
| paperless | Paperless-ngx | home | paperless | mini | Scanned documents, searchable | ✅ live (mini container; NAS storage) |
| wallabag | Wallabag | read | wallabag | mini | Save articles to read later | ✅ live |
| home-assistant | Home Assistant | home | ha | ha | Lights, climate & smart home | ✅ live (HA Green; REST `http://192.168.10.50:8123`) |
| ntfy | ntfy | home | ntfy | mini | Push notifications to your phone | ✅ live |
| tautulli | Tautulli | admin | tautulli | mini | What's being watched on Plex | ✅ live |
| maintainerr | Maintainerr | admin | maintainerr | mini | Tidies the Plex library | ❌ **retired — drop** (stack deleted, no vhost) |
| tdarr | Tdarr | admin | tdarr | — | Optimizes video files | ❌ **not deployed** (Caddy block commented out) |
| pinchflat | Pinchflat | watch | pinchflat | mini | Auto-saves YouTube channels | ✅ live |
| sonarr | Sonarr | admin | sonarr | seedbox | TV automation | ✅ live (Caddy proxies to NAS/edge network) |
| radarr | Radarr | admin | radarr | seedbox | Movie automation | ✅ live |
| lidarr | Lidarr | admin | lidarr | seedbox | Music automation | ✅ live |
| qbittorrent | qBittorrent | admin | qbit | seedbox | Downloads | ⚠️ verify — live download client is **Deluge** (`deluge.{$DOMAIN}`); no `qbit` vhost |
| beszel | Beszel | admin | status | mini | Server health | ✅ live |
| uptime-kuma | Uptime Kuma | admin | uptime | mini | Are the services up? | ✅ live |
| dependency-track | Dependency-Track | admin | deptrack | — | Security/vuln dashboard | ❌ **fully retired — drop** |
| adguard | AdGuard Home | admin | dns | mini | Network-wide ad blocking | ✅ live |
| healthchecks | Healthchecks | admin | health | mini | Backup heartbeat monitor | ✅ live |
| dockge | Dockge | admin | dockge | mini | Container management | ✅ live |
| forgejo | Forgejo | admin | git | mini | The config-as-code Git forge | ✅ live |
| litellm | LiteLLM | admin | llm | **rig** | Local AI gateway | ⚠️ host = **rig, not mini**; AI stack is rig-only |
| frigate | Frigate | admin | frigate | — | Camera AI | ❌ **not deployed** (Caddy block commented out; future plan) |

> Treat this table as a starting draft only. Before generating, diff it against the live `Caddyfile` (subdomain truth) and `homepage/config/services.yaml` (icons/captions). The `host` column is maintainer-reference only — never render it. `admin` services are real but should sit visually *below* the household ones, behind a "Show technical tools" toggle on Home. Extra live services not in this draft (e.g. `stash`, `deluge`, `slskd`, `prowlarr`, `readarr`, `flaresolverr`, `romm`, `amp`, `metube`, `wiki`) should be reconciled from the Homepage config at generation time.

## 5. Design system — Apple.com, 2012

The look to match is apple.com from ~2012 (OS X Mountain Lion / iOS 6 marketing pages): restrained, bright, lots of breathing room, thin gray headlines, glossy accents used *sparingly*. Below are concrete, implementable values, intentionally specific so the build doesn't drift into generic "flat modern."

### 5.1 Typography

- **Stack:** `"Myriad Set Pro","Myriad Pro","Helvetica Neue",Helvetica,Arial,sans-serif`. (Myriad was Apple's 2012 marketing face; Helvetica Neue is the faithful free fallback. Do **not** use San Francisco / `-apple-system` — that's the post-2014 look.)
- **Headlines are thin and gray, not black.** Hero headline ~`48–56px`, `font-weight: 300–400`, color `#333`, tight letter-spacing (`-0.02em`).
- **Body:** `~14–15px`, `#333` on white, line-height ~`1.5`.
- **Captions / fine print:** `~11–12px`, `#888`.
- Headlines centered in hero/section intros; body left-aligned.

### 5.2 Color

| Token | Value | Use |
|---|---|---|
| `--bg` | `#ffffff` | page background |
| `--bg-alt` | `#f2f2f2` → subtle vertical gradient `#fbfbfb`→`#f0f0f0` | alternating bands, footer |
| `--ink` | `#333333` | headlines & body |
| `--ink-soft` | `#666666` | secondary text |
| `--ink-faint` | `#888888` | captions |
| `--rule` | `#d6d6d6` | hairline dividers (often a 1px gradient that fades at the ends) |
| `--link` | `#0070c9` (2012-accurate Apple link blue, `#1a7fd4` hover) | text links |
| `--nav-top` | `#f2f2f2` | global nav gradient top |
| `--nav-bottom` | `#cfcfcf` | global nav gradient bottom |
| `--nav-ink` | `#4d4d4d` | nav link text (with a `1px` white text-shadow below) |

Accent buttons (used only for the rare primary action) use the era's **glossy blue**: a top-to-bottom gradient roughly `#2e8ce6`→`#0a60c0`, `1px` inner top highlight (`inset 0 1px 0 rgba(255,255,255,.4)`), `4px` radius, white text. Use text links with `›` for almost everything; reserve the glossy button for at most one action per page.

### 5.3 The global nav bar (signature element)

A ~`44px` silver bar: vertical gradient `--nav-top`→`--nav-bottom`, a `1px` `#b8b8b8` bottom border with a `1px` white highlight line above it (the classic "aluminum lip"). Links are `--nav-ink`, ~`12px`, evenly spaced, with a subtle white bottom text-shadow so they look engraved. On hover, links brighten to `--ink`. Sticky to top. This bar is the single biggest "this is 2012 Apple" signal — get it right.

### 5.4 Components

- **Tile (Home grid):** white card, `1px #e3e3e3` border *or* borderless with a very soft shadow (`0 1px 3px rgba(0,0,0,.08)`), `~6px` radius. Centered app icon (`~96px` desktop), bold-ish name (`#333`), one gray caption line, and a blue `Learn more ›` at the bottom. Hover (desktop only): lift shadow slightly + reveal an `Open ↗` shortcut. Apple's 2012 product grids used hairline column separators between items — optional but on-brand for a denser layout.
- **Section intro:** centered thin-gray title, a faded `1px` gradient rule under it, generous top margin (`~64px`).
- **Buttons row (detail page):** primary = one glossy blue button; secondary actions = blue text links with `›`.
- **Chips (related / category):** small rounded `#f2f2f2` pills, `#0070c9` text.
- **Icons:** reuse the Homepage icon set (dashboard-icons / selfh.st — the same PNGs referenced in `homepage/config/services.yaml`). Square, rounded-rect mask (`~22%` radius) to read as "app icons."
- **Imagery:** minimal. White space *is* the design. No stock photos.

### 5.5 Layout & spacing

- Max content width `~980px`, centered (the 2012 apple.com grid was ~980).
- Generous vertical rhythm: section gaps `~64–80px`, never cramped.
- Alternate white and `--bg-alt` bands to separate categories on Home.

## 6. Responsive strategy (desktop = higher fidelity)

One codebase, two experiences via CSS. **Desktop (≥1024px) is the showcase; mobile is the clean, fast utility version.**

**Desktop (≥1024px):**
- Full silver global nav with all links + search affordance.
- 4–5 column tile grid, `~96px` icons, hairline separators, hover lift + `Open ↗` reveal.
- Roomy hero (`48–56px` headline), wide `980px` grid, alternating bands.
- Glossy button highlights, subtle shadows, the full "marketing page" feel.

**Tablet (640–1023px):** 3-column grid, nav links may wrap, hover effects kept.

**Mobile (<640px):**
- Nav collapses to wordmark + a simple text menu (or a minimal disclosure — no heavy hamburger drawer).
- **2-column** tile grid, larger tap targets (`≥44px`), `~64px` icons, captions may truncate to one line.
- Hero headline drops to `~30–34px`; remove decorative gradients that don't read on small screens; no hover-only actions (the whole tile taps through to the detail page).
- Detail page: buttons go full-width stacked; sections single-column.
- Performance budget matters more here: inline critical CSS, lazy-load icons.

Use `clamp()` for fluid type and a mobile-first stylesheet with `min-width` breakpoints at `640px` and `1024px`.

## 7. Tech stack & build

**Recommendation: Eleventy (11ty).** Zero-config static site generator that reads `services.yaml`, loops a Nunjucks template per service, and outputs plain static HTML/CSS — exactly what Caddy's `file_server` wants. No client framework, no runtime, nothing to break on rebuild. It directly satisfies the "one data file → many pages" content model.

```
home-hub/
├── .eleventy.js              # config: input src/, output _site/
├── package.json              # devDependency: @11ty/eleventy
├── src/
│   ├── data/
│   │   └── services.yaml      # THE source of truth (§4)
│   ├── _includes/
│   │   ├── base.njk           # html shell: nav + footer + <head>
│   │   ├── tile.njk           # includes the ☆/★ pin control
│   │   └── service-actions.njk
│   ├── _data/                 # 11ty global data (categories, site name, domain)
│   ├── css/styles.css         # the Apple-2012 design system (§5)
│   ├── js/favorites.js        # the only script: localStorage pin/Favorites logic (§3.3)
│   ├── index.njk              # Home — Favorites row + grouped grid (pagination over services)
│   ├── s.njk                  # generates /s/<slug>/ via pagination over services
│   ├── start.njk
│   └── about.njk
└── _site/                    # build output → served by Caddy
```

Detail pages are produced with 11ty **pagination** over `services` (one page per item, `permalink: /s/{{ service.id }}/`). Footer sitemap and host chips iterate the same data. **Result: adding a service = adding one YAML block, then `npm run build`.**

**No-build fallback (if a toolchain is unwanted):** a single `index.html` plus `services.json` rendered client-side with a small vanilla-JS template, and detail pages handled by a hash route (`/#/s/plex`). Trade-off: loses real static URLs / bookmarkable per-service pages and basic SEO — so prefer Eleventy unless the owner objects to running a build.

**Build/deploy:** `npm run build` → `_site/`. Commit the source into the repo (see §9); CI or a one-line script copies `_site/` to the Caddy static-sites volume. Keep it boring and rebuildable, matching the repo's whole philosophy.

## 8. Caddy integration

The site is static files served by Caddy alongside the existing reverse-proxy blocks. **Pick the front-door hostname** — recommended: the **apex `tabaska.us`** (it's the natural "home base"; `home.tabaska.us` is already taken by the Homepage dashboard, and `start.`/`hub.` are good alternatives). Decide with the owner; the Homepage app can stay where it is — this site links *out* to it like any other service, or replaces it as the default front door.

Add one block to `foss-setup/configs/docker-stack/stacks/caddy/caddy/Caddyfile`:

```caddy
# Household front door — static "it just works" hub (this plan)
tabaska.us {                      # or hub.tabaska.us
	import local_tls              # NOTE: live snippet is `local_tls` (real LE certs via
	                              #   Cloudflare DNS-01); the original draft said `cloudflare_tls`
	root * /srv/home-hub          # mounted _site/ build output
	file_server
	encode zstd gzip
	# optional: long cache for hashed assets, no-cache for HTML
	@html path *.html /
	header @html Cache-Control "no-cache"
}
```

!!! note "Correction: TLS snippet name"
    The source draft imported `cloudflare_tls`. The **live Caddyfile** uses a snippet named **`local_tls`** (which itself does Cloudflare DNS-01 with real Let's Encrypt certs). Use `import local_tls` to match reality.

Mount the built `_site/` into the Caddy container at `/srv/home-hub` (add a volume in the caddy `compose.yaml`). Because it's the same Caddy that already fronts every `*.tabaska.us` service, the **Open <app> ›** links resolve with zero extra config. TLS reuses the existing Cloudflare DNS-01 wildcard snippet — no new certs to manage.

## 9. Where this lives in the repo

Add the site as its own stack/source folder so it's versioned and rebuildable like everything else:

```
foss-setup/configs/docker-stack/stacks/home-hub/   # source + compose for the build/serve
```

Keep `services.yaml` here as the single source of truth. Document in the folder README that it is *seeded from* `homepage/config/services.yaml` + the `Caddyfile` but is hand-maintained for the friendly prose. Add a one-paragraph pointer from the top-level `README.md` ("Phase 4 — Glue & polish") since this site *is* the human glue layer.

## 10. Accessibility & performance

- Semantic HTML: real `<nav> <main> <section> <article> <footer>`, one `<h1>` per page, headings in order. Tiles are `<a>` wrapping the card (whole-tile click).
- Color contrast: `#333` on white passes AA; verify the `#888` captions hit AA at their size, darken to `#717171` if not. The glossy-blue button needs white text ≥ AA — verify.
- Keyboard: visible focus rings on every link/tile; logical tab order; skip-to-content link.
- Alt text on every app icon (`"<Name> icon"`); decorative gradients are CSS, not images.
- Performance: static HTML, inline critical CSS, lazy-load below-the-fold icons, no JS framework. Target a sub-second first paint on LAN. Whole site should be a few hundred KB.
- Works with JS disabled (Eleventy path): every link and page is real HTML.

## 11. Build milestones (suggested order)

1. **Scaffold:** init Eleventy, `base.njk` shell with the Apple-2012 global nav + footer, `styles.css` implementing the design tokens (§5). Ship a static Home with 3 hard-coded tiles to lock the look first.
2. **Data layer:** author `services.yaml` (seed from repo §4.3, **applying the 2026-07-14 corrections above**); wire Home to generate the full grouped grid from data.
3. **Pinning:** `favorites.js` + the ☆/★ control + the Favorites row (§3.3). Verify it persists across reloads and degrades with JS off.
4. **Detail pages:** `s.njk` pagination → `/s/<slug>/` with the full template (§3.2). Write the plain-language prose for the ~10 household-facing services first; `admin` ones can ship with lighter copy.
5. **Supporting pages:** `/start/`, `/about/`, footer sitemap.
6. **Responsive pass:** desktop high-fidelity → tablet → mobile (§6); test at 375 / 768 / 1440px.
7. **Caddy deploy:** add the site block + volume (§8, `import local_tls`), build, serve, verify every **Open ›** link resolves and TLS is green.
8. **Polish & verify:** accessibility checks (§10), proofread copy for jargon, confirm catalog matches the live Caddyfile, confirm no host/IP leaks anywhere in the rendered output.

## 12. Definition of done

- [ ] Lands on the front-door hostname over HTTPS with no warnings.
- [ ] Every service in the live `Caddyfile` appears as a tile, grouped by task, with a working **Open ›** link.
- [ ] Each service has a detail page a non-technical person can follow: what it is, when to use it, a 3–5 step how-to, and the right action buttons.
- [ ] Any service can be pinned (☆) from a tile or its detail page; pinned ones appear in a Favorites row at the top and persist across reloads on that browser. Clearing favorites works; JS-off still leaves a usable catalogue.
- [ ] No machine name, host, or IP appears anywhere in the rendered site.
- [ ] Desktop is visibly higher-fidelity than mobile (grid density, icon size, hover reveals, hero scale) while both are usable.
- [ ] Reads unmistakably as Apple.com 2012: silver gradient nav, thin gray headlines, glossy-blue `›` links, hairline rules, lots of white space.
- [ ] Adding a new service = one YAML block + rebuild. No HTML edits required.
- [ ] Source committed under `foss-setup/`; site rebuilds from scratch with `npm run build`.

## 13. Decisions left for the owner

1. **Front-door hostname:** apex `tabaska.us` vs `hub.`/`start.tabaska.us`, and whether this replaces or sits beside the existing Homepage dashboard (currently live on `home.tabaska.us`).
2. **`admin` services:** show them (behind a "technical tools" toggle) or hide them entirely from the household view?
3. **Search box** on desktop: ship in v1 or defer.
4. **Wordmark / household name** to put in the nav and hero.

---
[← Architecture & design](index.md)
