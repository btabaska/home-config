# FOSS Setup — End-to-End Validation Report

> **Re-validation status (after fixes applied):** All Critical/High/Medium findings below have been implemented across the markdown, HTML, configs, and scripts. Image tags re-verified to exist (Dependency-Track `apiserver:5.0.2`/`frontend:5.0.1`, Navidrome `0.62.0`, Pinchflat `v2025.9.26`, Maintainerr `maintainerr/maintainerr:v3.15.3`, Miniflux `2.3.1`; Frigate kept at `0.17.1` because `0.17.2` does not exist). Cross-file consistency re-checked: Syft `1.45.1` / Grype `0.114.0` agree across all three files; the markdown number changes (RAM `~$40-110`, seedbox `6-10 TB`/HDD, always-on `~82-113 W`/`~$150-200`, LiteLLM fallback `llama3.2:1b`) were mirrored into the HTML so the two guides stay in sync. Both HTML JSON data blocks still parse; all shell scripts pass `bash -n`; changed YAML parses. See the "Re-validation outcome" section at the bottom.



Pre-implementation deep validation of `foss-setup-plan-2.md`, `foss-setup/docs/index.html`, and the `foss-setup/` config/script tree. Performed by a 7-agent validation swarm, each section cross-checked against its referenced config files and external facts (versions, prices, commands) as of June 2026.

**Overall verdict:** The guide is unusually well-researched and internally consistent. Almost all hardware, pricing, and architectural facts hold up. The problems are concentrated in **pinned image tags that don't exist or are stale**, a few **configs that won't start as shipped**, two **Ansible "set-and-forget pull" gaps**, and **doc-vs-config naming mismatches**. None are design-level flaws; all are fixable before/early in rollout.

Counts: **1 Critical, 9 High, ~20 Medium, ~20 Low/Nice-to-have.**

---

## CRITICAL — deploy blocker

### C1. Dependency-Track image tags `5.6.0` are invalid (won't deploy)
- **Where:** `configs/docker-stack/stacks/dependency-track/compose.yaml:17,50`; mirrored in `configs/inventory/inventory.md:38-39`.
- **Problem:** `dependencytrack/apiserver:5.6.0` and `dependencytrack/frontend:5.6.0` are pinned. DT v5 GA **restarts numbering at `5.0.0`**; tags `5.0.0–5.6.0` only ever existed in the archived pre-GA `hyades-*` repos (which the project says explicitly *not* to consume), and the frontend never published `5.6.0` at all. `docker compose up` fails to pull (frontend especially) — and ironically violates the guide's own "pin a *verified* version" thesis.
- **Fix:** Pin to current verified GA tags from the official `dependencytrack/apiserver` + `dependencytrack/frontend` repos (e.g. `5.0.x`); update the inventory sample to match.

---

## HIGH

### H1. Pinchflat image tag `v2026.3.1` does not exist
- `configs/docker-stack/stacks/pinchflat/compose.yaml:14`. Latest release is `v2025.9.26` (no 2026 release; dev appears stalled). `docker compose pull` fails. → Pin `:latest` or a verified digest; consider noting the project is dormant and keep yt-dlp/MeTube as fallback.

### H2. `immich-go ... --watch` is not a real flag
- `scripts/media/immich-go-import.sh:66-70`. `--watch` belongs to the official Immich CLI (`immich upload --watch`), not immich-go. The continuous-ingest example won't run (one-shot path is fine). → Use `immich upload --watch <dir>` or a cron/timer re-running the script.

### H3. LiteLLM fallback to the Mac mini will not resolve on Linux Docker
- `configs/docker-stack/stacks/litellm/compose.yaml` + `config.yaml:27`. `host.docker.internal` is undefined on native Linux Docker; no `extra_hosts` entry exists. The always-on small-model fallback silently breaks. → Add `extra_hosts: ["host.docker.internal:host-gateway"]` and set `OLLAMA_HOST=0.0.0.0` on the host (+ firewall allow). Correct the misleading config comment.

