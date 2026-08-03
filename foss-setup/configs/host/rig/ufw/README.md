# rig UFW — silence known-benign discovery log flood (fix-64 / SL12)

**Problem (SL12):** the rig's kernel log carried **8,000+ `[UFW BLOCK]` lines per
boot** (~5/min), drowning real signal (failure-pattern #7, noisy-log-degrades-signal):

- ~8,100/boot were **IPv6 Syncthing local-discovery multicast** to `ff12::8384`
  UDP `dport 21027`. The foss-03 mesh uses **static addresses**, so this discovery
  is unused. Ubuntu/CachyOS `before.rules` silently `RETURN`s IPv4 multicast in the
  `ufw-not-local` chain, but `before6.rules` **has no equivalent chain**, so the
  IPv6 copies hit the logged default-deny.
- ~6,300/boot were unsolicited UDP from **192.168.10.177** (a Samsung TV /
  SmartThings device, `dport 15600` + rotating high ports) doing benign LAN
  discovery.

**Fix:** silently `DROP` these two known-benign flows **before** they reach the
logging chain — they were already being blocked, we just stop journaling them. No
listening port is opened; the firewall posture is unchanged.

Applied as marked, idempotent blocks (grep `fleet-sweep-fix-64`):

`/etc/ufw/before.rules` — inserted in the `ufw-before-input` chain, right after the
`RELATED,ESTABLISHED -j ACCEPT` line:
```
# BEGIN fleet-sweep-fix-64 (SL12): silent-drop known-benign discovery noise (no UFW log)
-A ufw-before-input -s 192.168.10.177 -j DROP
-A ufw-before-input -p udp --dport 21027 -j DROP
# END fleet-sweep-fix-64
```

`/etc/ufw/before6.rules` — inserted in the `ufw6-before-input` chain, same anchor:
```
# BEGIN fleet-sweep-fix-64 (SL12): silent-drop known-benign discovery noise (no UFW log)
-A ufw6-before-input -p udp --dport 21027 -j DROP
# END fleet-sweep-fix-64
```

Apply: `sudo ufw reload`.

**Verify** (block count for these must stay flat):
```
journalctl -k -b 0 --since -1min | grep -c 'UFW BLOCK'   # was ~5/min, now ~0
```

Host-level config that **no role re-applies** — land here **and** live. Regression
is monitored by the `rig-mdns-fw-quiet` verification check.
