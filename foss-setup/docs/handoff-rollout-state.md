# Rollout handoff state

### Run 0 results (2026-07-07 evening)

- **ansible-pull converges GREEN on mini** (first success ever): ok=34 failed=0, apply mode. Fixes: SOPS gates on backup+sbom roles, un-ignored break-glass pubkey, removed conflicting docker apt source on mini, chezmoi via installer on Debian.
- Repo topology fixed: forgejo `home/homelab` = foss-setup/ subtree, published via `scripts/docs/publish-deploy.sh` (fast-forwards).
- mini: /opt/stacks drift committed+pushed; etckeeper repaired; 3 dead CIFS mounts disabled (systemctl --failed = 0); maintainerr healthy; duplicate mini Immich stopped (Caddy->NAS verified).
- Secrets: leaked ntfy diun token REVOKED + rotated (vault: ntfy.diun_token); wallabag admin rotated (vault: wallabag.*). NAS AdGuard password rotation still blocked on container being up.
- migration-snapshot archived to nas:/volume1/backups/migration-snapshot-2026-07-07 (92,128/92,128 files verified).
- gpu-power-tune awk/read bug fixed in repo (deployed copy on rig pending sudo).
- Rig BLOCKED on two gates: btabaska sudo needs password (vault sudo slots empty; NOPASSWD or password needed) and rig forgejo deploy key unregistered (rig pubkey staged; register in Forgejo web or provide forgejo admin creds). Units staged at rig:~/staging/.
- HA discovered live at 192.168.10.50:8123 (creds in vault); not on tailnet yet.

### Runs 1-2 autonomous results (2026-07-07 night)

- **Verification framework LIVE** (verify-01..05): 41 checks across 7 domains; daily timer 07:15 on mini; ntfy topic `verification` (dedicated token); LLM triage on rig via ollama qwen3-coder:30b — first cycle: 35 pass, 6 fail (all expected: dns-02 x2, nas-08 dump, 3 git-drift), 6/6 valid triage verdicts; reopen-suggestions.json feeds session starts.
- **home.tabaska.us rebuilt** (home-01..04): 40-service catalog (service-catalog.yaml), 39 verified Caddy vhosts incl. ha + wiki + NAS/rig services; categorized Homepage with live widgets (vault keys, values only on mini).
- **wiki.tabaska.us LIVE** (wiki-01..04): 51 pages — hosts, 7 runbooks, operations, network + 32 generated service pages (gen-wiki-services.py); build via build-wiki.sh (pinned mkdocs-material 9.5).
- Notes: mini->rig SSH denied by tailnet ACL (rig checks are HTTP); mini->nas SSH key added; Sunshine down on rig (502 expected); all *.tabaska.us certs are Caddy-internal CA by design (Cloudflare token would enable real certs).

## Session 4 — 2026-07-07 (Plan v3)

- **Full repo + fleet audit** performed (every host inspected against the guide and configs).
- **Guide refactored into 8 staged runs** (Plan v3 in `docs/index.html`) — **194 tasks** total.
- **Regressions found and reopened:** `dns-02`, `game-10`, `nas-08` — previously marked done but no longer true on the fleet.
- **Run 0 execution started** (docs/repo reorganization, hygiene, tracker groundwork).
- Docs reorganized: validation report archived, wiki/home-hub designs moved under `docs/`, NAS schema and game-server guide moved next to their configs, root `README.md` added.

# Rollout handoff state — 2026-07-05 (session 3)

Import this into the tracker (`docs/index.html`) so checkmarks match reality for the next agent.

## Quick import (browser)

