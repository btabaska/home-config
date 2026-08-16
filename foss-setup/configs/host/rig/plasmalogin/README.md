# plasmalogin autologin (`/etc/plasmalogin.conf`)

Mirror of the live rig's `/etc/plasmalogin.conf`. The rig's entire game-streaming
chain is **session-scoped**: `apollo.service` (`WantedBy=xdg-desktop-autostart.target`)
and `display-policy.service` (`WantedBy=graphical-session.target`) only start when the
btabaska Plasma Wayland session logs in. With no autologin, the rig boots to the
plasmalogin greeter and both units silently never start — the host looks green while
streaming is completely dead.

**Incident 2026-08-16:** the `[Autologin]` section had `Session=plasma` but no
`User=` key (lost around the SDDM → plasmalogin migration), so the Aug 3 reboot
parked the rig at the greeter and Apollo was down for 13 days unnoticed. Fixed by
restoring `User=btabaska`; the old conf is at `/etc/plasmalogin.conf.bak-20260816`
on the rig. Now guarded by verification checks `game-apollo-serverinfo` (consumer
probe from the mini) and `game-apollo-session-display` (plug + session + autologin
key + unit, on the rig) in `verification/checks.d/gaming.yaml`.

To apply: copy to `/etc/plasmalogin.conf` (root), then
`sudo systemctl restart plasmalogin.service` — safe only when nobody is logged into
the desktop; the restart tears down the greeter and auto-logs-in btabaska.
