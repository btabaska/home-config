# `strip-trilium-config.py`

> Remove the read-27 Trilium artifacts from a Caddyfile / Homepage services.yaml /

**Path:** `foss-setup/scripts/notes-trial/strip-trilium-config.py` · **Category:** [notes-trial](index.md) · **Type:** Python

## What it does

```text
Remove the read-27 Trilium artifacts from a Caddyfile / Homepage services.yaml /
verification coverage manifest. Idempotent: if the artifact is already gone, it is a no-op.

Used by teardown-trilium.sh to revert the live config on the mini, but each transform is a
pure text edit so it can be run/tested against the repo mirrors too, e.g.:

    python3 strip-trilium-config.py \\
      --caddyfile configs/docker-stack/stacks/caddy/caddy/Caddyfile \\
      --homepage  configs/docker-stack/stacks/homepage/config/services.yaml \\
      --coverage  verification/coverage/mini.containers \\
      --check                 # report-only, exit 3 if anything still present, write nothing
```

## Environment / variables referenced

`DOMAIN`

## See also

- [`teardown-trilium.sh`](teardown-trilium-sh.md)
- [notes-trial scripts](index.md) · [All scripts](../index.md)
