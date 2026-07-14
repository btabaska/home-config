# Checks — system

`foss-setup/verification/checks.d/system.yaml` — 8 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `sys-ansible-pull`

ansible-pull last run succeeded

- **host:** `mini` · **severity:** `crit` · **guards task:** `glue-03` · **enabled:** True
- **expects:** `^ExecMainStatus=0$`

```bash
systemctl show ansible-pull.service -p ExecMainStatus
```

## `sys-failed-units`

no failed systemd units on mini

- **host:** `mini` · **severity:** `warn` · **guards task:** `glue-03` · **enabled:** True
- **expects:** `^0$`

```bash
systemctl --failed --no-legend | wc -l
```

## `sys-disk-root`

root filesystem below 85% used

- **host:** `mini` · **severity:** `crit` · **guards task:** `glue-04` · **enabled:** True
- **expects:** `^([0-7]?[0-9]|8[0-5])$`

```bash
df --output=pcent / | tail -1 | tr -dc '0-9'
```

## `sys-docker-restart-loops`

no container with RestartCount > 3

- **host:** `mini` · **severity:** `warn` · **guards task:** `docker-12` · **enabled:** True
- **expects:** `^0$`

```bash
docker ps -q | xargs -r docker inspect --format '{{.Name}} {{.RestartCount}}' | awk '$2>3' | wc -l
```

## `sys-tailscale-peers`

tailscale up with at least 1 online peer

- **host:** `mini` · **severity:** `crit` · **guards task:** `net-05` · **enabled:** True
- **expects:** `^[1-9][0-9]*$`

```bash
tailscale status --json | python3 -c 'import json,sys;d=json.load(sys.stdin);print(sum(1 for p in d.get("Peer",{}).values() if p.get("Online")))'
```

## `sys-home-assistant`

Home Assistant answers on 192.168.10.50:8123

- **host:** `url` · **severity:** `crit` · **guards task:** `ha-01` · **enabled:** True
- **expects:** `^200$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://192.168.10.50:8123/
```

## `sys-seedbox-ssh`

seedbox reachable over SSH (disabled: SSH blocked by ACL)

- **host:** `local` · **severity:** `info` · **guards task:** `seed-01` · **enabled:** False
- **expects:** `^seedbox-ok$`

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 seedbox 'echo seedbox-ok'
```

## `sys-docker-subnet-squat`

no docker network overlaps 192.168.0.0/16 (LAN/VLAN space)

- **host:** `mini` · **severity:** `warn` · **guards task:** `ha-19` · **enabled:** True
- **expects:** `^0$`

```bash
docker network ls -q | xargs -n1 docker network inspect --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null | grep -c '^192\.168\.' || true
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
