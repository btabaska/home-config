# `syncthing-setup-cachyos.sh`

> syncthing-setup-cachyos.sh

**Path:** `foss-setup/scripts/reading/syncthing-setup-cachyos.sh` · **Category:** [Reading stack](index.md) · **Type:** Bash

## Synopsis

```
Safe to re-run: skips the pacman install if syncthing is already present and
```

## What it does

```text
 syncthing-setup-cachyos.sh

 Idempotent install + enable of Syncthing as a systemd *user* service on
 CachyOS (Arch-based desktop). Use this to P2P-sync your Calibre/KOReader
 books + reading-progress files between the desktop, the NAS, and devices —
 no cloud involved.

 Safe to re-run: skips the pacman install if syncthing is already present and
 only enables the unit if it isn't already enabled.

 Why a *user* service (not syncthing@user.service):
   - The user unit runs as you, with your $HOME and file ownership — exactly
     what you want for syncing files in your home dir on a desktop.
   - The system template unit (syncthing@.service) is meant for headless
     servers. See the ArchWiki for the distinction.
   - We enable `loginctl enable-linger` so Syncthing keeps running across
     logout/reboot without an active graphical session.

 Refs:
   - ArchWiki: https://wiki.archlinux.org/title/Syncthing
   - Autostart: https://docs.syncthing.net/users/autostart.html
   - First setup / GUI: https://docs.syncthing.net/intro/getting-started.html

 Usage:
   ./syncthing-setup-cachyos.sh
   The Web GUI then lives at http://127.0.0.1:8384 (add folders + remote
   device IDs there). To reach the GUI from another LAN machine, see the note
   printed at the end.
```

## Environment / variables referenced

`USER`

## See also

- [Reading stack scripts](index.md) · [All scripts](../index.md)
