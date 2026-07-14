# `tailscale-install-up.sh`

> tailscale-install-up.sh

**Path:** `foss-setup/scripts/network/tailscale-install-up.sh` · **Category:** [Network](index.md) · **Type:** Bash

## Synopsis

```
Safe to re-run: skips install if already present, skips `up` if already logged in.
```

## What it does

```text
 tailscale-install-up.sh

 Idempotent install + bring-up of Tailscale on Ubuntu Server (Mac mini host).
 Safe to re-run: skips install if already present, skips `up` if already logged in.

 Refs:
   - Install on Linux:        https://tailscale.com/docs/install/linux
   - Connection types/ports:  https://tailscale.com/docs/reference/connection-types

 Usage:
   ./tailscale-install-up.sh                 # interactive login (prints a URL to open)
   TS_HOSTNAME=macmini ./tailscale-install-up.sh
   TS_AUTHKEY=tskey-auth-xxxx ./tailscale-install-up.sh   # unattended/headless
```

## Environment / variables referenced

`TS_AUTHKEY`, `TS_HOSTNAME`

## See also

- [`dns-resilience-verify.sh`](dns-resilience-verify-sh.md)
- [`tailscale-connectivity-test.sh`](tailscale-connectivity-test-sh.md)
- [`tailscale-ssh-enable.sh`](tailscale-ssh-enable-sh.md)
- [`tailscale-verify-direct.sh`](tailscale-verify-direct-sh.md)
- [`zbf-isolation-verify.sh`](zbf-isolation-verify-sh.md)
- [Network scripts](index.md) · [All scripts](../index.md)
