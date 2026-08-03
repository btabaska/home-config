# rig avahi-daemon — restrict mDNS to the physical LAN (fix-64 / SM15)

**Problem (SM15):** avahi-daemon published the rig's hostname on **every** interface
— `enp10s0`, `tailscale0`, `docker0`, every `br-*` docker bridge and every `veth*`
pair. Docker constantly creates/destroys veth interfaces (container start/stop,
health-check restarts), and each event made avahi re-register `cachyos.local`,
see the record it had just announced on another interface, declare a **"Host name
conflict"**, and rename itself `cachyos-2`, `cachyos-3`, … `cachyos-8306`. Result:
1,856 conflicts per boot (~1 every 50s), `cachyos.local` no longer resolved, and
Apollo/Moonlight discovery of the rig was effectively broken.

**Fix:** bind avahi to the physical LAN interface only. mDNS/Moonlight discovery
is a LAN concern; the tailnet uses MagicDNS and the docker bridges have no business
carrying the host record.

In `/etc/avahi/avahi-daemon.conf`, under `[server]`:

```ini
allow-interfaces=enp10s0
```

Apply: `sudo systemctl restart avahi-daemon`.

**Verify:**
```
avahi-resolve -n cachyos.local          # -> cachyos.local  192.168.10.12
journalctl -u avahi-daemon --since -5min | grep -c "Host name conflict"   # -> 0
```

This is host-level config that **no role re-applies** (see the parent
`configs/host/rig/README.md`) — land any change here **and** live. Regression is
monitored by the `rig-mdns-fw-quiet` verification check.