### H4. Internal capacity contradiction: §0 vs §3/§4 (8 GB Mac mini oversubscribed)
- §0 capacity note (lines 29,35) says the 8 GB Mac mini gets **one small** game server and a **≤1B** LLM at most. But §4 line 270 lists Valheim/Terraria/Factorio/etc. as "always-on" on the Mac mini, and `litellm/config.yaml:26` sets the fallback to `llama3.2:3b` (~3–4 GB), and §3 line 252 says "1-3B." → Make §4 host at most one light server always-on; change the LiteLLM fallback to a ≤1B model (or move it to the NAS post-RAM-upgrade).

### H5. `borgmatic.service` never supplies the passphrase (unattended Borg fails)
- `scripts/backup/borgmatic.service` vs `borgmatic-config.yaml:48` (`encryption_passphrase: ${BORG_PASSPHRASE}`). The oneshot unit has no `EnvironmentFile`, so timer runs get an empty passphrase and error out (the restic unit does this correctly). → Add `EnvironmentFile=/etc/borgmatic/passphrase.env` (chmod 600), or use borgmatic's `encryption_passcommand`/passphrase-file.

### H6. Caddy's default image can't parse its own Caddyfile (reverse proxy won't start)
- `caddy/compose.yaml:18-19` ships the stock `caddy:2.11.4-alpine` (custom `build:` commented out), but every vhost in `caddy/Caddyfile` uses `import cloudflare_tls` → `dns cloudflare`, a third-party module not in the official image. Caddy fails at startup and takes the whole stack's proxy down. → Ship the custom build active by default, or make `cloudflare_tls` opt-in and default to `tls internal`.

### H7. `ansible-pull` discards the inventory → group logic no-ops
- `configs/ansible/ansible-pull.service:24-30` runs `--inventory 'localhost,' --connection local`, so `group_names` is empty: the `docker` role never runs, `on_demand.yml` (rig wake-gating) never loads, and `base` reads `hosts/localhost/pkglist.txt`. The entire "set-and-forget pull" story silently no-ops. → Use the repo inventory with `--limit "$(hostname -s)"`, or convert group gates to host-fact conditionals.

### H8. "Pull applies only OS security patches in `--check`" is not implemented
- doc line 648 + `ansible-pull.service` + `roles/base/tasks/main.yml:18-34`. `--check` suppresses *all* changes; no task uses `check_mode: false`, and `base` only *enables* unattended-upgrades (never runs an upgrade). → Add `check_mode: false` to the patch tasks you actually want applied, and reword the claim.

### H9. HTML `esc()` doesn't escape double-quotes → "copy command" buttons silently break
- `docs/index.html:884`, used at `:923` (`data-cmd="${esc(c)}"`). Any command containing `"` truncates the attribute, so the clipboard payload is garbled (visible text is fine — silent failure). Affects many commands (`net-10`, `docker-02`, `seed-04`, `sec-02`, …) and one aria-label (`seed-01`). → Add `.replace(/"/g,"&quot;")` (and `'`→`&#39;`) to `esc()`, or use `textContent`+`dataset`.

---

## MEDIUM

**Networking (Sec 0–1)**
- **M-net1.** Section 1 table calls the IoT/Cameras zone "Untrusted" (lines 61-62), but line 55 and `vlan-zone-firewall-plan.md` define separate `IoT` and `Cameras` zones. Following the table literally breaks the camera↔IoT isolation rules. → Use the real zone names.
- **M-net2.** Work zone listed as "own / Trusted" (line 63) contradicts the "internet-only, isolated" intent (line 76 + config). → Make Work its own isolated zone.
- **M-net3.** Listing Matter in the mDNS proxy (`mdns-multicast-checklist.md:34`) conflicts with official Matter guidance (mDNS forwarders corrupt Matter packets). → Strengthen the hedge / remove the Matter service strings; keep Matter devices on HA's VLAN.

**Media core (Sec 2 pt1)**
- **M-mc1.** Immich `valkey:9` digest doesn't match the v2.7.5 release compose (comment claims it does; Postgres digest *does* match). → Re-copy the valkey digest or soften the comment.
- **M-mc2.** Navidrome `0.61.2` is behind `0.62.0`, which carries 6 security fixes (auth bypass, IDOR) relevant to multi-user/LAN-exposed installs. → Bump to `0.62.0`.

