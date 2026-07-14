# `gen-inventory-md.sh`

> render a readable what/where/version/status table at

**Path:** `foss-setup/scripts/inventory/gen-inventory-md.sh` · **Category:** [Inventory & manifests](index.md) · **Type:** Bash

## What it does

```text
 gen-inventory-md.sh — render a readable what/where/version/status table at
                       configs/inventory/inventory.md from the manifests that
                       export-manifests.sh wrote under hosts/<hostname>/.

 Idempotent: regenerates the whole file each run. Called by export-manifests.sh
 (and runnable standalone). Commit the result so the inventory tracks reality.

 Optional env:
   REPO_ROOT=/path/to/foss-setup    # defaults to two levels up from this script
   STACKS_DIR=/opt/stacks           # used to count running/compose services
```

## Environment / variables referenced

`HOST`, `HOST_DIR`, `OUT`, `PRETTY_NAME`, `REPO_ROOT`, `SCRIPT_DIR`, `STACKS_DIR`

## See also

- [`etckeeper-setup.sh`](etckeeper-setup-sh.md)
- [`export-manifests.sh`](export-manifests-sh.md)
- [Inventory & manifests scripts](index.md) · [All scripts](../index.md)
