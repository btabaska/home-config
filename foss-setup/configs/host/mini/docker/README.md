# mini /etc/docker/daemon.json (fix-19)

Docker `default-address-pools` so new container networks are carved as /24s from
`172.16.0.0/12` (then `10.201.0.0/16` overflow) and can **never** auto-allocate
into `192.168.x` — which on this box had squatted `192.168.16.0/20`, overlapping
the LAN and IoT VLAN (192.168.20.x).

Applied 2026-07-09 (out of the maintenance window, user-authorized): backed up to
`/etc/docker/daemon.json.bak-prefix19`, then `systemctl restart docker`. Existing
networks keep their subnets across the restart; only newly-created networks draw
from the pools. Verified: pools active in `docker info`, 0 × 192.168 networks,
all containers recovered.

`log-driver`/`log-opts` (10 MB × 3) are the pre-existing settings, preserved.
