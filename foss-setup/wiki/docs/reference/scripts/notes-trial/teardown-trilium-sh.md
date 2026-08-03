# `teardown-trilium.sh`

> fully revert the read-27 Trilium (TriliumNext) Obsidian-replacement trial.

**Path:** `foss-setup/scripts/notes-trial/teardown-trilium.sh` · **Category:** [notes-trial](index.md) · **Type:** Bash

## Synopsis

```
teardown-trilium.sh                          # dry-run: print the plan, touch nothing
```

## What it does

```text
 teardown-trilium.sh — fully revert the read-27 Trilium (TriliumNext) Obsidian-replacement trial.

 DRY-RUN by default: prints exactly what it would do and changes nothing. Add --apply to run.

 Usage:
   teardown-trilium.sh                          # dry-run: print the plan, touch nothing
   teardown-trilium.sh --apply                  # tear down the LIVE trial (keeps ./data notes)
   teardown-trilium.sh --apply --purge-data     # also delete the notes (after a backup tarball)
   teardown-trilium.sh --apply --repo-revert    # also git-revert the repo commit + print publish steps

 Live things removed: the trilium container, the Caddy vhost, the Homepage tile, the coverage
 manifest line, the verification check, and the Uptime-Kuma monitor. Because every byte of
 Trilium state is in /opt/stacks/trilium/data and nothing else was modified in place, this
 leaves no residue. The repo/config files are reverted with git (see --repo-revert).
```

## Environment / variables referenced

`APPLY`, `HERE`, `MINI`, `MINI_SSH`, `MONITOR`, `PURGE`, `REPO`, `REPO_REVERT`, `SHA`, `STACK`

## See also

- [`strip-trilium-config.py`](strip-trilium-config-py.md)
- [notes-trial scripts](index.md) · [All scripts](../index.md)
