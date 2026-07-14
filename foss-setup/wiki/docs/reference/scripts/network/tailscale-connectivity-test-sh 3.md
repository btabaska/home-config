# `tailscale-connectivity-test.sh`

> tailscale-connectivity-test.sh

**Path:** `foss-setup/scripts/network/tailscale-connectivity-test.sh` · **Category:** [Network](index.md) · **Type:** Bash

## What it does

```text
 tailscale-connectivity-test.sh

 Quick end-to-end reachability test across the tailnet. For each online peer it:
   1) runs a Tailscale-layer ping (works even when ICMP is firewalled), and
   2) optionally TCP-probes a service port (e.g. NAS 5001, SSH 22).
 Idempotent and read-only -- safe to run any time as a health check.

 Refs:
   - tailscale ping / status:  https://tailscale.com/docs/reference/connection-types

 Usage:
   ./tailscale-connectivity-test.sh
   PORTS="22 5001 8123" ./tailscale-connectivity-test.sh    # also TCP-probe these ports
```

## Environment / variables referenced

`PEERS`, `PORTS`

## See also

- [`dns-resilience-verify.sh`](dns-resilience-verify-sh.md)
- [`tailscale-install-up.sh`](tailscale-install-up-sh.md)
- [`tailscale-ssh-enable.sh`](tailscale-ssh-enable-sh.md)
- [`tailscale-verify-direct.sh`](tailscale-verify-direct-sh.md)
- [`zbf-isolation-verify.sh`](zbf-isolation-verify-sh.md)
- [Network scripts](index.md) · [All scripts](../index.md)