**Media acquisition / seedbox (Sec 2 pt2)**
- **M-ma1.** *Big one:* running slskd/Soularr/Unpackerr/Recyclarr via `docker compose` assumes root, but the chosen Bytesized plan is a **no-root managed seedbox** (your own `provider-comparison.md:46` + userspace-Tailscale scripts confirm this). The one-click catalog (line 173) doesn't list those tools. → Confirm the catalog one-clicks them, or move to a root-capable tier; reconcile "install from catalog" vs "`docker compose up -d`."
- **M-ma2.** Upload-cap number conflicts with Bytesized's own table (Stream +3 = 6 TB on `/plans` vs 10 TB on `/appbox`). → Verify at checkout; say "6–10 TB."
- **M-ma3.** "3000 GB NVMe-class storage" (line 173) — the New Appbox tier is **HDD**. → Drop "NVMe-class."
- **M-ma4.** `lidarr-slskd-soularr.md:60-65` tells you to override `REMOTE_MOVIES/LOCAL_MOVIES` to add music — but `seedbox-sync.sh` already syncs music natively (`SYNC_MUSIC=1` default). Following the doc breaks movie sync. → Replace with "music is automatic; `SYNC_MUSIC=0` to disable."
- **M-ma5.** Music dest path mismatch: `seedbox-sync.sh:57` `/volume1/music` vs doc `/volume1/media/music`. → Pick one (match Navidrome's library path).
- **M-ma6.** `configs/seedbox/.env.example` is missing, but `lidarr-slskd-soularr.md:78` says `cp .env.example .env`. → Add the template (covers slskd/Soularr/Unpackerr vars).
- **M-ma7.** Maintainerr pinned to the deprecated `jorenn92` image repo (comment even notes the move). → Switch to `ghcr.io/maintainerr/maintainerr`.
- **M-ma8.** Unpackerr container path prefixes won't match the native *arrs' reported paths → never extracts (moot if Docker isn't available, see M-ma1). → Align mount/paths or run as a native binary.

**Smart home / gaming (Sec 3–4)**
- **M-sh1.** LiteLLM `simple-shuffle` with no `order:` means ~50% of requests hit the sleeping rig first and eat a 15 s timeout before failover. → Add `order: 1` (rig) / `order: 2` (Mac mini); drop the redundant self-referential `fallbacks`.
- **M-sh2.** `install-haos-vm.sh:36` uses `OVMF_CODE_4m.fd` (lowercase m) — canonical is `OVMF_CODE_4M.fd`; preflight only warns then fails in `virt-install`. → Fix casing + add a VARS NVRAM template, or use `--boot uefi`.

**Power / backup / config (Sec 5–7)**
- **M-bk1.** Borg repo inits `--append-only` *and* sets GFS retention → client-side prune never frees space, and append-only here is only a local flag a compromised client can flip (real immutability needs server-side `borg serve --append-only`). Contradicts line 370. → Either drop append-only and rely on B2 Object Lock, or keep it and remove client prune + document the admin-prune path.
- **M-bk2.** B2 price drift: plan says $6.95/TB (correct), but `backup-architecture.md:8,11` and `restic-backup.env.example:6` still say ~$6/TB. → Update the two helper files.
- **M-cf1.** "Container split" naming: §9 line 683 says "Komodo/Dockge run containers," but §7/Phase 4/stack README all recommend **Dockhand (or Dockge)**, with Komodo as the non-recommended heavy option. → Make line 683 "Dockhand/Dockge."

**Inventory / SBOM / Ansible (Sec 8–9)**
- **M-an1.** `roles/base` reads `hosts/<host>/pkglist.txt`, but `export-manifests.sh` writes `pkglist.pacman-explicit.txt`/`pkglist.aur.txt`/`pkglist.apt-manual.txt`. The "manifest becomes the enforcer" claim is broken (masked by `ignore_errors`). → Align filenames.
- **M-an2.** `roles/sbom` copies units from `scripts/inventory/...` via a relative `src` that won't resolve from the role → SBOM timer never installs. → Use `{{ playbook_dir }}/../../...` or role `files/`.
- **M-an3.** `roles/docker` uses `community.docker.docker_network` (needs the Docker Python SDK, never installed) and installs distro `docker.io` (clashes with the runbook's official docker-ce path). → Install `python3-docker` (or `command: docker network create`) and standardize the engine source.
- **M-an4.** Backup role backs up `/home` only; restore runbook restores `/opt/stacks` + `/var/lib/docker/volumes`. They aren't wired together. → Default `extra_backup_paths` to include those.
- **M-an5.** Seedbox is in `fleet`/`always_on` groups, so root-level roles (base/tailscale/backup/state) target a no-root box despite the "user-space only" rule. Only `docker_hosts` is excluded. → Remove seedbox from `fleet` or give it a user-space-only play.
- **M-an6.** DT apiserver RAM understated: doc says "1-2GB," `mem_limit: 2g` — official minimum is 2–4.5 GB, recommended 8–16 GB; 2g risks OOM/refusal. → Quote 4GB+, raise `mem_limit`.
- **M-an7.** §9's inline `inventory/hosts.yml` example diverges from the real `inventory.ini`: YAML-vs-INI, MagicDNS FQDNs vs ssh aliases, and it omits the `fleet`/`docker_hosts` groups that `site.yml` and the docker role actually depend on. Also references non-existent `monitoring` role and `deploy-stacks.yml`/`sbom.yml` playbooks, and `group_vars/debian.yml`/`arch.yml`/`host_vars/*` that don't exist. → Sync the example to the real inventory; drop or implement the missing pieces.

**HTML / cross-doc**
- **M-html1.** Network port map contradicts task instructions: Forgejo shown as `3000/22` but tasks use `:3030`; Miniflux shown as `8080` but task says `:8082`. → Make the map match the task ports.
- **M-html2.** README repo-layout omits `configs/inventory/` and `scripts/inventory/` even though the whole SBOM/inventory layer (central to Phase 4) lives there. → Add both directories.

---

## LOW / NICE-TO-HAVE (verify or polish; not blocking)

- **Net:** RAM ~$130 is top-of-market (~$40–110 typical); IoT→RFC1918 block mixes legacy paradigm into the ZBF design; IoT→gateway port list (53/67-68 vs 53/67/123); "never dual-home HA" is stricter than documented Matter practice; HA omitted from Trusted row in the Sec 1 table; J4125 official 8GB cap caveat; SSH example user `you@macmini` vs alias `mini`/`User admin`.
- **Media core:** Miniflux `2.3.0`→`2.3.1`; "Proton" likely over-listed in the Euro-Office fork attribution; Pinchflat missing from the Sec 0 host table; immich-go RAW default could be `StackCoverRaw`; "Kindle Store ended for pre-2013 devices May 20 2026" unconfirmed.
- **Media acq:** Paperless "broker" naming inverted (Redis is the broker, not Postgres — works, comment is wrong); app count "71+" vs current "67+"; Soularr `v1.2.2` ghcr tag — verify or use documented Docker Hub image; rclone key-path home inconsistency; Seerr config-dir ownership (UID 1000) note; Stream +3 is "limited availability" — have a fallback; Unpackerr "near-mandatory" oversells for torrent-only.
- **Smart home/gaming:** `gpu-power-tune.service` won't re-apply on resume (claim says it does); `nut-client-ubuntu.sh` uses NUT 2.8 `secondary` (fails on 22.04's `slave`); Frigate inline comments imply the 2014 Mac mini iGPU is OpenVINO-capable (it isn't — use Coral); LiteLLM `timeout: 15` may false-trip on a 14B cold load; Frigate `0.17.1`→`0.17.2`; gpu-power-tune heredoc shows a placeholder ExecStart path.
- **Backup/config:** always-on subtotal high-end 118→113 W; Hetzner "~$4/TB" overstated (~$2–3.2/TB); `restic restore latest` not host-scoped despite comment; `borgmatic init` deprecated → `repo-create`; Dockhand-vs-AdGuard port 3000 clash if you swap managers; Pi-hole alternative needs a one-line Caddyfile edit; Homepage `HOMEPAGE_ALLOWED_HOSTS` must be edited for LAN/proxy; Healthchecks container healthcheck path unverified.
- **SBOM/Ansible:** Syft/Grype pins stale (1.18.1/0.86.1 vs 1.45.1/0.113.0) and `ENFORCE_TOOL_PINS=1` will block a fresh run; two pin sources can drift; `stdout_callback = yaml` now lives in `community.general`; `serial` expression fragile under push; control-repo URL naming inconsistent across files; `inventory.md` sample misplaces DT/Forgejo; apiserver `wget` healthcheck unverified; `host_key_checking = True` needs known_hosts pre-seed for first push.
- **HTML/cross-doc:** decimal-hour estimate mis-parse ("1-1.5 hr"→5 hr); one-time-hardware card "$250–800" hard to reconcile with itemized ~$425+ floor; tab ARIA roles + heading hierarchy; HA Green "1.7-3W" vs "2-3W" self-variance; "Mac mini" vs "Ubuntu" label mixing; Komodo absent from HTML; `md:122` Rockbox'd-iPod leftover contradicts the chosen Apple-firmware path; wallabag dir breaks the `stacks/<svc>/` convention; ZBT-2 link slug.

---

## Strongly verified correct (high-confidence highlights)

- **Plex pricing:** $119.99→$249.99 (Mar 2025)→**$749.99 at 12:01 AM UTC July 1, 2026**; remote video paywalled 2025; lifetime grandfathered. Both guides match and are correct.
- **DS920+ → 20GB** with Crucial **CT16G4SFD8266** (every spec verified); J4125 Quick Sync; Mac mini Macmini7,1 i5-4278U 8GB soldered, ~6–15 W. All accurate.
- **UniFi ZBF** (six built-in zones, stateful/directional rules, custom outrank built-in, one-way migration), **IGMP snooping OFF**, gaming stays on Trusted for mDNS — all correct and current.
- **Immich** 2.7.5 stable / 3.0-rc, VectorChord image, RAW support, immich-go/pbak; **Calibre-Web-Automated** (KOSync); iPod libgpod/Rhythmbox + Rockbox via freemyipod — accurate.
- **Seerr** (Overseerr/Jellyseerr successor), *arr roles, slskd+Soularr relationship, Kometa/Maintainerr/Tautulli, Paperless 5-service architecture, Readarr retired — accurate. `seedbox-sync.sh` is non-destructive (copy-only, flock, set -euo).
- **HA Green/HAOS 18.0**, Nest SDM ($5 + Pub/Sub + OAuth, Production-consent gotcha), Midea `midea_ac_lan` + ESPHome SLWF-01, Frigate 0.17 config, Zigbee ZBT-2/Sonoff-E, WoL + gpu-power-tune scripts, Sunshine/Moonlight networking — accurate.
- **Electricity math** checks out at $0.20/kWh; **3-2-1-1-0** framing; restic units + non-destructive `restore-test.sh`; **Watchtower archived Dec 2025** + fork; Dockhand/Diun 4.33.0/Beszel/Caddy 2.11.4 current; AdGuard→Unbound over the compose network; valid Unbound + Tailscale HuJSON ACL.
- **SBOM story:** Syft+Grype roles, SOPS+age (no ansible-vault, no committed secrets), CVE-2026-33634/trivy-action supply-chain summary, DT upload mechanics, push playbooks (`patch`/`reboot`/`audit`) idempotent and correct.
- **Cross-doc:** every config/script path referenced by the HTML resolves to a real file; service-to-host placement is consistent across both guides; sensor shopping list prices match exactly; HTML JSON data blocks are valid and self-consistent.

---

## Recommended fix order before implementation

1. **Pinned image tags first** (these block deploys): Dependency-Track (C1), Pinchflat (H1) — plus the stale/insecure bumps Navidrome 0.62.0, Maintainerr repo, DT RAM.
2. **Configs that won't start as shipped:** Caddy `cloudflare_tls` (H6), borgmatic passphrase (H5), LiteLLM `host.docker.internal` (H3).
3. **Set-and-forget Ansible gaps:** ansible-pull inventory (H7) + patch-in-check (H8), plus the role path/SDK/filename fixes (M-an1..7).
4. **Seedbox reality check:** root vs managed-catalog (M-ma1) — decide before buying the plan.
5. **Internal consistency cleanups:** Mac mini capacity (H4), zone names (M-net1/2), container-manager naming (M-cf1), doc-vs-inventory (M-an7), HTML port map + copy-button bug (H9, M-html1).
6. **Polish pass:** the Low/Nice-to-have list.

---

## Re-validation outcome (post-fix)

Implemented by a 5-agent swarm partitioned by file ownership (no edit conflicts), then I reconciled the cross-document number drift the markdown-only edits would otherwise have left in the HTML.

### Confirmed fixed
- **Deploy blockers:** Dependency-Track GA tags (`5.0.2`/`5.0.1`) in compose + inventory sample; Pinchflat pinned to an existing tag; Caddy now defaults to the custom build (cloudflare DNS module), so the proxy starts; `borgmatic.service` supplies `BORG_PASSPHRASE` via `EnvironmentFile`; LiteLLM has `extra_hosts: host.docker.internal:host-gateway`.
- **Ansible set-and-forget:** `ansible-pull` runs against the repo `inventory.ini` with `--limit "$(hostname -s)"` (group logic resolves); the "applies patches in --check" claim reworded + `check_mode:false` scoped to unattended-upgrades enablement; base-role pkglist filenames, sbom-role unit src path, docker-role `python3-docker` + single docker-ce source, and backup `extra_backup_paths` all fixed; seedbox moved out of root-level `fleet`.
- **Consistency:** container-manager naming (Dockhand/Dockge), DT RAM (4g + ≥4GB guidance), §9 inventory example matches reality, zone names (IoT/Cameras/Work), Matter mDNS caveat, B2 `$6.95/TB` everywhere, append-only dropped in favour of B2 Object Lock, seedbox root/managed reality reconciled, new `configs/seedbox/.env.example`, music path standardized to `/volume1/music`.
- **HTML:** `esc()` escapes quotes (copy buttons work), Forgejo `3030`/Miniflux `8082` port map, NUT NAS IP `192.168.10.10`, decimal-hour estimator, tab ARIA roles, ZBT-2 link, README `inventory/` dirs.

### Reconciled during re-validation (markdown→HTML drift that the fixes introduced)
- HTML RAM price `~$130` → `~$40-110` (8 spots); seedbox cap `10 TB/mo` → `6-10 TB/mo` + storage marked HDD (incl. the seed-01 task prose); always-on subtotal `~82-118 W / ~$150-205` → `~82-113 W / ~$150-200` (table + cost card).
- **LiteLLM fallback model** `llama3.2:3b` → `llama3.2:1b` — the earlier fix added `order:`/timeout but left a 3B model on the 8 GB Mac mini, contradicting the new "≤1B" capacity decision. Now consistent.

### Residual notes (acceptable / by-design, not blockers)
- **ansible-pull (H7):** the fix requires each host's `hostname -s` to equal its inventory alias (`macmini`/`cachyos`/`seedbox`); this is documented in a comment in the unit. If you prefer not to rename hosts, switch the `--limit` to an explicit per-host value or add `ansible_host` fact mapping.
- **Frigate** stays at `0.17.1` (0.17.2 was never released).
- **Komodo** still appears in the markdown as a *documented alternative* container manager (Section 7 / split / stack table) — intentional; only the Section 9 "bottom line" that wrongly elevated it was corrected. It remains absent from the HTML by design.
- The remaining **Low/Nice-to-have** polish items not individually called out above were addressed by the owning agents (see their change logs) or are cosmetic.
