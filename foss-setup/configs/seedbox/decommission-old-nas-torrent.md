# Decommission the Old Home Torrent Stack (NAS qBittorrent + Gluetun + dual-LAN policy routing)

**Phase 2 — do this LAST, only after the seedbox pipeline is verified end-to-end** (a Seerr request
flows seedbox → sync → Plex). The old setup torrented on the DS920+ behind a home VPN; thousands of
simultaneous peer connections exhausted the Dream Wall's conntrack table until a reboot — the classic
torrent-kills-the-router failure, worsened by VPN MTU overhead. The 5 Mbps cap was a band-aid. The
seedbox removes the root cause, so this whole apparatus comes out.

> Reversibility: keep configs/exports until the seedbox has run clean for ~1–2 weeks. Then delete.

---

## Pre-flight (don't skip)

- [ ] Seedbox pipeline confirmed working end-to-end (request → download → import → sync → Plex → Seerr "Available").
- [ ] **Back up the UniFi config** (Settings → System → Backup) before touching routing/firewall — the
      Zone-Based Firewall is a one-way door. Ref: UniFi network plan (`configs/network/vlan-zone-firewall-plan.md`).
- [ ] Note your current NAS qBittorrent **active torrents** — anything you still want to seed should be
      re-added on the seedbox first (re-download or migrate the `.torrent`/resume data).
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
- [ ] If installed as a DSM package (not Docker): uninstall the Download Station / qBittorrent
      package from Package Center.
- [ ] Delete the Gluetun config + WireGuard/OpenVPN credentials (they're no longer needed; the seedbox
      is your private egress for P2P now). Securely remove any saved VPN provider keys.

---

## 2. Undo the dual-LAN policy routing on the NAS

The old design used the NAS's second NIC + policy routes to force torrent traffic out the VPN. Remove it.

- [ ] **DSM GUI path:** Control Panel → Network → Network Interface → remove the second LAN's static
      route / gateway override; if you created a bonded/second profile only for the VPN, delete it.
- [ ] **If you hand-added routes/rules over SSH**, list and remove them:
      ```bash
      ip rule show                      # find the custom 'from <nas-vpn-ip> lookup <table>' rule
      sudo ip rule del from <NAS_VPN_IP> lookup <TABLE_ID>
      ip route show table <TABLE_ID>    # inspect
      sudo ip route flush table <TABLE_ID>
      ```
      Then remove the matching entries from any boot script / `Task Scheduler` boot-up task that
      re-applied them (DSM → Control Panel → Task Scheduler → look for a "torrent routing" boot task).
- [ ] Reboot the NAS and confirm a single default route and normal LAN reachability:
      ```bash
      ip route get 1.1.1.1              # should exit via your normal LAN gateway
      ```
- [ ] **Free the second NAS LAN port:** leave it unused, or repurpose it — e.g. enable **Link
      Aggregation / failover** in Control Panel → Network → Bond (only if your switch supports it).

---

## 3. Drop the 5 Mbps throttle

The bandwidth cap existed only to keep the swarm from melting the router. Remove it everywhere it lives:

- [ ] qBittorrent global rate limits — gone with the container (above).
- [ ] **Dream Wall / UniFi:** Settings → check for any **Smart Queues / QoS / per-client rate limit**
      or a Traffic Rule that throttled the NAS — remove or disable it.
- [ ] Any per-port/per-IP shaping you added for the torrent box — remove.

---

## 4. Firewall / router cleanup (UniFi)

- [ ] Remove the **port-forward(s)** that exposed the old qBittorrent listen port (e.g. 6881) — the
      seedbox needs no inbound holes at home.
- [ ] Remove firewall rules/zones created specifically for the VPN-routed NAS torrent traffic.
- [ ] If you forwarded UDP for the VPN, remove it (keep **UDP 41641** only if you use it for Tailscale
      direct connections — that's unrelated and still wanted).
- [ ] Verify conntrack is healthy now (no more swarm): on the gateway, table usage should sit low.

---

## 5. Verify & document

- [ ] Reboot the Dream Wall once; confirm no conntrack pressure and normal browsing/streaming.
- [ ] Confirm Plex still serves the existing library (untouched on the NAS) and new titles arrive only
      via the seedbox sync.
- [ ] Confirm the NAS no longer initiates any P2P/VPN connections:
      ```bash
      sudo ss -tunp | grep -iE 'wireguard|openvpn|6881' || echo "no torrent/vpn sockets — clean"
      ```
- [ ] Update your runbook/Git notes: "home VPN torrent stack retired YYYY-MM-DD; acquisition is
      seedbox-only." Commit the removed compose files' deletion so the repo reflects reality.

> If you ever want to torrent at home again, the real fix for the crashes is simply capping
> qBittorrent's global max connections (~200) and per-torrent peers — but with the seedbox you won't need to.
