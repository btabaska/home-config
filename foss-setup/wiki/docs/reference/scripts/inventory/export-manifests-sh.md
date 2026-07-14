# `export-manifests.sh`

> snapshot everything needed to rebuild THIS host into the

**Path:** `foss-setup/scripts/inventory/export-manifests.sh` · **Category:** [Inventory & manifests](index.md) · **Type:** Bash

## What it does

```text
 export-manifests.sh — snapshot everything needed to rebuild THIS host into the
                       control repo, then regenerate the human-readable inventory.

 What it captures into hosts/<hostname>/ (idempotent — overwrites each run):
   - Explicitly-installed packages (per distro):
       Arch/CachyOS : pacman -Qqe  (+ AUR/foreign packages via pacman -Qqm)
       Ubuntu/Debian: apt-mark showmanual
   - flatpak applications (if flatpak present)
   - Pinned container image tags (grep 'image:' across /opt/stacks)
   - crontabs: `crontab -l` per user + a listing of /etc/cron.d
   - systemd timers (system) + user timer unit listing (~/.config/systemd/user)
   Then calls gen-inventory-md.sh to refresh configs/inventory/inventory.md.

 Designed for a weekly systemd timer (export-manifests.timer). Commit the
 resulting hosts/<hostname>/ files so the box is reproducible from git.

 Optional env:
   REPO_ROOT=/path/to/foss-setup     # defaults to two levels up from this script
   STACKS_DIR=/opt/stacks            # where compose stacks live
   NTFY_URL=https://ntfy.example/inventory   # pinged on failure (optional)
```

## Environment / variables referenced

`HOST`, `NTFY_URL`, `OUT_DIR`, `REPO_ROOT`, `SCRIPT_DIR`, `STACKS_DIR`, `SUDO_USER`, `USER`, `USER_HOME`

## See also

- [`etckeeper-setup.sh`](etckeeper-setup-sh.md)
- [`gen-inventory-md.sh`](gen-inventory-md-sh.md)
- [Inventory & manifests scripts](index.md) · [All scripts](../index.md)
