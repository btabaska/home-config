# `cachyos-desktop-baseline.sh`

> cachyos-desktop-baseline.sh

**Path:** `foss-setup/scripts/setup/cachyos-desktop-baseline.sh` · **Category:** [Host setup](index.md) · **Type:** Bash

## What it does

```text
 cachyos-desktop-baseline.sh
 Install the browser + office baseline on the CachyOS (Arch) rig.

 What it sets up:
   * A browser (default: Firefox from the official repo). Optionally LibreWolf
     (hardened) and/or Zen (Firefox-based, polished) from the AUR.
   * LibreOffice (default: libreoffice-fresh, the 26.2 current branch) for
     offline office work. Set LIBREOFFICE_PKG=libreoffice-still for the prior
     (more conservative) maintenance branch, or =none to skip.

 Setting Kagi as the default search engine is a per-profile *browser* action and
 cannot be reliably scripted — it's documented at the end and printed on finish.

 Docs:
   - LibreOffice on Arch:   https://wiki.archlinux.org/title/LibreOffice
   - Firefox on Arch:       https://wiki.archlinux.org/title/Firefox
   - LibreWolf:             https://librewolf.net/installation/arch/
   - Zen browser (AUR):     https://aur.archlinux.org/packages/zen-browser-bin
   - Kagi default search:   https://help.kagi.com/kagi/getting-started/setting-default.html

 Idempotent: pacman/AUR installs use --needed, so re-running is a no-op for
 already-installed packages. Do NOT run as root — AUR builds must run as a normal
 user; the script calls sudo only where needed.

 Usage:
   ./cachyos-desktop-baseline.sh                       # Firefox + LibreOffice (default)
   BROWSERS="firefox zen" ./cachyos-desktop-baseline.sh
   BROWSERS="firefox librewolf zen" ./cachyos-desktop-baseline.sh
   LIBREOFFICE_PKG=libreoffice-still ./cachyos-desktop-baseline.sh   # prior branch instead
   LIBREOFFICE_PKG=none ./cachyos-desktop-baseline.sh                # skip office
```

## Environment / variables referenced

`AUR_HELPER`, `BROWSERS`, `EUID`, `LIBREOFFICE_PKG`

## See also

- [`install-docker-ubuntu.sh`](install-docker-ubuntu-sh.md)
- [`install-haos-vm.sh`](install-haos-vm-sh.md)
- [`nut-client-retire.sh`](nut-client-retire-sh.md)
- [`nut-client-ubuntu.sh`](nut-client-ubuntu-sh.md)
- [Host setup scripts](index.md) · [All scripts](../index.md)
