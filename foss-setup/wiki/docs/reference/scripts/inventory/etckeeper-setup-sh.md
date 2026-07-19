# `etckeeper-setup.sh`

> put /etc under version control with etckeeper, and commit

**Path:** `foss-setup/scripts/inventory/etckeeper-setup.sh` · **Category:** [Inventory & manifests](index.md) · **Type:** Bash

## Synopsis

```
sudo ./etckeeper-setup.sh
```

## What it does

```text
 etckeeper-setup.sh — put /etc under version control with etckeeper, and commit
                      automatically on change via a systemd .path watcher.

 What it does (idempotent — safe to re-run):
   1. Detects the package manager (apt vs pacman) and installs etckeeper.
   2. Installs our etckeeper.conf to /etc/etckeeper/etckeeper.conf.
   3. Runs `etckeeper init` + an initial commit (no-op if already a repo).
   4. Installs etc-watch.path AND writes its companion etckeeper-commit.service.
   5. Enables the .path unit so /etc changes are committed automatically.

 Docs: https://etckeeper.branchable.com/

 >>> /etc HOLDS SECRETS. If you configure PUSH_REMOTE in etckeeper.conf it MUST
     point at a PRIVATE per-host repo (e.g. Forgejo). Never push /etc publicly. <<<

 Skipped on Synology/DSM (no systemd, managed appliance).

 Usage:  sudo ./etckeeper-setup.sh
 Optional env:
   CONF_SRC=/path/to/etckeeper.conf   # defaults to ../../configs/inventory/etckeeper.conf
```

## Environment / variables referenced

`COMMIT_SERVICE`, `CONF_SRC`, `DAILY_DROPIN_DIR`, `EUID`, `PATH_UNIT`, `PATH_UNIT_SRC`, `SCRIPT_DIR`, `SERIALIZE_WRAPPER`, `SYSTEMD_DIR`

## See also

- [`export-manifests.sh`](export-manifests-sh.md)
- [`gen-inventory-md.sh`](gen-inventory-md-sh.md)
- [Inventory & manifests scripts](index.md) · [All scripts](../index.md)
