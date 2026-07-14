# `tailscale-verify-direct.sh`

> tailscale-verify-direct.sh

**Path:** `foss-setup/scripts/network/tailscale-verify-direct.sh` · **Category:** [Network](index.md) · **Type:** Bash

## What it does

```text
 tailscale-verify-direct.sh

 Confirms peers are connected "direct" (peer-to-peer WireGuard) and NOT relayed
 through a DERP server. DERP works but is slower/higher-latency -- bad for
 game streaming, file sync, and backups. Also runs `netcheck` and flags the
 usual culprits (UDP blocked, symmetric NAT) and the UDP/41641 reminder.

 Refs:
   - Connection types (direct vs DERP):  https://tailscale.com/docs/reference/connection-types
   - netcheck fields / NAT traversal:    https://tailscale.com/kb/1082/firewall-ports/

 Usage:
   ./tailscale-verify-direct.sh                 # check all peers
   ./tailscale-verify-direct.sh nas cachyos     # also actively ping these peers until direct
```

## Environment / variables referenced

`NETCHECK`, `RELAYED`

## See also

- [`dns-resilience-verify.sh`](dns-resilience-verify-sh.md)
- [`tailscale-connectivity-test.sh`](tailscale-connectivity-test-sh.md)
- [`tailscale-install-up.sh`](tailscale-install-up-sh.md)
- [`tailscale-ssh-enable.sh`](tailscale-ssh-enable-sh.md)
- [`zbf-isolation-verify.sh`](zbf-isolation-verify-sh.md)
- [Network scripts](index.md) · [All scripts](../index.md)
