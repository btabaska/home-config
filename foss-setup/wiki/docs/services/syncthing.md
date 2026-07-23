# syncthing

Syncthing v2 — local-first file-sync HUB on the NAS (foss-03)

| | |
|---|---|
| **Host** | [nas](../hosts/nas.md) |
| **URL** | http://192.168.10.4:8384 (hub GUI; LAN/Tailscale-only, admin auth) |
| **Source** | `foss-setup/configs/nas/syncthing/docker-compose.yml` |

## About

Syncthing is the fleet's local-first, no-cloud file-sync mesh (task foss-03, replacing Proton Drive; the shared hub for game-12 save-sync). It runs a hub-and-spoke topology across three devices, all on Syncthing v2 (2.1.2) for protocol parity. The always-on HUB is a container on the NAS at `/volume1/docker/syncthing` (`syncthing/syncthing:2.1.2`, digest-pinned; PUID 1026/PGID 100), publishing the sync protocol on host `:22000` (tcp+udp) and its Web GUI/REST API on `:8384`. The two spokes are the rig (a systemd *user* service, task read-02, folder `~/Sync`) and a NODE container on the mini at `/opt/stacks/syncthing` (repo mirror dir `syncthing-node`). Both spokes pair only to the NAS hub, so the hub relays changes even when a peer is offline. One shared folder `default` (label "Sync") syncs across all three: `/volume1/docker/syncthing/Sync` on the hub, `~/Sync` on the rig, `/opt/stacks/syncthing/home/Sync` on the mini. NO CLOUD is enforced, not assumed: each device carries the others' STATIC LAN addresses (`tcp://192.168.10.4:22000` etc.), and relays + global discovery are DISABLED fleet-wide, so peers connect only over direct LAN TCP (verify with `/rest/system/connections` — type must be `tcp`/`quic`, never `relay`). HUB SAFETY NET: the shared folder carries STAGGERED file versioning on the NAS copy, so a delete or bad edit propagated from any peer is recoverable from `Sync/.stversions/` for up to 30 days. All three GUIs are behind admin auth (vault `syncthing.gui_user` + `syncthing.{nas,mini,rig}_gui_password`) and are reverse-proxied LAN/Tailscale-only through the mini Caddy: the hub at https://syncthing.tabaska.us and the rig at https://syncthing-rig.tabaska.us — both use `header_up Host localhost` to pass Syncthing's anti-DNS-rebind host check. The rig GUI was rebound off localhost to `0.0.0.0:8384` (+ ufw `:8384` from the LAN) on 2026-07-22 so it can be proxied; `scripts/reading/syncthing-setup-cachyos.sh` codifies this behind `SYNCTHING_GUI_PASSWORD` (it never binds `0.0.0.0` unauthenticated). Homepage surfaces ONE Infrastructure tile: a `customapi` widget on the hub's `/rest/db/status?folder=default` (key `HOMEPAGE_VAR_SYNCTHING_HUB_KEY`) showing folder state / pending items / size, with click-through to the hub GUI (which lists every device, including any personal laptop/phone that joins). Consumer probes (verification, warn): `syncthing-hub-mesh-direct` asks the hub whether both spokes are connected over a direct, non-relay transport, and `syncthing-gui-urls` confirms both reverse-proxy URLs serve real Syncthing.

## Containers

| Service | Image (pinned) | Ports |
|---|---|---|
| `syncthing` | `syncthing/syncthing:2.1.2@sha256:4464f4161dd0251e20d46bb3aec83363db75d80cef1abdd5d5fd4054b04a004d` | `8384:8384`, `22000:22000/tcp`, `22000:22000/udp`, `21027:21027/udp` |

## Volumes

| Service | Volume |
|---|---|
| `syncthing` | `/volume1/docker/syncthing:/var/syncthing` |

## Troubleshooting

- **A peer shows connected but over a public relay (168.x address, type `relay-*`) instead of the LAN — file data is leaving the LAN, defeating the no-cloud goal. Most often the rig.** — A firewall is blocking inbound `:22000` at the peer, so the hub can only reach it via relay. On the rig (CachyOS ships ufw active), open the LAN: `sudo ufw allow from 192.168.10.0/24 to any port 22000 proto tcp` (and `proto udp`, plus `21027/udp`). This is codified in `scripts/reading/syncthing-setup-cachyos.sh`. Then confirm the pair upgraded to `tcp` in each side's `/rest/system/connections`. Relays and global discovery are disabled in each node's options; do not re-enable them.
- **A file created on one device never appears on the others.** — Check the pair is connected AND direct (`curl -H "X-API-Key: $API" http://127.0.0.1:8384/rest/system/connections`; API key in each host's `config.xml`). Then confirm the `default` folder is shared to that peer on BOTH ends (`/rest/config/folders/default` devices list must include the peer's ID) and not paused/errored (`/rest/db/status?folder=default` state should be `idle`). The folder path must exist on disk with a `.stfolder` marker.
- **A file was deleted or overwritten by a bad sync and you need it back.** — On the NAS hub, look under `/volume1/docker/syncthing/Sync/.stversions/` — staggered versioning keeps timestamped copies (`name~YYYYMMDD-HHMMSS.ext`) for up to 30 days. Copy the wanted version back into `Sync/`; it re-propagates to the peers.

## Operations

```bash
# NAS stack — manage via DSM Container Manager (project: syncthing)
# or over SSH (sudo required): cd /volume1/docker/syncthing && sudo docker compose ps
```

Update procedure: [Runbooks → Update images](../runbooks/update-images.md). Full add/change loop: [Runbooks → Add a service](../runbooks/add-a-service.md).

*Generated by `scripts/docs/gen-wiki-services.py` — do not edit by hand; edit the compose file and regenerate.*
