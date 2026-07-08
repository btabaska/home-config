# sec-02/sec-05 executed overnight (pre-approved track, changes made)
- Docker log caps (10m x3): live on mini (docker restarted 02:18 UTC, 26s, all containers healthy after); rig daemon.json staged, activates w/ docker restart on next pull. Root cause found: rig was missing from [docker_hosts] — fixed in inventory.
- Existing containers keep unbounded logs until recreated; immich_server log at 97M flagged.
- unattended-upgrades on mini: security-only, Automatic-Reboot=false pinned via new role drop-in, dry-run clean. Rig: deliberately NO unattended pacman (partial-upgrade hazard); patch.yml push-mode is the arch lever — verified by design.
- ansible-pull green both hosts after (mini ok=35, rig ok=20; rig's first try failed because mini's docker restart blipped forgejo — recovered on retry).
- Progress: 122/201.
