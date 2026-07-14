# Decommission the old NAS torrent stack

> Historical runbook (Phase 2) for tearing down the retired home torrent apparatus: NAS qBittorrent + Gluetun VPN + dual-LAN policy routing, now superseded by the seedbox.

_Source: `foss-setup/configs/seedbox/decommission-old-nas-torrent.md` · migrated + validated 2026-07-14_

**Phase 2 — do this LAST, only after the seedbox pipeline is verified end-to-end** (a Seerr request flows seedbox → sync → Plex). The old setup torrented on the DS920+ (the NAS) behind a home VPN; thousands of simultaneous peer connections exhausted the Dream Wall's conntrack table until a reboot — the classic torrent-kills-the-router failure, worsened by VPN MTU overhead. The 5 Mbps cap was a band-aid. The seedbox removes the root cause, so this whole apparatus comes out.

> Reversibility: keep configs/exports until the seedbox has run clean for ~1–2 weeks. Then delete.

!!! note "Validated against live NAS (2026-07-14)"
    Decommission is complete. `docker ps -a` on the NAS shows **no `qbittorrent` and no `gluetun` container** (neither running nor stopped). The full container list is only the current stack: `sonarr radarr lidarr readarr prowlarr unpackerr flaresolverr rreading-glasses(+ -db) soularr beets calibre-web-automated stash immich(server/ml/postgres/redis) adguardhome-nas beszel-agent diun`. `ss -tunp` finds no `wireguard`/`openvpn`/`:6881`/`:8080` sockets ("no torrent/vpn sockets — clean"). `ip route get 1.1.1.1` exits via the normal LAN gateway `192.168.10.1`. Note: `ip rule show` still has per-NIC source rules `from 192.168.10.3 lookup eth0-table` and `from 192.168.10.4 lookup eth1-table` — this is ordinary dual-NIC source-based routing (both NICs active), NOT the old VPN policy-routing rule (there is no `from <nas-vpn-ip> lookup <vpn-table>` entry). The torrent-specific routing described in Section 2 has been undone.

---

## Pre-flight (don't skip)

- [ ] Seedbox pipeline confirmed working end-to-end (request → download → import → sync → Plex → Seerr "Available").
- [ ] **Back up the UniFi config** (Settings → System → Backup) before touching routing/firewall — the Zone-Based Firewall is a one-way door. See the UniFi network plan `reference/network/vlan-zone-firewall-plan.md` (source `reference/network/vlan-zone-firewall.md`).
- [ ] Note your current NAS qBittorrent **active torrents** — anything you still want to seed should be re-added on the seedbox first (re-download or migrate the `.torrent`/resume data).
- [ ] Export any *arr config you want to keep (Sonarr/Radarr settings) — though the seedbox now owns these.

---

## 1. Stop & remove the NAS download containers

If running via Synology Container Manager / docker-compose on the NAS:

- [ ] Stop the stack:
      ```bash
      docker compose down            # in the qbittorrent/gluetun compose dir
      ```
- [ ] Confirm nothing is still bound to the VPN/torrent ports:
      ```bash
      sudo ss -tulpn | grep -E 'qbittorrent|gluetun|8080|6881' || echo "clear"
      ```
- [ ] Remove containers + the Gluetun VPN container:
      ```bash
      docker rm -f qbittorrent gluetun 2>/dev/null || true
      docker image prune -a            # optional: reclaim image space
      ```
