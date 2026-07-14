# `zbf-isolation-verify.sh`

> zbf-isolation-verify.sh

**Path:** `foss-setup/scripts/network/zbf-isolation-verify.sh` · **Category:** [Network](index.md) · **Type:** Bash

## What it does

```text
 zbf-isolation-verify.sh

 Verify UniFi ZBF isolation policies (net-05 "Done when" criteria) from a client on
 any VLAN. Auto-detects zone from the local IP when using the 192.168.{vlan}.0/24 scheme
 from vlan-zone-firewall-plan.md, or set ZONE= explicitly.

 Usage:
   ./zbf-isolation-verify.sh                          # auto-detect zone
   ZONE=iot TRUSTED_IP=192.168.10.50 ./zbf-isolation-verify.sh
   ZONE=work TRUSTED_IP=192.168.10.1 ./zbf-isolation-verify.sh
   ZONE=trusted IOT_IP=192.168.20.10 ./zbf-isolation-verify.sh

 Refs:
   - configs/network/firewall-policy-walkthrough.md
   - configs/network/firewall-policy-order.md
```

## Environment / variables referenced

`INTERNET_IP`, `IOT_IP`, `LOCAL_IP`, `PING_COUNT`, `PING_TIMEOUT`, `TRUSTED_IP`, `ZONE`

## See also

- [`dns-resilience-verify.sh`](dns-resilience-verify-sh.md)
- [`tailscale-connectivity-test.sh`](tailscale-connectivity-test-sh.md)
- [`tailscale-install-up.sh`](tailscale-install-up-sh.md)
- [`tailscale-ssh-enable.sh`](tailscale-ssh-enable-sh.md)
- [`tailscale-verify-direct.sh`](tailscale-verify-direct-sh.md)
- [Network scripts](index.md) · [All scripts](../index.md)
