# `tailscale-ssh-enable.sh`

> tailscale-ssh-enable.sh

**Path:** `foss-setup/scripts/network/tailscale-ssh-enable.sh` · **Category:** [Network](index.md) · **Type:** Bash

## What it does

```text
 tailscale-ssh-enable.sh

 Turn on Tailscale SSH on this node so it accepts SSH over the tailnet —
 key-less, ACL-gated, with nothing exposed to the public internet. Run it on
 every host you want to administer (Mac mini, NAS-where-supported, rig, seedbox).
 Idempotent: safe to re-run.

 The ACTUAL access policy (who may SSH which host as which user) lives in your
 tailnet ACLs, NOT here — apply configs/network/tailscale-acl-ssh.hujson in the
 Tailscale admin console (Access Controls). This script only flips the per-node
 "accept SSH" switch.

 Refs:
   - Tailscale SSH:        https://tailscale.com/kb/1193/tailscale-ssh
   - ACL syntax (ssh):     https://tailscale.com/kb/1337/acl-syntax

 Usage:
   ./tailscale-ssh-enable.sh
```

## See also

- [`dns-resilience-verify.sh`](dns-resilience-verify-sh.md)
- [`tailscale-connectivity-test.sh`](tailscale-connectivity-test-sh.md)
- [`tailscale-install-up.sh`](tailscale-install-up-sh.md)
- [`tailscale-verify-direct.sh`](tailscale-verify-direct-sh.md)
- [`zbf-isolation-verify.sh`](zbf-isolation-verify-sh.md)
- [Network scripts](index.md) · [All scripts](../index.md)
