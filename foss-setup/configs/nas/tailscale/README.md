# NAS Tailscale — TUN mode (fix-21)

The Synology Tailscale package defaults to userspace networking: `tailscale ping`
works but **outbound TCP to tailnet IPs times out** (no `tailscale0` interface, route
to 100.64.0.0/10 falls through to the LAN gateway). That silently broke the documented
"arrs/soularr reach the seedbox over Tailscale" design until 2026-07-17.

Fix (applied live):

```
sudo /var/packages/Tailscale/target/bin/tailscale configure synology
sudo /usr/syno/bin/synosystemctl restart pkgctl-Tailscale.service   # drops tailnet ssh briefly
```

After it: `tailscale0` interface exists and containers on the NAS bridge reach
`100.119.134.94` (seedbox) transparently.

`13.task` (mirror of `/usr/syno/etc/synoschedule.d/root/13.task`) re-runs
`tailscale configure synology` daily at 00:00 so a DSM/package update can't silently
revert TUN mode. Deploy a changed task file with `ssh nas 'cat > …'` (SFTP disabled),
then `sudo /usr/syno/bin/synoschedtask --sync`. The `seedbox-tailnet-*` checks in
`verification/checks.d/seedbox.yaml` page ntfy if the path breaks anyway.

NOTE: the NAS `ssh nas` alias rides the tailnet (`nas.tailb31641.ts.net`) — restarting
this package kills your own session; reconnect after ~15s.