1. Open `foss-setup/docs/index.html` in your browser (file:// or served).
2. Click **Import progress** and choose `docs/progress-backup-2026-07-05.json`.

**Or** paste in DevTools console:

```javascript
fetch('../docs/progress-backup-2026-07-05.json')
  .then(r => r.json())
  .then(obj => {
    const done = obj.done || obj;
    const key = 'foss-analogue-progress-v1';
    const merged = { ...(JSON.parse(localStorage.getItem(key) || '{}')), ...done };
    localStorage.setItem(key, JSON.stringify(merged));
    location.reload();
  });
```

## Progress snapshot

| Metric | Value |
|--------|-------|
| Completed | **79 / 162** (49%) |
| Previous backup | `progress-backup-2026-07-03.json` (67 done) |
| This session | +12 tasks |

## Completed this session (2026-07-05)

| Wave | Tasks |
|------|-------|
| **DNS resilience** | dns-02 NAS secondary AdGuard (API configured, `*.tabaska.us → 192.168.10.2`) |
| **Life apps** | read-07 Wallabag, doc-01 Paperless-ngx (mini), read-14 Pinchflat |
| **Reading** | nas-09 CWA verified running, ebook-04 Libreseerr |
| **Ops** | docker-12 Diun (ntfy topic `diun`) |
| **Plex polish** | media-01 Tautulli, media-02 Kometa, media-03 Maintainerr |
| **Gaming** | game-08 WoL on rig, game-05 Sunshine installed + active |

## Ansible / glue-08 fixes pushed to Forgejo (`home/homelab`)

- `configs/ansible/files/id_ed25519.pub` (break-glass key)
- `admin_user: btabaska` in group_vars
- base role: missing pkglist manifest + check_mode fixes
- tailscale role: skip `tailscale up` when already connected

**Still partial:** ansible-pull timer runs but playbook may still fail on later roles; rig ansible-pull not deployed.

## Partial / deferred (do NOT mark done without verifying)

| Task | State |
|------|-------|
| **dns-02** | Deployed — **change NAS AdGuard admin password** (temp: set via API install; login at http://192.168.10.4:3000) |
| **dns-03** | UniFi DHCP fail-open chain — **you** (UniFi GUI) |
| **dns-04** | Outage drill — run `scripts/network/dns-resilience-verify.sh` after dns-03 |
| **dns-05** | NAT :53 + DoH blocking — **you** (UniFi GUI); only after dns-04 |
| **glue-01** | No UPS — nut-client on mini ready |
| **glue-08** | mini timer active; playbook still exits non-zero on some roles |
| **sbom-02** | mini + NAS scheduled; rig not done |
| **nas-08** | Immich healthy; pg_dump backup exists (2026-07-02); **schedule cron in DSM**; admin/Quick Sync pending |
| **read-07** | Change default Wallabag password; create API client for KOReader |
| **doc-01** | Paperless on **mini** (not NAS); complete first-visit admin wizard |
| **media-02** | Kometa needs `config/config.yml` Plex + TMDb keys |
| **read-14** | Pinchflat downloads to local `./downloads` — point at NAS YouTube library |
| **ebook-04** | Libreseerr needs Readarr API wiring in UI |
| **game-05** | Sunshine web UI pairing at https://192.168.10.12:47990 |
| **game-10** | gpu-power-tune script fixed in repo; verify service on rig |
| **B2 / sec-03 / handoff-05** | User skip until B2 ready |

## Key URLs

| Service | URL |
|---------|-----|
| Miniflux | https://rss.tabaska.us |
| Navidrome | https://music.tabaska.us |
| Mealie | https://recipes.tabaska.us |
| Wallabag | https://wallabag.tabaska.us |
| Paperless | https://paperless.tabaska.us |
| Pinchflat | https://pinchflat.tabaska.us |
| Homepage | https://home.tabaska.us |
| AdGuard (mini) | https://dns.tabaska.us |
| AdGuard (NAS) | http://192.168.10.4:3000 |
| Uptime Kuma | https://uptime.tabaska.us |
| DepTrack | https://deptrack.tabaska.us |
| Immich | https://immich.tabaska.us (LAN :2283) |
| CWA | http://192.168.10.4:8083 |
| Forgejo | http://macmini.tailb31641.ts.net:3030 |
| Libreseerr | http://192.168.10.2:8789 |

DNS: **Still gateway-only DHCP** until dns-03. Target chain: `#1` mini `192.168.10.2`, `#2` NAS `192.168.10.4`, `#3` gateway `192.168.10.1`.

## Suggested next_up

1. **dns-03** UniFi fail-open DHCP chain (~15 min in UniFi UI)
2. **dns-04** Run outage drill script
3. **read-03 / ebook-02** CWA ingest + Readarr hook
4. **ha-01** Home Assistant onboarding
5. **nas-08b** SD card import (after Immich admin)

## Secrets / hygiene

- NAS AdGuard temp admin password set during API install — **rotate immediately**
- ntfy Diun token: (rotated — see vault: `ntfy.diun_token` in `.handoff-secrets.yaml`; never store literal tokens in this doc)
- Wallabag/Paperless secrets generated on mini `.env` files — not in vault yet
- Seedbox SSH blocked by Tailscale ACL — add SSH policy for operator MacBook → betty