- [ ] If installed as a DSM package (not Docker): uninstall the Download Station / qBittorrent package from Package Center.
- [ ] Delete the Gluetun config + WireGuard/OpenVPN credentials (they're no longer needed; the seedbox is your private egress for P2P now). Securely remove any saved VPN provider keys.

!!! note "Validated against live NAS (2026-07-14)"
    This section is done: `docker ps -a` lists neither `qbittorrent` nor `gluetun`. Nothing is bound to `:6881`/`:8080` for torrent/VPN, and no WireGuard/OpenVPN sockets remain.

---

## 2. Undo the dual-LAN policy routing on the NAS

The old design used the NAS's second NIC + policy routes to force torrent traffic out the VPN. Remove it.

- [ ] **DSM GUI path:** Control Panel → Network → Network Interface → remove the second LAN's static route / gateway override; if you created a bonded/second profile only for the VPN, delete it.
- [ ] **If you hand-added routes/rules over SSH**, list and remove them:
      ```bash
      ip rule show                      # find the custom 'from <nas-vpn-ip> lookup <table>' rule
      sudo ip rule del from <NAS_VPN_IP> lookup <TABLE_ID>
      ip route show table <TABLE_ID>    # inspect
      sudo ip route flush table <TABLE_ID>
      ```
      Then remove the matching entries from any boot script / `Task Scheduler` boot-up task that re-applied them (DSM → Control Panel → Task Scheduler → look for a "torrent routing" boot task).
- [ ] Reboot the NAS and confirm a single default route and normal LAN reachability:
      ```bash
      ip route get 1.1.1.1              # should exit via your normal LAN gateway
      ```
- [ ] **Free the second NAS LAN port:** leave it unused, or repurpose it — e.g. enable **Link Aggregation / failover** in Control Panel → Network → Bond (only if your switch supports it).

!!! note "Validated against live NAS (2026-07-14)"
    The VPN policy route is gone — `ip rule show` has no `from <nas-vpn-ip> lookup <vpn-table>` entry, and `ip route get 1.1.1.1` exits via `192.168.10.1`. The NAS is still running BOTH NICs (`.3` on `eth0`, `.4` on `eth1`) with normal per-interface source-routing rules (`from 192.168.10.3 lookup eth0-table`, `from 192.168.10.4 lookup eth1-table`), so the second LAN port was NOT freed — it is repurposed as an ordinary active interface, not as VPN egress. That is the intended end-state, just not the "leave it unused" option.

---

## 3. Drop the 5 Mbps throttle

The bandwidth cap existed only to keep the swarm from melting the router. Remove it everywhere it lives:

- [ ] qBittorrent global rate limits — gone with the container (above).
- [ ] **Dream Wall / UniFi:** Settings → check for any **Smart Queues / QoS / per-client rate limit** or a Traffic Rule that throttled the NAS — remove or disable it.
- [ ] Any per-port/per-IP shaping you added for the torrent box — remove.

---

## 4. Firewall / router cleanup (UniFi)

- [ ] Remove the **port-forward(s)** that exposed the old qBittorrent listen port (e.g. 6881) — the seedbox needs no inbound holes at home.
- [ ] Remove firewall rules/zones created specifically for the VPN-routed NAS torrent traffic.
- [ ] If you forwarded UDP for the VPN, remove it (keep **UDP 41641** only if you use it for Tailscale direct connections — that's unrelated and still wanted).
- [ ] Verify conntrack is healthy now (no more swarm): on the gateway, table usage should sit low.

---

## 5. Verify & document

- [ ] Reboot the Dream Wall once; confirm no conntrack pressure and normal browsing/streaming.
- [ ] Confirm Plex still serves the existing library (untouched on the NAS) and new titles arrive only via the seedbox sync.
- [ ] Confirm the NAS no longer initiates any P2P/VPN connections:
      ```bash
      sudo ss -tunp | grep -iE 'wireguard|openvpn|6881' || echo "no torrent/vpn sockets — clean"
      ```
- [ ] Update your runbook/Git notes: "home VPN torrent stack retired YYYY-MM-DD; acquisition is seedbox-only." Commit the removed compose files' deletion so the repo reflects reality.

> If you ever want to torrent at home again, the real fix for the crashes is simply capping qBittorrent's global max connections (~200) and per-torrent peers — but with the seedbox you won't need to.

---

[← Seedbox & music reference](index.md)
