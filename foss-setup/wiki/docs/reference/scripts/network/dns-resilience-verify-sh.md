# `dns-resilience-verify.sh`

> confirm fail-open DNS chain (dns-04)

**Path:** `foss-setup/scripts/network/dns-resilience-verify.sh` · **Category:** [Network](index.md) · **Type:** Bash

## What it does

```text
 dns-resilience-verify.sh — confirm fail-open DNS chain (dns-04)

 Usage:
   ./dns-resilience-verify.sh
   MINI_IP=192.168.10.2 NAS_IP=192.168.10.4 GW_IP=192.168.10.1 ./dns-resilience-verify.sh

 Refs: configs/network/dns-resilience-plan.md
```

## Environment / variables referenced

`GW_IP`, `INTERNAL_NAME`, `MINI_IP`, `NAS_IP`, `TEST_NAME`

## See also

- [`tailscale-connectivity-test.sh`](tailscale-connectivity-test-sh.md)
- [`tailscale-install-up.sh`](tailscale-install-up-sh.md)
- [`tailscale-ssh-enable.sh`](tailscale-ssh-enable-sh.md)
- [`tailscale-verify-direct.sh`](tailscale-verify-direct-sh.md)
- [`zbf-isolation-verify.sh`](zbf-isolation-verify-sh.md)
- [Network scripts](index.md) · [All scripts](../index.md)
