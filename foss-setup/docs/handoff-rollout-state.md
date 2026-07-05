# Rollout handoff state — 2026-07-03 (session 2)

Import this into the tracker (`docs/index.html`) so checkmarks match reality for the next agent.

## Quick import (browser)

1. Open `foss-setup/docs/index.html` in your browser (file:// or served).
2. Click **Import progress** and choose `docs/progress-backup-2026-07-03.json`.

**Or** paste in DevTools console:

```javascript
fetch('../docs/progress-backup-2026-07-03.json')
  .then(r => r.json())
  .then(obj => {
    const done = obj.done || obj;
    const key = 'foss-analogue-progress-v1';
    const merged = { ...(JSON.parse(localStorage.getItem(key) || '{}')), ...done };
    localStorage.setItem(key, JSON.stringify(merged));
    location.reload();
  });
```

(Adjust the fetch path if the HTML is not opened from `docs/`.)

## Progress snapshot

| Metric | Value |
|--------|-------|
| Completed | **67 / 162** (41%) |
| Previous backup | `progress-backup-2026-07-03.json` (66 done) |
| This session | +1 task (nas-08 Immich) |

## Completed this session

| Wave | Tasks |
|------|-------|
| **G — Photos** | nas-08 Immich (v2.7.5, OpenVINO ML, Caddy front, pg_dump script) |

## Completed prior session

| Wave | Tasks |
|------|-------|
| **F — Life apps** | docker-04 Miniflux, docker-05 Navidrome, doc-02 Mealie |
| **A — Ops wave 1** | docker-07 AdGuard, docker-08 Dockge, docker-09 ntfy, docker-10 Beszel, glue-05 Forgejo |
| **dns-01** | Core (Unbound + AdGuard upstream + DNSSEC + `*.tabaska.us` rewrite) |
| **B — Backbone** | nas-01 snapshots (user confirmed) |
| **C — Media** | seed-07 E2E Plex, seed-06 MusicSeerr, seed-09 slskd, nas-29 Soularr, docker-16 MusicSeerr, **nas-08 Immich** |
| **D — Ops wave 2** | docker-06 Caddy, docker-11 Uptime Kuma, docker-15 Homepage |
| **E — Ops wave 3** | docker-13 git stacks, glue-07 Ansible, glue-08 ansible-pull, sbom-03 etckeeper, sbom-04 manifests, sbom-01 DepTrack, sbom-02 nightly Syft |

## Partial / deferred (do NOT mark done without verifying)

| Task | State |
|------|-------|
| **glue-01** | No UPS — nut-client on mini ready |
| **dns-01** | Core done (Unbound + AdGuard + rewrites). **Resilience not done** — see dns-02–dns-05 |
| **dns-02** | NAS secondary AdGuard — **AI can deploy** (compose + rewrite mirror) |
| **dns-03** | UniFi DHCP fail-open chain (mini → NAS → gateway) — **you** (UniFi GUI) |
| **dns-04** | Outage runbook + verify script — **AI can run drill** |
| **dns-05** | NAT :53 + DoH blocking — **you** (UniFi GUI); only after dns-04 |
| **glue-08** | mini timer active; ansible-pull fails on scaffold (`files/id_ed25519.pub`). Rig not deployed |
| **sbom-02** | mini + NAS scheduled; rig not done; verify first upload in DepTrack UI |
| **glue-06** | Rebuild drill capstone — not started |
| **glue-04b** | chezmoi fleet rig+mini — not started |
| **nas-08** | Deploy done — create admin, enable Quick Sync, test upload; schedule `/volume1/docker/immich/immich-pg-dump.sh` in DSM Task Scheduler |
| **B2 / sec-03 / handoff-05** | User skip until B2 ready |

## Key URLs

| Service | URL |
|---------|-----|
| Miniflux | https://rss.tabaska.us |
| Navidrome | https://music.tabaska.us |
| Mealie | https://recipes.tabaska.us |
| Homepage | https://home.tabaska.us |
| AdGuard | https://dns.tabaska.us |
| Uptime Kuma | https://uptime.tabaska.us |
| DepTrack | https://deptrack.tabaska.us |
| Immich | https://immich.tabaska.us (LAN :2283) |
| Forgejo | http://macmini.tailb31641.ts.net:3030 |

DNS: **Currently gateway-only** (user disabled AdGuard DHCP after 2026-07-03 outage). Target fail-open chain: `#1` mini `192.168.10.2`, `#2` NAS `192.168.10.4`, `#3` gateway `192.168.10.1` — see `configs/network/dns-resilience-plan.md`.

## Forgejo repos

| Repo | Contents |
|------|----------|
| `home/homelab` | Control repo (foss-setup at root) |
| `home/docker-stacks` | Live `/opt/stacks` on mini |

## Secrets

- Vault: `foss-setup/.handoff-secrets.yaml` (local only, never commit)
- DepTrack admin password: `/tmp/dtrack-admin-note.txt` on operator MacBook — **move to vault**
- ntfy admin password was briefly in git history of docker-stacks — rotate

## Suggested next_up

1. **dns-02** NAS secondary AdGuard (AI-autonomous when you're ready)
2. **dns-03** UniFi fail-open DHCP chain (15 min in UniFi UI)
3. **ha-01** Home Assistant onboarding
4. **nas-08b** SD card import (after Immich admin + API key)
5. **read-07** Wallabag

## Host notes

- mini hostname: `macmini` (Ansible inventory alias)
- NAS docker: `sudo /var/packages/ContainerManager/target/usr/bin/docker compose` from stack dirs
- Soularr → slskd via public IP `185.162.184.38:5030` (Tailscale DERP blocks NAS→seedbox TS IP)
- Caddy: `local_tls` (no Cloudflare token yet)
- Life apps credentials: `~/life-apps-credentials.txt` on mini (Miniflux admin; Mealie needs first-visit admin)
- Immich DB password in vault (`immich.db_password`); uploads at `/volume1/photo`
