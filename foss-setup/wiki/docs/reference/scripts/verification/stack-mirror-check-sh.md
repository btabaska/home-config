# `stack-mirror-check.sh`

> repo↔live drift guard for the mini compose fleet

**Path:** `foss-setup/scripts/verification/stack-mirror-check.sh` · **Category:** [verification](index.md) · **Type:** Bash

## Synopsis

```
stack-mirror-check.sh mirrors|manifest
```

## What it does

```text
 stack-mirror-check.sh — repo↔live drift guard for the mini compose fleet
 (fix-41; classes M48 "live stack with no repo mirror", M49 "polluted image
 manifest", M51 "live .env keys missing from the repo example").

 Designed to run ON the mini FROM a fetched clone of home/homelab at origin/main
 HEAD (same pattern as wiki-drift-check.sh) so it always judges live state
 against what a rebuild would actually check out. Invoked by the `stack-mirror-
 drift` and `manifest-image-purity` checks in verification/checks.d/git-hygiene.yaml.

 Usage:  stack-mirror-check.sh mirrors|manifest

   mirrors  — every live /opt/stacks/<name>/ that has a top-level compose file
              must have configs/docker-stack/stacks/<name>/<same filename>
              byte-identical in the repo, and (if the stack has a .env) every
              live .env key must exist in the repo .env.example. One-way on
              purpose: a live-only key is what a rebuild silently drops; an
              example-only key is cosmetic.
   manifest — the image NAME set in hosts/<host>/compose-images.txt must equal
              the name set greped from live top-level compose files. Names, not
              pins: pin bumps between weekly export runs are expected snapshot
              lag, a name that exists nowhere live is pollution (phantom image,
              .bak sweep-in) or a stale add/retire.

 Exit 0 + STACK-MIRRORS-OK / MANIFEST-PURITY-OK on success; exit 1 with one
 line per violation otherwise. Runbook: wiki/docs/runbooks/git-hygiene.md
```

## Environment / variables referenced

`COMPOSE_NAMES`, `HOST`, `MIRROR`, `MODE`, `ROOT`, `STACKS_DIR`

## See also

- [`deploy.sh`](deploy-sh.md)
- [verification scripts](index.md) · [All scripts](../index.md)
