#!/usr/bin/env python3
"""Generate task-overrides.json for all tasks after net-13."""
import json
from pathlib import Path

OUT = Path(__file__).parent / "task-overrides.json"
R = Path(__file__).resolve().parents[2]  # foss-setup root
REPO = "~/Documents/Home/foss-setup"  # MacBook path in commands (adjust if cloned elsewhere)

def mac_repo():
    return f"cd {REPO}  # adjust if your clone lives elsewhere"

def P(*ids):
    return f"Prerequisite: {', '.join(ids)} complete."

def D(*pairs):
    return [{"title": a, "url": b} for a, b in pairs]

MAC_OPEN = "On your MacBook: open this task's verify block and keep the repo at ~/Documents/Home/foss-setup handy."

def nas_docker(app, src_subpath, dest=None, prereqs=(), extra_steps=None, extra_cmds=None, files=None, verify="", docs=None):
    """Standard NAS Container Manager deploy from MacBook."""
    if dest is None:
        dest = f"/volume1/docker/{app}"
    src = f"{REPO}/{src_subpath}"
    steps = [MAC_OPEN]
    if prereqs:
        steps.append(P(*prereqs))
    steps.extend([
        CM,
        f"`ssh nas 'sudo mkdir -p {dest}'`",
        f"`scp -r {src} nas:/tmp/{app}`",
        f"`ssh nas 'sudo rsync -a /tmp/{app}/ {dest}/'`",
        f"`ssh nas 'cd {dest} && cp -n .env.example .env 2>/dev/null || true'` — edit secrets before up",
        f"`ssh nas 'cd {dest} && docker compose pull && docker compose up -d'`",
        f"`ssh nas 'cd {dest} && docker compose ps'`",
    ])
    if extra_steps:
        steps.extend(extra_steps)
    cmds = [
        f"scp -r {src} nas:/tmp/{app}",
        f"ssh nas 'sudo rsync -a /tmp/{app}/ {dest}/'",
        f"ssh nas 'cd {dest} && docker compose up -d'",
        f"ssh nas 'cd {dest} && docker compose ps'",
    ]
    if extra_cmds:
        cmds.extend(extra_cmds)
    out = {"steps": steps, "commands": cmds, "files": files or [src_subpath], "verify": verify}
    if docs:
        out["docs"] = docs
    return out

def ustack(stack, port, env="fill secrets in .env", curl_path="/", no_curl=False):
    steps = [
        MAC_OPEN,
        P("docker-01", "docker-02"),
        f"`scp -r {REPO}/configs/docker-stack/stacks/{stack} mini:/tmp/{stack}`",
        f"`ssh mini 'sudo mkdir -p /opt/stacks/{stack} && sudo rsync -a /tmp/{stack}/ /opt/stacks/{stack}/'`",
        f"`ssh mini 'cd /opt/stacks/{stack} && cp -n .env.example .env 2>/dev/null || true'` — {env}",
        f"`ssh mini 'cd /opt/stacks/{stack} && docker compose up -d'`",
        f"`ssh mini 'docker compose -f /opt/stacks/{stack}/compose.yaml ps'`",
    ]
    if port and not no_curl:
        steps.append(f"MacBook browser (Tailscale): http://macmini.<tailnet>:{port}")
    cmds = [
        f"scp -r {REPO}/configs/docker-stack/stacks/{stack} mini:/tmp/{stack}",
        f"ssh mini 'sudo rsync -a /tmp/{stack}/ /opt/stacks/{stack}/'",
        f"ssh mini 'cd /opt/stacks/{stack} && cp -n .env.example .env && docker compose up -d'",
    ]
    if port and not no_curl:
        cmds.append(f"ssh mini 'curl -sfI http://127.0.0.1:{port}{curl_path} | head -1'")
    return {
        "steps": steps,
        "commands": cmds,
        "files": [f"configs/docker-stack/stacks/{stack}/compose.yaml", f"configs/docker-stack/stacks/{stack}/.env.example"],
    }

CM = "Prerequisite: DSM **Container Manager** installed (Package Center → Container Manager → Install). Install now if missing."

O = {}

# === net-14, glue-01 (hand-tuned) ===
O["net-14"] = {
    "steps": [
        MAC_OPEN,
        P("net-13"),
        "MacBook: `ssh-keygen -t ed25519 -C homelab-maint -f ~/.ssh/id_ed25519_homelab`",
        "Per host: DSM → Control Panel → Terminal & SNMP → Enable SSH; Ubuntu: `sudo systemctl enable --now ssh`",
        "`ssh-copy-id -i ~/.ssh/id_ed25519_homelab.pub user@192.168.10.10` (nas) and `.11` (mini); rig after WoL (game-08)",
        f"`cp {REPO}/configs/network/ssh-config.example ~/.ssh/config` — set tailnet names/users; `chmod 600 ~/.ssh/config`",
        "Test: `ssh nas hostname`, `ssh mini hostname`, `ssh rig hostname`",
        "Document break-glass path in configs/network/ssh-maintenance-access.md",
    ],
    "commands": [
        "ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_homelab -C homelab-maint",
        f"cp {REPO}/configs/network/ssh-config.example ~/.ssh/config",
        "chmod 600 ~/.ssh/config",
        "ssh nas 'hostname'",
        "ssh mini 'hostname'",
    ],
    "files": ["configs/network/ssh-config.example", "configs/network/ssh-maintenance-access.md"],
    "docs": D(("SSH config", "https://man.openbsd.org/ssh_config"), ("Synology SSH", "https://kb.synology.com/en-us/DSM/help/DSM/AdminCenter/system_terminal_snmp")),
    "verify": "MacBook `ssh nas` and `ssh mini` work without password; ~/.ssh/config IdentityFile matches id_ed25519_homelab.",
}

O["glue-01"] = {
    "steps": [
        MAC_OPEN,
        P("net-08", "net-14"),
        "MacBook → DSM https://nas.<tailnet>:5001 → Control Panel → Hardware & Power → UPS",
        "Enable USB UPS; shutdown after N minutes on battery",
        "Enable Network UPS server; permit device IP **192.168.10.11** (mini)",
        f"`scp {REPO}/scripts/setup/nut-client-ubuntu.sh mini:/tmp/`",
        "`ssh mini 'sudo NAS_IP=192.168.10.10 bash /tmp/nut-client-ubuntu.sh'` — installs nut-client if missing",
        "`ssh mini 'upsc ups@192.168.10.10'` shows battery status",
        "`ssh mini 'systemctl is-active nut-monitor.service || systemctl is-active nut-client.service'`",
    ],
    "commands": [
        f"scp {REPO}/scripts/setup/nut-client-ubuntu.sh mini:/tmp/",
        "ssh mini 'sudo NAS_IP=192.168.10.10 bash /tmp/nut-client-ubuntu.sh'",
        "ssh mini 'upsc ups@192.168.10.10'",
    ],
    "files": ["scripts/setup/nut-client-ubuntu.sh"],
    "verify": "mini reads UPS from NAS; Dream Wall on UPS battery.",
}

# === NAS storage ===
O["nas-00a"] = {
    "steps": [
        P("net-08"),
        "MacBook: `ssh nas` → record used space: `df -h /volume1 /volume2 /volume3`",
        "Open Storage Manager in DSM; confirm **three separate Basic pools** (~14.6 / 10.9 / 16.4 TB usable) — not SHR, not merged.",
        "Map where TV, movies, music, books, and Tier 1 data live **today** on each volume (not just vol1) — see nas-storage-schema.md §5 runbook.",
        "Confirm Tailscale on NAS (net-08) before any bulk data moves.",
        "Optional: `ssh nas 'sudo btrfs filesystem usage /volume1 /volume2 /volume3'` for detailed audit",
    ],
    "commands": [
        "ssh nas 'df -h /volume1 /volume2 /volume3'",
        "ssh nas 'cat /proc/mdstat'",
    ],
    "files": ["../nas-storage-schema.md"],
    "verify": "Written path map shows target placement: TV→vol3/tv, movies→vol2/movies, music/books/Tier1→vol1; notes which libraries need moving vs already correct.",
}

O["nas-00b"] = {
    "steps": [
        P("nas-00a"),
        "**Only if vol2/vol3 are unorganized:** MacBook → DSM → Control Panel → Shared Folder → delete media shares on vol2/vol3.",
        "**Only if needed:** Storage Manager → wipe vol2/vol3 data; recreate empty Basic Btrfs volumes on bays 2 and 3. Do **not** convert to SHR or merge pools.",
        "If vol2/vol3 already hold movies/TV in the right place, **skip wipe** — go straight to nas-00c.",
        "Do NOT touch vol1 — docker, Tier 1, and any rsync sources stay until nas-00c/nas-00e.",
        "Storage Manager → confirm three **independent** Basic pools remain (~14.6 / 10.9 / 16.4 TB usable).",
    ],
    "commands": ["ssh nas 'ls -la /volume2 /volume3'"],
    "files": ["../nas-storage-schema.md"],
    "verify": "Three separate Basic pools healthy; vol2 ready for movies, vol3 ready for TV (empty or already correct). Vol1 untouched.",
}

O["nas-00c"] = {
    "title": "Create DSM shares on each Basic volume (+ Btrfs settings)",
    "estimate": "45 min–8 hrs (depends on rsync)",
    "steps": [
        MAC_OPEN,
        P("nas-00b"),
        "Safety: net-08 complete (Tailscale on NAS) before bulk data moves. Hyper Backup (nas-02) comes after shares exist.",
        "You have **three independent Basic volumes** — each DSM share lives on **one volume only** (vol3=TV, vol2=movies, vol1=music/books/Tier1/docker). No merged pool, no cross-volume shares.",
        "**Volume 3:** DSM → Control Panel → Shared Folder → Create **`tv`** on **Volume 3**.",
        "**Volume 2:** Create **`movies`** on **Volume 2**.",
        "**Volume 1:** Create shares: `music`, `books`, `youtube`, `games`, `manual`, `photo`, `docs`, `appdata`, `backups`, `vault`, `home`, `staging`, `frigate`, `cache` — all on **Volume 1**.",
        "**Volume 1 infrastructure (directories, NOT Shared Folders):** `ssh nas 'sudo mkdir -p /volume1/docker /volume1/mounts/seedbox-files /volume1/scripts/media'`",
        "Storage Manager → each volume: Btrfs checksums ON; compression ON for docs/appdata/vault on vol1; OFF for media shares; atime OFF.",
        "**Move data only where nas-00a path map shows wrong placement** (skip libraries already on the correct volume): TV→`/volume3/tv/`, movies→`/volume2/movies/`; on vol1 organize music/books/Tier1 into their shares if still flat.",
        "Verify any rsync: `ssh nas 'du -sb <src> <dest>'` byte counts match; dry-run `rsync -avhn --delete` shows zero pending.",
        "Do **not** delete old duplicate paths until nas-00d exports work and **nas-00e** confirms Ubuntu Plex/*arr see the new paths.",
    ],
    "commands": [
        "ssh nas 'sudo mkdir -p /volume1/docker /volume1/mounts/seedbox-files /volume1/scripts/media'",
        "ssh nas 'rsync -avh --info=progress2 /volume1/<old-tv>/ /volume3/tv/'",
        "ssh nas 'rsync -avh --info=progress2 /volume1/<old-movies>/ /volume2/movies/'",
        "ssh nas 'du -sb /volume3/tv /volume2/movies'",
        "ssh nas 'rsync -avhn --delete /volume1/<old-tv>/ /volume3/tv/'",
    ],
    "files": ["../nas-storage-schema.md"],
    "verify": "Each volume holds only its role: vol3/tv, vol2/movies, vol1/music+books+Tier1+docker infra. Byte counts match after any rsync.",
}

O["nas-00d"] = {
    "steps": [
        P("nas-00c", "net-01"),
        "DSM → Control Panel → Group: create household, media, docker-service groups",
        "DSM → Control Panel → Shared Folder → Edit each share: NFS/SMB permissions per schema",
        "Control Panel → File Services → SMB: min SMB2, max SMB3; enable Bonjour",
        "Control Panel → File Services → NFS: export tv,movies,music to Trusted 192.168.10.0/24 only, squash",
        "MacBook test mount: `mkdir -p ~/mnt/test && mount -t nfs nas:/volume3/tv ~/mnt/test` (from LAN or Tailscale subnet route)",
    ],
    "commands": [
        "showmount -e nas.<tailnet>.ts.net",
        "ssh nas 'synoshare --enum ALL'",
    ],
    "files": ["../nas-storage-schema.md", "configs/network/vlan-zone-firewall-plan.md"],
    "verify": "Trusted client mounts NFS exports; SMB works for household.",
}

O["nas-00e"] = {
    "steps": [
        MAC_OPEN,
        P("nas-00d"),
        "**Interim** while Plex/*arr still on Ubuntu (before nas-10/nas-21 migrate them to NAS).",
        "`ssh mini 'sudo apt install -y nfs-common'` if mount fails",
        "`ssh mini 'sudo mkdir -p /mnt/nas/{tv,movies,music,books}'` — add NFS fstab lines to 192.168.10.10 exports",
        "`ssh mini 'sudo mount -a && ls /mnt/nas/tv | head'`",
        "Re-point Plex (Ubuntu) libraries and Sonarr/Radarr/Lidarr root folders to /mnt/nas/*",
        "Play test in Plex; spot-check *arr import — only then delete vol1 duplicates",
        "After nas-10 + nas-21 land on NAS, retire Ubuntu stacks (seed-08)",
    ],
    "commands": [
        "ssh mini 'grep /mnt/nas /etc/fstab'",
        "ssh mini 'sudo mount -a && ls /mnt/nas/tv | head'",
    ],
    "files": ["../nas-storage-schema.md"],
    "verify": "Ubuntu apps use NAS paths; duplicates removed safely.",
}

O["nas-01"] = {
    "steps": [
        P("nas-00c"),
        "DSM Package Center → install **Snapshot Replication**",
        "Snapshot Replication → Snapshots → select Tier1 shares on vol1",
        "Hourly snapshots Tier1; daily on tv/movies/music/books",
        "Retention → GFS + Immutable 7–14 days on Tier1",
        "`ssh nas 'synosharesnap --help'` if CLI preferred",
    ],
    "commands": ["ssh nas 'synosharesnap --help'"],
    "files": ["configs/nas/backup-architecture.md"],
    "verify": "Snapshots visible in DSM; test restore one file.",
}

O["nas-02"] = {
    "steps": [
        MAC_OPEN,
        P("nas-01"),
        "Backblaze: create private bucket + application key with Object Lock",
        "DSM Package Center → **Hyper Backup** → + → Cloud → S3 Compatible → Backblaze B2",
        "Select Tier1 shares (photo,docs,appdata,backups,vault,home) — add Immich dump folder **after nas-08**",
        "Enable client-side encryption; store .pem in password manager + paper",
        "Schedule daily 03:00; run first backup now",
        "Store B2 application key in Bitwarden; scope to single bucket only",
    ],
    "commands": [],
    "files": ["configs/nas/backup-architecture.md"],
    "verify": "Hyper Backup task succeeds; encrypted .pem stored offline.",
}

O["nas-03"] = {
    "steps": [
        MAC_OPEN,
        P("nas-01"),
        "Attach USB HDD to NAS",
        "Hyper Backup or USB Copy → Tier2 paths: **/volume3/tv**, **/volume2/movies**, **/volume1/music**, **/volume1/books**",
        "Schedule weekly; label two drives for rotation",
        "Run first backup now; test restore one file from USB",
        "Log rotation date in configs/nas/backup-architecture.md",
    ],
    "commands": [],
    "files": ["configs/nas/backup-architecture.md"],
    "verify": "Weekly job completes; offsite drive rotation logged.",
}

O["nas-04"] = {
    "steps": [
        MAC_OPEN,
        P("nas-02"),
        "Backblaze: create **separate** bucket + application key for Linux hosts (not the NAS Hyper Backup bucket)",
        f"`scp {REPO}/scripts/backup/restic-backup.sh {REPO}/scripts/backup/restic-backup.env.example {REPO}/scripts/backup/restic-backup.service {REPO}/scripts/backup/restic-backup.timer mini:/tmp/`",
        "`ssh mini 'sudo apt install -y restic && sudo install -d -m 0700 /etc/restic /opt/scripts'`",
        "`ssh mini 'sudo install -m 755 /tmp/restic-backup.sh /opt/scripts/ && sudo install -m 600 /tmp/restic-backup.env.example /etc/restic/b2.env'`",
        "Edit /etc/restic/b2.env on mini (RESTIC_REPOSITORY, B2 keys); `openssl rand -base64 48` → /etc/restic/password",
        "`ssh mini 'sudo cp /tmp/restic-backup.service /tmp/restic-backup.timer /etc/systemd/system/'`",
        "`ssh mini 'sudo systemctl daemon-reload && sudo systemctl enable --now restic-backup.timer'`",
        "`ssh mini 'sudo ENV_FILE=/etc/restic/b2.env /opt/scripts/restic-backup.sh'`",
    ],
    "commands": [
        f"scp {REPO}/scripts/backup/restic-backup.sh mini:/tmp/",
        "ssh mini 'sudo apt install -y restic'",
        "ssh mini 'sudo systemctl enable --now restic-backup.timer'",
    ],
    "files": ["scripts/backup/restic-backup.sh", "scripts/backup/restic-backup.env.example", "scripts/backup/restic-backup.timer"],
    "verify": "restic snapshots lists on mini; timer active.",
}

O["nas-05"] = {
    "steps": [
        P("nas-04"),
        "`ssh rig 'sudo pacman -S --needed restic'`",
        "Copy restic script; create /etc/restic/b2.env with RESTIC_REPOSITORY=b2:bucket:rig",
        "Exclude caches/Steam from BACKUP_PATHS",
        "Enable timer (Persistent=true for on-demand rig)",
    ],
    "commands": [
        f"scp {REPO}/scripts/backup/restic-backup.sh rig:/tmp/",
        "ssh rig 'sudo pacman -S --needed restic'",
        "ssh rig 'sudo systemctl enable --now restic-backup.timer'",
    ],
    "files": ["scripts/backup/restic-backup.sh"],
    "verify": "rig restic repo initialized; timer enabled.",
}

O["nas-06"] = {
    "steps": [
        P("nas-04"),
        "Order Hetzner Storage Box; enable SSH (port 23)",
        "`ssh mini 'ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_borg -C borgmatic'`",
        "Install borgmatic; copy borgmatic-config.yaml to /etc/borgmatic/",
        "Init append-only repo; first backup; timer 03:10",
    ],
    "commands": [
        f"scp {REPO}/scripts/backup/borgmatic-config.yaml mini:/tmp/",
        "ssh mini 'sudo apt install -y borgbackup borgmatic'",
        "ssh mini 'borgmatic create --stats'",
    ],
    "files": ["scripts/backup/borgmatic-config.yaml", "scripts/backup/borgmatic.timer"],
    "verify": "borgmatic list shows archive; timer active. (Append-only is via B2 Object Lock on restic — not borg client append-only.)",
}

O["nas-07"] = {
    "steps": [
        P("nas-02", "nas-04", "nas-06"),
        "Confirm all encryption keys in Bitwarden + paper",
        f"MacBook: `ENV_FILE=/etc/restic/b2.env ssh mini '{REPO}/scripts/backup/restore-test.sh restic'`",
        "borgmatic restore test on mini",
        "DSM Hyper Backup: restore sample from B2",
        "Log restore date in backup-architecture.md",
    ],
    "commands": [
        f"ssh mini 'ENV_FILE=/etc/restic/b2.env /opt/scripts/restore-test.sh restic'",
        f"ssh mini '/opt/scripts/restore-test.sh borgmatic /etc/borgmatic/config.yaml'",
    ],
    "files": ["scripts/backup/restore-test.sh", "configs/nas/backup-architecture.md"],
    "verify": "All three backup paths restore a test file.",
}

# glue cachyos
O["glue-02"] = {
    "steps": [
        f"`scp {REPO}/scripts/setup/cachyos-desktop-baseline.sh rig:/tmp/`",
        "`ssh rig 'bash /tmp/cachyos-desktop-baseline.sh'` — browsers + LibreOffice",
        "Set default browser; pin favorites",
        "Reboot optional; verify desktop apps launch",
    ],
    "commands": [f"scp {REPO}/scripts/setup/cachyos-desktop-baseline.sh rig:/tmp/", "ssh rig 'bash /tmp/cachyos-desktop-baseline.sh'"],
    "files": ["scripts/setup/cachyos-desktop-baseline.sh"],
    "verify": "Firefox/Chromium and LibreOffice open on rig.",
}

O["glue-03"] = {
    "steps": [
        P("glue-02"),
        "On rig: set Kagi as default search in browser settings",
        "Install Kagi browser extension if desired",
        "Document choice in dotfiles if tracked",
    ],
    "commands": ["ssh rig 'xdg-settings get default-web-browser'"],
    "files": [],
    "verify": "Address bar searches use Kagi.",
}

O["glue-04"] = {
    "steps": [
        MAC_OPEN,
        "MacBook: `brew install chezmoi` (or `{REPO}/scripts/dotfiles/bootstrap-dotfiles.sh` with `CHEZMOI_NO_APPLY=1`).".format(REPO=REPO),
        "`chezmoi init` — import live configs: `chezmoi add ~/.config/fish ~/.config/nvim ~/.config/alacritty ~/.gitconfig` (adjust paths).",
        f"Add homelab SSH config: `cp {REPO}/configs/network/ssh-config.example ~/.ssh/config`, edit tailnet/users, `chezmoi add --encrypt ~/.ssh/config` (age key in Proton Pass).",
        "`chezmoi apply` → `chezmoi cd` → commit and push to GitHub (`git branch -M main` if branch is still `master`).",
        "MacBook verify: `chezmoi diff` empty; `chezmoi managed` lists fish/nvim/alacritty/ssh/gitconfig.",
        "Continue to **glue-04b** to bootstrap the CachyOS rig and Mac mini.",
    ],
    "commands": [
        "brew install chezmoi",
        "chezmoi init",
        "chezmoi add ~/.config/fish ~/.config/nvim ~/.config/alacritty ~/.gitconfig",
        f"cp {REPO}/configs/network/ssh-config.example ~/.ssh/config",
        "chezmoi apply",
        "chezmoi cd && git branch -M main && git push -u origin main",
        "chezmoi diff",
        "chezmoi status",
    ],
    "files": [
        "scripts/dotfiles/bootstrap-dotfiles.sh",
        "scripts/dotfiles/chezmoi-quickstart.md",
        "configs/network/ssh-config.example",
    ],
    "docs": D(("chezmoi", "https://www.chezmoi.io/"), ("chezmoi quick start", "https://www.chezmoi.io/quick-start/")),
    "verify": "GitHub `btabaska/dotfiles` has chezmoi source layout; MacBook `chezmoi diff` is empty.",
}

O["glue-04b"] = {
    "steps": [
        MAC_OPEN,
        P("glue-04"),
        "**Before bootstrapping other hosts:** confirm the age private key (`~/.config/chezmoi/key.txt`) is backed up in Proton Pass — encrypted SSH config won't decrypt without it.",
        f"**CachyOS rig** (fish/nvim/alacritty + ssh): `scp {REPO}/scripts/dotfiles/bootstrap-dotfiles.sh rig:/tmp/` then `ssh rig 'DOTFILES_REPO=btabaska bash /tmp/bootstrap-dotfiles.sh'`.",
        f"**Mac mini** (ssh + gitconfig; lighter set): `scp {REPO}/scripts/dotfiles/bootstrap-dotfiles.sh mini:/tmp/` then `ssh mini 'DOTFILES_REPO=btabaska bash /tmp/bootstrap-dotfiles.sh'`.",
        "On each host after bootstrap: copy age key from Proton Pass to `~/.config/chezmoi/key.txt` if SSH config is encrypted, then `chezmoi apply`.",
        "Verify fleet-wide from MacBook: `ssh rig 'chezmoi diff && chezmoi status'` and `ssh mini 'chezmoi diff && chezmoi status'` — both diffs must be empty.",
        "Test SSH aliases: `ssh mini hostname`, `ssh rig hostname` (wake rig first via game-08 if needed).",
        "**Ongoing sync:** edit on one box → `chezmoi edit` → `chezmoi apply` → `chezmoi cd && git push`; on others → `chezmoi update`. Use `.tmpl` files for per-host differences (see chezmoi-quickstart.md).",
        "glue-08 ansible-pull will automate `chezmoi init --apply` later; manual bootstrap is fine until Forgejo (glue-05) is up.",
    ],
    "commands": [
        f"scp {REPO}/scripts/dotfiles/bootstrap-dotfiles.sh rig:/tmp/",
        "ssh rig 'DOTFILES_REPO=btabaska bash /tmp/bootstrap-dotfiles.sh'",
        f"scp {REPO}/scripts/dotfiles/bootstrap-dotfiles.sh mini:/tmp/",
        "ssh mini 'DOTFILES_REPO=btabaska bash /tmp/bootstrap-dotfiles.sh'",
        "ssh rig 'chezmoi diff && chezmoi status'",
        "ssh mini 'chezmoi diff && chezmoi status'",
        "ssh mini 'hostname'",
        "ssh rig 'hostname'",
    ],
    "files": [
        "scripts/dotfiles/bootstrap-dotfiles.sh",
        "scripts/dotfiles/chezmoi-quickstart.md",
        "configs/network/ssh-config.example",
        "configs/network/ssh-maintenance-access.md",
    ],
    "docs": D(("chezmoi", "https://www.chezmoi.io/"), ("chezmoi templating", "https://www.chezmoi.io/user-guide/templating/")),
    "verify": "`chezmoi diff` empty on rig and mini; `ssh mini` / `ssh rig` work from MacBook.",
}

# docker foundation
O["docker-01"] = {
    "steps": [
        MAC_OPEN,
        f"`scp {REPO}/scripts/setup/install-docker-ubuntu.sh mini:/tmp/`",
        "`ssh mini 'sudo bash /tmp/install-docker-ubuntu.sh'`",
        "`ssh mini 'sudo usermod -aG docker $USER'` — re-login or `newgrp docker`",
        "`ssh mini 'docker run --rm hello-world'`",
        "**Before docker-07 (AdGuard :53):** disable systemd-resolved stub per script output:",
        "`ssh mini 'sudo sed -i \"s/^#\\?DNSStubListener=.*/DNSStubListener=no/\" /etc/systemd/resolved.conf'`",
        "`ssh mini 'sudo ln -sf /run/systemd/resolve/resolv.conf /etc/resolv.conf && sudo systemctl restart systemd-resolved'`",
    ],
    "commands": [
        f"scp {REPO}/scripts/setup/install-docker-ubuntu.sh mini:/tmp/",
        "ssh mini 'sudo bash /tmp/install-docker-ubuntu.sh'",
        "ssh mini 'docker compose version'",
        "ssh mini 'docker run --rm hello-world'",
    ],
    "files": ["scripts/setup/install-docker-ubuntu.sh"],
    "docs": D(("Docker Ubuntu", "https://docs.docker.com/engine/install/ubuntu/"),),
    "verify": "docker and docker compose work on mini without sudo.",
}

O["docker-02"] = {
    "steps": [
        P("docker-01"),
        "`ssh mini 'sudo docker network create edge || true'`",
        f"`scp -r {REPO}/configs/docker-stack/stacks mini:/tmp/stacks`",
        "`ssh mini 'sudo mkdir -p /opt/stacks && sudo rsync -a /tmp/stacks/ /opt/stacks/'`",
        "`ssh mini 'for d in /opt/stacks/*/; do cp -n \"$d/.env.example\" \"$d/.env\" 2>/dev/null; done'`",
        "Read configs/docker-stack/README.md for port map",
    ],
    "commands": [
        "ssh mini 'docker network create edge || true'",
        f"scp -r {REPO}/configs/docker-stack/stacks mini:/tmp/stacks",
        "ssh mini 'sudo rsync -a /tmp/stacks/ /opt/stacks/'",
    ],
    "files": ["configs/docker-stack/README.md"],
    "verify": "docker network ls shows edge; /opt/stacks populated.",
}

# docker stacks via template
for did, stack, port, env in [
    ("docker-03", "seerr", 5055, "TZ; init: true mandatory; mount old Jellyseerr config if migrating"),
    ("docker-04", "miniflux", 8082, "ADMIN_USERNAME/PASSWORD before first up"),
    ("docker-05", "navidrome", 4533, "ND_MUSICFOLDER=/mnt/nas/music after nas-00e NFS mount"),
    ("docker-07", "adguard", 3000, "complete wizard; upstream=unbound:5335 after dns-01"),
    ("docker-08", "dockge", 5001, "DOCKGE_STACKS_DIR=/opt/stacks"),
    ("docker-09", "ntfy", 8080, "NTFY_BASE_URL=http://macmini.<tailnet>:8080 — host port 8080 not 80"),
    ("docker-10", "beszel", 8090, "hub first; paste agent TOKEN/KEY into .env then recreate agent"),
    ("docker-11", "uptime-kuma", 3001, "create admin on first visit"),
    ("doc-02", "mealie", 9000, "BASE_URL + secret"),
    ("read-14", "pinchflat", 8945, "mount NAS /volume1/youtube on mini first — see step below"),
    ("media-01", "tautulli", 8181, "wizard: Plex http://192.168.10.10:32400 + token"),
    ("media-03", "maintainerr", 6246, "NAS Plex + *arr at 192.168.10.10; dry-run rules first"),
]:
    o = ustack(stack, port, env)
    if did == "read-14":
        o["steps"].insert(3, "`ssh mini 'sudo mkdir -p /mnt/nas/youtube && sudo mount -t nfs 192.168.10.10:/volume1/youtube /mnt/nas/youtube'` — add to fstab; set PINCHFLAT_DOWNLOADS in .env")
    O[did] = o

O["docker-12"] = ustack("diun", 0, "DIUN_NTFY_* webhook to ntfy topic", no_curl=True)
O["docker-12"]["steps"].extend([
    "Deploy **after** docker-09 (ntfy) and other stacks — Diun watches running containers only",
    "Verify: `ssh mini 'docker inspect diun --format \"{{.State.Health.Status}}\"'` — no web UI",
])
O["docker-12"]["commands"].append("ssh mini 'docker inspect diun --format \"{{.State.Health.Status}}\"'")
O["docker-12"]["verify"] = "Diun healthy; test image-update notification arrives in ntfy app."

O["media-02"] = ustack("kometa", 0, "copy config.yml.example; fill Plex URL + TMDb", no_curl=True)
O["media-02"]["steps"].extend([
    "`ssh mini 'cd /opt/stacks/kometa && cp -n config/config.yml.example config/config.yml'`",
    "`ssh mini 'cd /opt/stacks/kometa && docker compose run --rm kometa --run'` — batch job, no HTTP port",
    "`ssh mini 'docker logs kometa --tail 50'`",
])
O["media-02"]["commands"].append("ssh mini 'cd /opt/stacks/kometa && docker compose run --rm kometa --run'")
O["media-02"]["verify"] = "Kometa one-shot run exits 0; collections/overlays appear in Plex."

# === HA tasks ===
HA = "http://homeassistant.<tailnet>:8123"
for hid, steps, cmds, files, verify in [
    ("ha-01", [
        "Decision: HA Green purchased — unbox and connect Ethernet to Trusted LAN",
        "MacBook: reserve static IP or DHCP reservation 192.168.10.x in UniFi",
        "Note MAC for inventory",
    ], [], [], "HA Green on network."),
    ("ha-02", [
        P("ha-01"),
        "Browse to http://homeassistant.local:8123 or IP from router",
        "Create owner account; complete onboarding",
        "Settings → System → Updates: enable automatic backups later (ha-11)",
        "Install Advanced SSH & Web Terminal add-on for break-glass (net-14)",
    ], ["ping homeassistant.local"], [], "HA UI loads; owner account works."),
]:
    O[hid] = {"steps": steps, "commands": cmds, "files": files, "verify": verify}

O["ha-03"] = {
    "steps": [
        P("ha-01"),
        f"Alternative to Green: on rig `scp {REPO}/scripts/setup/install-haos-vm.sh rig:/tmp/`",
        "`ssh rig 'sudo bash /tmp/install-haos-vm.sh'` — KVM VM",
        "Bridge VM NIC to Trusted LAN; browse VM IP:8123",
    ],
    "commands": [f"scp {REPO}/scripts/setup/install-haos-vm.sh rig:/tmp/", "ssh rig 'sudo bash /tmp/install-haos-vm.sh'"],
    "files": ["scripts/setup/install-haos-vm.sh"],
    "verify": "HAOS VM reachable at :8123.",
}

O["ha-04"] = {"steps": [P("ha-02"), "HACS: https://hacs.xyz/docs/setup/download — run install script via SSH add-on or UI", "Restart HA; HACS appears in sidebar", "Install HACS integrations as needed"], "commands": [], "files": [], "verify": "HACS sidebar present."}
O["ha-05"] = {"steps": [P("ha-02"), "Settings → Devices → Add Integration → Philips Hue", "Press Hue bridge button when prompted", "Assign Hue entities to areas", "Move Hue bridge to IoT VLAN per net-02"], "commands": [], "files": [], "verify": "Hue lights controllable locally."}
O["ha-06"] = {"steps": [P("ha-02"), "Google Cloud: enable Smart Device Management API; create OAuth client", "HA: Add Google Nest integration; complete OAuth", "Store refresh token backup in Bitwarden"], "commands": [], "files": [], "verify": "Nest climate visible in HA."}
O["ha-07"] = {"steps": [P("ha-04"), "HACS → midea_ac_lan or official integration", "Add each Midea device by IP on IoT VLAN", "BACK UP integration config to NAS", "Test local control without cloud"], "commands": [], "files": ["configs/homeassistant/midea-local-setup.md"], "verify": "Midea AC responds from HA."}
O["ha-08"] = {"steps": [P("ha-07"), "Flash ESPHome on SLWF-01Pro per configs/homeassistant/esphome-midea-slwf01.yaml", "Add ESPHome integration; adopt device on IoT", "Disable cloud Midea dongle after cutover"], "commands": [], "files": ["configs/homeassistant/esphome-midea-slwf01.yaml"], "verify": "AC controlled via ESPHome only."}
O["ha-09"] = {"steps": [P("ha-02"), "Install Whisper + Piper add-ons for Assist", "Settings → Voice assistants → pipeline", "Point conversation agent to LiteLLM (ha-17) for complex queries", "Test wake word on phone Companion app"], "commands": [], "files": [], "verify": "Voice command triggers automation."}
O["ha-10"] = {"steps": [P("ha-05", "ha-07"), "Settings → Dashboards → Energy", "Add grid, solar if any, device monitors from Hue/Nest/Midea"], "commands": [], "files": [], "verify": "Energy dashboard shows live usage."}
O["ha-11"] = {"steps": [
    P("ha-02"),
    "Install Samba Backup or HA backup to NAS share backups/ha/",
    "Schedule nightly 04:00",
    "Copy encryption key to Bitwarden + paper — loss = unrecoverable backups",
    "Test restore on spare VM or second instance",
], "commands": [], "files": ["configs/homeassistant/backup-checklist.md"], "verify": "Backup file lands on NAS nightly."}
O["ha-12"] = {"steps": [P("ha-04"), "Add-on: Mosquitto broker", "Add-on or container: Zigbee2MQTT + USB coordinator on Trusted", "Z2M → MQTT → HA auto-discovery", "Pair first sensor"], "commands": [], "files": [], "verify": "Zigbee sensor updates in HA."}
O["ha-13"] = {"steps": [P("ha-02"), "Install Companion on phones; enable location", "Add mmWave or Bermuda for room presence", "Create person-based automations"], "commands": [], "files": [], "verify": "Arrival automation fires."}
O["ha-14"] = {"steps": [P("ha-02"), "HACS/integration: UniFi Protect", "Enter Protect credentials; adopt cameras", "Assign camera entities to areas"], "commands": [], "files": [], "verify": "Camera streams in HA."}
O["ha-15"] = {
    "steps": [
        MAC_OPEN,
        P("ha-14"),
        "**GATE:** NAS RAM ≥20GB recommended (defer with Immich ML on 4GB).",
        CM,
        f"`scp -r {REPO}/configs/docker-stack/stacks/frigate nas:/tmp/frigate`",
        "`ssh nas 'sudo mkdir -p /volume1/docker/frigate && sudo rsync -a /tmp/frigate/ /volume1/docker/frigate/'`",
        "Copy config/config.yml.example → config.yml; set RTSP URLs + detector (Quick Sync or Coral)",
        "`ssh nas 'cd /volume1/docker/frigate && cp -n .env.example .env && docker compose up -d'`",
        "HA → Frigate integration for person/package events",
    ],
    "commands": [
        f"scp -r {REPO}/configs/docker-stack/stacks/frigate nas:/tmp/frigate",
        "ssh nas 'cd /volume1/docker/frigate && docker compose up -d'",
        "ssh nas 'curl -sfI http://127.0.0.1:8971/ | head -1'",
    ],
    "files": ["configs/docker-stack/stacks/frigate/compose.yaml", "configs/docker-stack/stacks/frigate/config/config.yml.example"],
    "docs": D(("Frigate", "https://docs.frigate.video/"),),
    "verify": "Frigate detects person; HA receives events.",
}
O["ha-16"] = {"steps": [P("ha-05"), "HA → HomeKit Bridge integration", "Pair iPhone Home app via QR", "Expose only needed domains"], "commands": [], "files": [], "verify": "Siri controls Hue via HomeKit."}
O["ha-17"] = {
    **ustack("litellm", 4000, "LITELLM_MASTER_KEY + Ollama upstream"),
}
O["ha-17"]["steps"] = O["ha-17"]["steps"] + [
    "Point HA Assist conversation agent to http://192.168.10.11:4000 (LiteLLM)",
    "On rig: set OLLAMA_KEEP_ALIVE=0 so VRAM frees between requests (game-13)",
]

# === Seed / media pipeline ===
O["seed-01"] = {
    "steps": [
        MAC_OPEN,
        "MacBook browser: sign up bytesized-hosting.com **Stream +3** (3000 GB, €16/mo EU)",
        "Record SFTP user, home /home/hd34/btabaska, IP **185.162.184.38** in Bitwarden",
        "Architecture lock-in: Betty runs **ONLY Deluge** — do NOT install Sonarr/Radarr/Prowlarr/qBittorrent on seedbox",
        "One-click install Deluge only; set ratio/seed-time limits for self-prune under 3 TB",
        "Record Deluge daemon port + password (needed by nas-22)",
    ],
    "commands": [],
    "files": ["configs/seedbox/provider-comparison.md", "configs/seedbox/rclone.conf.example"],
    "docs": D(("Bytesized", "https://bytesized-hosting.com/"), ("Deluge labels", "https://deluge.readthedocs.io/en/latest/modules/label.html")),
    "verify": "AppBox active; Deluge installed; credentials documented; no *arr apps on Betty.",
}
O["betty-01"] = {
    "steps": [
        P("seed-01"),
        "`ssh seedbox` → confirm Deluge WebUI",
        "Note daemon port + password for nas-22",
        "Create labels: sonarr→files/tv, radarr→files/movies, lidarr→files/music, readarr→files/books, manual→files/manual",
        "`mkdir -p ~/files/{tv,movies,music,books,manual}`",
    ],
    "commands": ["ssh seedbox 'mkdir -p ~/files/{tv,movies,music,books,manual} && ls ~/files'"],
    "files": ["configs/nas/media-automation/README.md"],
    "verify": "Deluge sorts completed torrents into label folders.",
}
O["seed-03"] = {
    "steps": [
        P("seed-01"),
        "`ssh seedbox` → install Tailscale static binaries userspace mode",
        "Start tailscaled with custom socket; `tailscale up`",
        f"`scp {REPO}/scripts/media/verify-tailscale-seedbox.sh seedbox:~/`",
        "`PEERS='mac-mini nas' ~/verify-tailscale-seedbox.sh`",
    ],
    "commands": [
        "ssh seedbox 'mkdir -p ~/tailscale && cd ~/tailscale'",
        f"scp {REPO}/scripts/media/verify-tailscale-seedbox.sh seedbox:~/",
        "ssh seedbox 'PEERS=\"mac-mini nas\" ./verify-tailscale-seedbox.sh'",
    ],
    "files": ["scripts/media/verify-tailscale-seedbox.sh"],
    "verify": "Seedbox on tailnet; Deluge WebUI up.",
}
O["nas-20"] = {
    "steps": [
        MAC_OPEN,
        P("betty-01"),
        "Install rclone on NAS (SynoCommunity or static binary) if not present",
        f"`scp {REPO}/configs/seedbox/rclone.conf.example {REPO}/scripts/media/rclone-seedbox-mount.sh {REPO}/scripts/media/rclone-seedbox-watchdog.sh nas:/tmp/`",
        "`ssh nas 'sudo mkdir -p /root/.ssh /volume1/scripts/media /volume1/mounts/seedbox-files'`",
        "`ssh nas 'sudo ssh-keygen -t ed25519 -f /root/.ssh/seedbox_ed25519 -N \"\" -C nas-rclone'`",
        "`ssh nas 'sudo ssh-copy-id -i /root/.ssh/seedbox_ed25519.pub -p 22 btabaska@185.162.184.38'`",
        "`ssh nas 'sudo cp /tmp/rclone.conf.example /root/.config/rclone/rclone.conf && sudo chmod 600 /root/.config/rclone/rclone.conf'`",
        "`ssh nas 'sudo cp /tmp/rclone-seedbox-*.sh /volume1/scripts/media/ && sudo chmod +x /volume1/scripts/media/rclone-seedbox-*.sh'`",
        "`ssh nas 'grep -q user_allow_other /etc/fuse.conf || echo user_allow_other | sudo tee -a /etc/fuse.conf'`",
        "`ssh nas 'sudo /volume1/scripts/media/rclone-seedbox-mount.sh'`",
        "DSM Task Scheduler: boot = mount script; every 5 min = watchdog",
        "`ssh nas 'mountpoint /volume1/mounts/seedbox-files && ls /volume1/mounts/seedbox-files'`",
    ],
    "commands": [
        f"scp {REPO}/configs/seedbox/rclone.conf.example nas:/tmp/",
        f"scp {REPO}/scripts/media/rclone-seedbox-mount.sh {REPO}/scripts/media/rclone-seedbox-watchdog.sh nas:/tmp/",
        "ssh nas 'sudo /volume1/scripts/media/rclone-seedbox-mount.sh'",
        "ssh nas 'mountpoint /volume1/mounts/seedbox-files'",
    ],
    "files": ["configs/seedbox/rclone.conf.example", "scripts/media/rclone-seedbox-mount.sh", "scripts/media/rclone-seedbox-watchdog.sh"],
    "verify": "Mount lists Betty files/ tree; watchdog scheduled.",
}
O["nas-21"] = {
    "steps": [
        P("nas-20"),
        CM,
        "**Migrate configs (before first start):** on Ubuntu `docker compose stop` sonarr radarr lidarr readarr.",
        "Fresh-copy from Ubuntu: `scp -r mini:/home/btabaska/server/configs/sonarr nas:/tmp/` → /volume1/docker/sonarr/ "
        "(repeat radarr, liadarr→lidarr, readarr). See migration-from-ubuntu.md.",
        f"`scp -r {REPO}/configs/nas/media-automation nas:/tmp/` → /volume1/docker/media-automation/",
        "`ssh nas 'cd /volume1/docker/media-automation && cp .env.example .env'` — PUID/PGID from id, paths, RG_DB_PASSWORD",
        "Phase A: `docker compose up -d prowlarr flaresolverr sonarr radarr`",
        "Phase B: lidarr readarr rreading-glasses rreading-glasses-db",
        "Phase C: unpackerr after nas-25 config",
    ],
    "commands": [
        "scp -r mini:/home/btabaska/server/configs/sonarr nas:/tmp/",
        f"scp -r {REPO}/configs/nas/media-automation nas:/tmp/",
        "ssh nas 'cd /volume1/docker/media-automation && cp .env.example .env'",
        "ssh nas 'cd /volume1/docker/media-automation && docker compose up -d prowlarr flaresolverr sonarr radarr'",
    ],
    "files": [
        "configs/nas/media-automation/docker-compose.yml",
        "configs/nas/media-automation/.env.example",
        "configs/nas/media-automation/README.md",
        "configs/nas/media-automation/migration-from-ubuntu.md",
    ],
    "verify": "Core *arr UIs respond on NAS ports; migrated library counts look correct.",
}
O["nas-22"] = {
    "steps": [
        P("nas-21"),
        "**If migrating from Ubuntu:** update root folders (/data/tv/→/tv, /data/movies/→/movies, "
        "/data/music/→/music, /data/books/→/cwa-book-ingest) and Refresh & Scan.",
        "Remove qBittorrent download clients; add remote Deluge @ 185.162.184.38 + label per app.",
        "Remove Jackett Torznab indexers; Prowlarr → Apps Full Sync. Re-add private indexers using old "
        "Jackett Indexers/*.json from migration-snapshot as credential reference.",
        "Remote Path Mapping: /home/hd34/btabaska/files/ → /seedbox/",
        "Prowlarr → FlareSolverr http://flaresolverr:8191; test search",
        "Test import: manual Deluge torrent with label sonarr → Sonarr imports from /seedbox",
    ],
    "commands": [
        "ssh nas 'docker compose -f /volume1/docker/media-automation/docker-compose.yml ps'",
        "ssh nas 'docker logs sonarr --tail 30'",
    ],
    "files": [
        "configs/nas/media-automation/README.md",
        "configs/nas/media-automation/migration-from-ubuntu.md",
    ],
    "verify": "Migrated library counts match expectations; manual grab imports from /seedbox.",
}
O["nas-28"] = {
    "steps": [
        MAC_OPEN,
        P("nas-22", "docker-01", "docker-02"),
        f"`scp -r {REPO}/configs/docker-stack/stacks/recyclarr mini:/tmp/recyclarr`",
        "`ssh mini 'sudo rsync -a /tmp/recyclarr/ /opt/stacks/recyclarr/'`",
        "Edit config/recyclarr.yml: NAS base_url http://192.168.10.10:8989 / :7878 + API keys from each *arr",
        "`ssh mini 'cd /opt/stacks/recyclarr && cp -n .env.example .env && docker compose run --rm recyclarr sync'`",
        "`ssh mini 'cd /opt/stacks/recyclarr && docker compose run --rm recyclarr list templates'`",
        "Schedule weekly: `0 3 * * 0 cd /opt/stacks/recyclarr && docker compose run --rm recyclarr sync`",
    ],
    "commands": [
        f"scp -r {REPO}/configs/docker-stack/stacks/recyclarr mini:/tmp/recyclarr",
        "ssh mini 'sudo rsync -a /tmp/recyclarr/ /opt/stacks/recyclarr/'",
        "ssh mini 'cd /opt/stacks/recyclarr && docker compose run --rm recyclarr sync'",
    ],
    "files": [
        "configs/docker-stack/stacks/recyclarr/compose.yaml",
        "configs/docker-stack/stacks/recyclarr/config/recyclarr.yml",
        "configs/docker-stack/stacks/recyclarr/.env.example",
    ],
    "docs": D(
        ("Recyclarr", "https://recyclarr.dev/guide/getting-started/"),
        ("TRaSH Sonarr naming", "https://trash-guides.info/Sonarr/Sonarr-recommended-naming-scheme/"),
    ),
    "verify": "recyclarr sync exits 0; Sonarr/Radarr show TRaSH quality profiles + plex-tmdb naming.",
}
O["nas-23"] = {
    "steps": [P("nas-22"), "Lidarr: Deluge label lidarr; root /music; FLAC preferred", "Prowlarr music indexer sync", "Rename tracks ON", "Verify Plex Music + iPod path /volume1/music"],
    "commands": ["ssh nas 'curl -s http://127.0.0.1:8686/api/v1/system/status -H \"X-Api-Key: <KEY>\"'"],
    "files": ["configs/nas/media-automation/README.md"],
    "verify": "Album imports to /volume1/music.",
}
O["nas-24"] = {
    "steps": [P("nas-22"), P("nas-09"), "Readarr metadata http://rreading-glasses:8788 via /settings/development", "Root /cwa-book-ingest", "Deluge label readarr"],
    "commands": ["ssh nas 'docker compose -f /volume1/docker/media-automation/docker-compose.yml ps readarr'"],
    "files": ["configs/nas/media-automation/README.md", "configs/nas/calibre-web-automated/docker-compose.yml"],
    "verify": "Book lands in CWA ingest.",
}
O["nas-25"] = {
    "steps": [P("nas-22"), "Fill unpackerr.conf API keys", "`docker compose up -d unpackerr`", "Test RAR extract"],
    "commands": ["ssh nas 'cd /volume1/docker/media-automation && docker compose up -d unpackerr'", "ssh nas 'docker logs unpackerr --tail 30'"],
    "files": ["configs/nas/media-automation/unpackerr/unpackerr.conf"],
    "verify": "RAR release auto-imported.",
}
O["nas-26"] = {
    "steps": [P("nas-20"), "Schedule rclone-manual-copy.sh every 15 min as root", "ONLY manual lane", "Never sync *arr folders"],
    "commands": ["ssh nas 'sudo /volume1/scripts/media/rclone-manual-copy.sh'"],
    "files": ["scripts/media/rclone-manual-copy.sh"],
    "verify": "manual/ file copies to /volume1/manual.",
}
O["nas-27"] = {
    "steps": [P("nas-22", "nas-23", "nas-24", "nas-25", "nas-26"), "Run README self-check docker inspect mounts", "Confirm single scheduled rclone job", "Report violations"],
    "commands": ["ssh nas \"docker inspect sonarr radarr lidarr readarr unpackerr --format '{{.Name}}{{range .Mounts}} {{.Destination}}({{.Propagation}}){{end}}'\""],
    "files": ["configs/nas/media-automation/README.md"],
    "verify": "All self-check items pass.",
}
O["nas-10"] = {
    "steps": [
        P("nas-00d"),
        "**Before install:** stop Ubuntu Plex (`docker compose stop`). Never run old + new Plex with the same MachineIdentifier.",
        "Take a **fresh** copy from Ubuntu Plex appdata (linuxserver `/config` → `Library/Application Support/Plex Media Server/`).",
        "DSM Package Center → Plex Media Server (NOT Container Manager). Copy P0 files before first start: "
        "Preferences.xml, .LocalAdminToken, com.plexapp.plugins.library.db, com.plexapp.plugins.library.blobs.db. "
        "Optional P1/P2: Plug-in Support/Preferences|Data/, Metadata/, Media/. Skip Logs/ and dated *.db-* backups.",
        "http://nas:32400/web — sign in (skip claim wizard if Preferences.xml has valid PlexOnlineToken).",
        "Libraries: movies=/volume2/movies tv=/volume3/tv music=/volume1/music — run Scan Library Files if needed.",
        "Transcoder → hardware acceleration ON (Quick Sync). Verify Home users + resume playback.",
        "Add Plex appdata to Hyper Backup Tier1. See configs/nas/plex/README.md §4 for full vs scan-only fallback.",
    ],
    "commands": [
        "ssh mini 'cd ~/server/compose/plex && docker compose stop'",
        "ssh nas 'ls /volume2/movies /volume3/tv /volume1/music'",
        "curl -s http://192.168.10.10:32400/identity",
    ],
    "files": ["configs/nas/plex/README.md", "configs/nas/backup-architecture.md"],
    "verify": "Plex plays with HW transcode; Home users and watch history preserved (or scan-only fallback documented).",
}
O["seed-05"] = {
    "steps": [
        P("docker-03", "nas-22", "nas-28"),
        "Seerr :5055 → Services → Radarr/Sonarr/Lidarr at 192.168.10.10",
        "Root folders /movies /tv /music; TRaSH profiles",
        "Link Plex NAS server + token",
    ],
    "commands": [
        "curl -s http://192.168.10.10:7878/api/v3/system/status -H 'X-Api-Key: <KEY>'",
        "curl -s http://192.168.10.10:8989/api/v3/system/status -H 'X-Api-Key: <KEY>'",
    ],
    "files": ["configs/docker-stack/stacks/seerr/compose.yaml"],
    "verify": "Seerr test passes; request hits NAS *arr.",
}
O["seed-07"] = {
    "steps": [P("seed-05", "nas-25", "nas-10"), "Request small title in Seerr", "Watch Deluge → NAS import → Plex", "Seerr Available"],
    "commands": ["ssh nas 'ls /volume1/mounts/seedbox-files/movies'", "ssh nas 'docker logs sonarr --tail 20'"],
    "files": ["configs/nas/plex/README.md"],
    "verify": "End-to-end playable in Plex.",
}
O["seed-08"] = {
    "steps": [P("seed-07"), "Backup UniFi", "Remove NAS qbittorrent/gluetun", "Undo dual-LAN routing", "Stop Ubuntu Plex/*arr if still running"],
    "commands": ["ssh nas 'docker rm -f qbittorrent gluetun 2>/dev/null; ip rule show'"],
    "files": ["configs/seedbox/decommission-old-nas-torrent.md"],
    "verify": "No P2P/VPN sockets on NAS.",
}
O["nas-08"] = nas_docker(
    "immich",
    "configs/nas/immich",
    prereqs=("nas-01", "nas-02", "nas-00c"),
    extra_steps=[
        "Browser http://192.168.10.10:2283 → create admin → Settings → Video Transcoding → Quick Sync",
        "DSM Task Scheduler: nightly pg_dump to /volume1/docker/immich/backups; add folder to Hyper Backup after first dump",
    ],
    verify="Immich :2283 loads; test upload succeeds; HW transcode enabled.",
    docs=D(
        ("Immich Docker", "https://docs.immich.app/install/docker-compose"),
        ("Immich HW transcoding", "https://docs.immich.app/features/hardware-transcoding"),
    ),
)
O["nas-08"]["files"] = ["configs/nas/immich/docker-compose.yml", "configs/nas/immich/.env.example"]

O["nas-08b"] = {
    "steps": [
        MAC_OPEN,
        P("nas-08", "net-14"),
        "Immich UI → Account Settings → API Keys → create key",
        "Copy SD card to rig SSD first (see scripts/media/immich-go-import.md)",
        f"`scp {REPO}/scripts/media/immich-go-import.sh {REPO}/scripts/media/immich-go-import.md rig:~/`",
        "`ssh rig 'chmod +x ~/immich-go-import.sh'`",
        "`ssh rig 'DRY_RUN=1 CARD_PATH=/path/to/copy IMMICH_SERVER=http://192.168.10.10:2283 IMMICH_API_KEY=<key> ~/immich-go-import.sh'`",
        "`ssh rig 'CARD_PATH=/path/to/copy IMMICH_SERVER=http://192.168.10.10:2283 IMMICH_API_KEY=<key> ~/immich-go-import.sh'`",
    ],
    "commands": [
        f"scp {REPO}/scripts/media/immich-go-import.sh rig:~/",
        "ssh rig 'IMMICH_SERVER=http://192.168.10.10:2283 IMMICH_API_KEY=<key> CARD_PATH=/path/to/copy ~/immich-go-import.sh'",
    ],
    "files": ["scripts/media/immich-go-import.sh", "scripts/media/immich-go-import.md"],
    "docs": D(("immich-go", "https://github.com/simulot/immich-go"),),
    "verify": "RAW+JPEG from test SD copy appear stacked in Immich library.",
}

O["nas-09"] = nas_docker(
    "calibre-web-automated",
    "configs/nas/calibre-web-automated",
    dest="/volume1/docker/calibre-web-automated",
    prereqs=("nas-02", "nas-00c"),
    extra_steps=[
        "http://192.168.10.10:8083 — LAN/Tailscale only; **disable Kobo sync** until CWA v4.0.7+ (CVE-2026-7713)",
        "Drop test EPUB into ingest folder; confirm appears in /volume1/books",
    ],
    verify="CWA UI loads; ingest works; not exposed publicly.",
    docs=D(("Calibre-Web-Automated", "https://github.com/crocodilestick/Calibre-Web-Automated"),),
)
O["nas-09"]["files"] = ["configs/nas/calibre-web-automated/docker-compose.yml"]

O["doc-01"] = {
    "steps": [
        MAC_OPEN,
        P("nas-01", "nas-02", "nas-00c"),
        "**GATE:** NAS RAM ≥20GB OR defer until RAM upgrade (Paperless + Immich ML cannot share 4GB).",
        CM,
        "`ssh nas 'sudo mkdir -p /volume1/docs/{consume,media,export} /volume1/docker/paperless-ngx'`",
        f"`scp -r {REPO}/configs/docker-stack/stacks/paperless-ngx nas:/tmp/paperless`",
        "Adapt compose on NAS: remove external `edge` network; bind /volume1/docs/* ; set PUID/PGID from `id`",
        "`ssh nas 'sudo rsync -a /tmp/paperless/ /volume1/docker/paperless-ngx/ && cd /volume1/docker/paperless-ngx && cp -n .env.example .env'`",
        "Edit .env: PAPERLESS_SECRET_KEY, PAPERLESS_DBPASS, PAPERLESS_ADMIN_PASSWORD",
        "`ssh nas 'cd /volume1/docker/paperless-ngx && docker compose up -d'`",
        "SMB mount docs share from MacBook; drop test PDF in consume/",
    ],
    "commands": [
        f"scp -r {REPO}/configs/docker-stack/stacks/paperless-ngx nas:/tmp/paperless",
        "ssh nas 'cd /volume1/docker/paperless-ngx && docker compose up -d'",
        "ssh nas 'curl -sfI http://127.0.0.1:8000/ | head -1'",
    ],
    "files": ["configs/docker-stack/stacks/paperless-ngx/compose.yaml", "configs/docker-stack/stacks/paperless-ngx/.env.example"],
    "docs": D(("Paperless-ngx Docker", "https://docs.paperless-ngx.com/setup/#docker"),),
    "verify": "http://nas:8000 shows OCR'd searchable PDF; consume via SMB works.",
}

# === read-* device/cachyos ===
O["read-01"] = {"steps": ["`ssh rig 'sudo pacman -S --needed calibre'`", "Create library ~/CalibreLibrary", "Enable content server optional"], "commands": ["ssh rig 'calibre --version'"], "files": [], "verify": "Calibre opens on rig."}
O["read-02"] = {"steps": [P("read-01"), f"`scp {REPO}/scripts/reading/syncthing-setup-cachyos.sh rig:~/`", "Enable systemd user syncthing", "Pair with NAS/other devices"], "commands": [f"scp {REPO}/scripts/reading/syncthing-setup-cachyos.sh rig:~/"], "files": ["scripts/reading/syncthing-setup-cachyos.sh"], "verify": "Syncthing UI :8384 synced."}
O["read-03"] = {
    "steps": [
        MAC_OPEN,
        P("read-01", "read-02", "nas-09"),
        "CVE note: keep CWA LAN-only; disable Kobo sync until v4.0.7+",
        "Syncthing on rig: share EPUB folder → NAS CWA ingest path",
        "Drop test EPUB into shared folder; refresh CWA library",
        "`ssh nas 'curl -sfI http://127.0.0.1:8083/ | head -1'`",
    ],
    "commands": ["ssh nas 'curl -sfI http://127.0.0.1:8083/ | head -1'"],
    "files": ["configs/nas/calibre-web-automated/docker-compose.yml", "scripts/reading/koreader-cwa-wallabag-wiring.md"],
    "verify": "EPUB in CWA library and OPDS catalog.",
}
O["read-04"] = {"steps": ["Kobo: install KOReader via NickelMenu/CrossPoint", "Enable OPDS plugin"], "commands": [], "files": ["scripts/reading/koreader-cwa-wallabag-wiring.md"], "verify": "KOReader boots on Kobo."}
O["read-05"] = {"steps": [P("read-01", "read-03", "read-04"), "KOReader OPDS → CWA URL on LAN/Tailscale", "Download test book"], "commands": [], "files": ["scripts/reading/koreader-cwa-wallabag-wiring.md"], "verify": "Book opens on Kobo."}
O["read-06"] = {"steps": [P("read-03", "read-04"), "Enable KOSync in KOReader + CWA"], "commands": [], "files": [], "verify": "Progress syncs Kobo↔CWA."}
O["read-07"] = {
    "steps": [
        MAC_OPEN,
        P("docker-02"),
        f"`scp -r {REPO}/configs/docker-stack/wallabag mini:/tmp/wallabag`",
        "`ssh mini 'sudo mkdir -p /opt/stacks/wallabag && sudo rsync -a /tmp/wallabag/ /opt/stacks/wallabag/'`",
        "`ssh mini 'cd /opt/stacks/wallabag && cp -n .env.example .env && docker compose up -d'`",
        "Browser http://macmini.<tailnet>:8200 → create user → save test article",
        "`ssh mini 'curl -sfI http://127.0.0.1:8200/ | head -1'`",
    ],
    "commands": [
        f"scp -r {REPO}/configs/docker-stack/wallabag mini:/tmp/wallabag",
        "ssh mini 'sudo rsync -a /tmp/wallabag/ /opt/stacks/wallabag/'",
        "ssh mini 'cd /opt/stacks/wallabag && docker compose up -d'",
        "ssh mini 'curl -sfI http://127.0.0.1:8200/ | head -1'",
    ],
    "files": ["configs/docker-stack/wallabag/docker-compose.yml", "configs/docker-stack/wallabag/.env.example"],
    "docs": D(("Wallabag", "https://doc.wallabag.org/"),),
    "verify": "Wallabag UI loads; saved article retrievable; /api/info returns 200.",
}
O["read-08"] = {"steps": [P("read-04", "read-07"), "KOReader Wallabag plugin with mini URL"], "commands": [], "files": ["scripts/reading/koreader-cwa-wallabag-wiring.md"], "verify": "Article syncs to Kobo."}
O["read-09"] = {"steps": [P("read-04", "docker-04"), "KOReader news plugin → Miniflux API"], "commands": [], "files": [], "verify": "RSS item readable on Kobo."}
O["read-10"] = {"steps": [f"`scp {REPO}/scripts/media/install-ipod-tools-cachyos.sh rig:~/`", "`ssh rig 'bash ~/install-ipod-tools-cachyos.sh'`"], "commands": [f"scp {REPO}/scripts/media/install-ipod-tools-cachyos.sh rig:~/"], "files": ["scripts/media/install-ipod-tools-cachyos.sh", "scripts/media/ipod-sync-cachyos.md"], "verify": "rhythmbox detects iPod."}
O["read-11"] = {"steps": [P("read-10"), "Mount iPod; Rhythmbox sync /volume1/music master"], "commands": ["ssh rig 'rhythmbox-client --print-playing'"], "files": ["scripts/media/ipod-sync-cachyos.md"], "verify": "Playlist on iPod plays."}
O["read-12"] = {"steps": [P("read-10"), "Install gPodder; subscribe podcasts; sync via libgpod"], "commands": ["ssh rig 'gpodder --version'"], "files": [], "verify": "Podcast episode on iPod."}
O["read-13"] = {
    "steps": [
        MAC_OPEN,
        "On rig: `ssh rig 'sudo pacman -S --needed obsidian'` (or Flatpak)",
        "Create vault e.g. ~/Documents/ObsidianVault on rig",
        "On MacBook: install Obsidian; subscribe to **official Obsidian Sync** (paid, E2E encrypted — not self-hosted)",
        "Settings → Sync → enable E2E encryption; confirm note syncs MacBook ↔ rig",
        "Ensure vault path is in NAS Tier-1 backup scope (nas-02)",
    ],
    "commands": ["ssh rig 'pacman -Q obsidian 2>/dev/null || echo install obsidian'"],
    "docs": D(("Obsidian Sync", "https://help.obsidian.md/Obsidian+Sync/Obsidian+Sync"),),
    "verify": "Vault syncs E2E across MacBook and rig via official Obsidian Sync.",
}

# === Phase 4 docker special ===
O["docker-14"] = {"steps": [P("docker-06", "docker-07", "docker-08"), "Optional Coolify — or stay Dockge+Caddy", "Document chosen path"], "commands": [], "files": ["configs/docker-stack/README.md"], "verify": "New app reachable via Caddy."}
O["dns-01"] = {
    "steps": [
        MAC_OPEN,
        P("docker-07"),
        "`ssh mini 'cd /opt/stacks/unbound && docker compose up -d'`",
        "AdGuard UI → DNS → upstream: `unbound:5335` (container name on edge network, not 127.0.0.1)",
        "`ssh mini 'cd /opt/stacks/adguard && docker compose restart'`",
        "Dream Wall: NAT redirect outbound UDP/TCP 53 to mini; block known DoH endpoints",
        "Optional NAS redundancy: CM on NAS → second AdGuard; DHCP secondary DNS = nas IP",
        "Test from MacBook: `dig @192.168.10.11 cloudflare.com` + DNSSEC; attempt client bypass (should fail)",
    ],
    "commands": [
        "ssh mini 'cd /opt/stacks/unbound && docker compose up -d'",
        "ssh mini 'docker inspect unbound --format \"{{.State.Health.Status}}\"'",
        "ssh mini 'cd /opt/stacks/adguard && docker compose restart'",
    ],
    "files": [
        "configs/docker-stack/stacks/unbound/compose.yaml",
        "configs/docker-stack/stacks/unbound/unbound/unbound.conf",
        "configs/docker-stack/stacks/adguard/compose.yaml",
    ],
    "docs": D(
        ("Unbound", "https://docs.pi-hole.net/guides/dns/unbound/"),
        ("AdGuard upstream", "https://github.com/AdguardTeam/AdGuardHome/wiki/Configuration"),
    ),
    "verify": "DNSSEC validates via mini resolver; bypass blocked; AdGuard shows unbound upstream.",
}
O["docker-06"] = {
    "steps": [
        MAC_OPEN,
        P("docker-02", "docker-03", "docker-04", "docker-05"),
        f"`scp -r {REPO}/configs/docker-stack/stacks/caddy mini:/tmp/caddy`",
        "`ssh mini 'sudo rsync -a /tmp/caddy/ /opt/stacks/caddy/'`",
        "Edit caddy/.env: DOMAIN, ACME_EMAIL, CLOUDFLARE_API_TOKEN, NAS_IP for offloaded services",
        "Edit caddy/caddy/Caddyfile hostnames",
        "`ssh mini 'cd /opt/stacks/caddy && cp -n .env.example .env && docker compose up -d --build'`",
        "UniFi: allow 80/443 to mini only",
    ],
    "commands": [
        f"scp -r {REPO}/configs/docker-stack/stacks/caddy mini:/tmp/caddy",
        "ssh mini 'sudo rsync -a /tmp/caddy/ /opt/stacks/caddy/'",
        "ssh mini 'cd /opt/stacks/caddy && docker compose up -d --build'",
    ],
    "files": [
        "configs/docker-stack/stacks/caddy/compose.yaml",
        "configs/docker-stack/stacks/caddy/caddy/Caddyfile",
        "configs/docker-stack/stacks/caddy/Dockerfile",
    ],
    "verify": "HTTPS vhosts resolve via Tailscale/LAN; caddy_data volume persists certs.",
}
O["docker-15"] = {
    "steps": [
        MAC_OPEN,
        P("docker-06", "docker-10", "docker-11"),
        f"`scp -r {REPO}/configs/docker-stack/stacks/homepage mini:/tmp/homepage`",
        "`ssh mini 'sudo rsync -a /tmp/homepage/ /opt/stacks/homepage/'`",
        "Edit config/services.yaml + widgets.yaml; set HOMEPAGE_ALLOWED_HOSTS in .env",
        "`ssh mini 'cd /opt/stacks/homepage && cp -n .env.example .env && docker compose up -d'`",
        "Add Caddy vhost home.<domain>; include HA Green tile after ha-01",
        "MacBook: http://macmini.<tailnet>:3010",
    ],
    "commands": [
        f"scp -r {REPO}/configs/docker-stack/stacks/homepage mini:/tmp/homepage",
        "ssh mini 'sudo rsync -a /tmp/homepage/ /opt/stacks/homepage/'",
        "ssh mini 'curl -sfI http://127.0.0.1:3010/ | head -1'",
    ],
    "files": [
        "configs/docker-stack/stacks/homepage/compose.yaml",
        "configs/docker-stack/stacks/homepage/config/services.yaml",
    ],
    "verify": "Homepage :3010 shows live widgets for family + operator sections.",
}
O["glue-05"] = {
    "steps": [
        MAC_OPEN,
        P("docker-01", "docker-02"),
        f"`scp -r {REPO}/configs/git mini:/tmp/forgejo`",
        "`ssh mini 'sudo mkdir -p /opt/stacks/forgejo && sudo rsync -a /tmp/forgejo/ /opt/stacks/forgejo/'`",
        "`ssh mini 'cd /opt/stacks/forgejo && cp -n .env.example .env'` — FORGEJO_DB_PASSWORD, domain, UID/GID",
        "`ssh mini 'cd /opt/stacks/forgejo && docker compose up -d'` — uses docker-compose.yml + edge network",
        "Browser :3030 → create admin; disable open registration; create homelab repo",
        "Push foss-setup mirror; set CONTROL_REPO_URL for glue-08 ansible-pull",
    ],
    "commands": [
        f"scp -r {REPO}/configs/git mini:/tmp/forgejo",
        "ssh mini 'sudo rsync -a /tmp/forgejo/ /opt/stacks/forgejo/'",
        "ssh mini 'cd /opt/stacks/forgejo && docker compose up -d'",
        "ssh mini 'curl -sf http://127.0.0.1:3030/api/healthz'",
    ],
    "files": ["configs/git/docker-compose.yml", "configs/git/.env.example", "configs/git/repo-structure.md"],
    "docs": D(("Forgejo Docker", "https://forgejo.org/docs/latest/admin/installation/docker/"),),
    "verify": "Git push to Forgejo succeeds; healthz returns ok.",
}
O["glue-08"] = {
    "steps": [
        MAC_OPEN,
        P("glue-07", "glue-06"),
        "Each host hostname must match inventory (macmini, cachyos, seedbox)",
        f"`scp {REPO}/configs/ansible/ansible-pull.service {REPO}/configs/ansible/ansible-pull.timer mini:/tmp/`",
        "Edit CONTROL_REPO_URL in ansible-pull.service to Forgejo SSH URL before copying",
        "`ssh mini 'sudo cp /tmp/ansible-pull.service /tmp/ansible-pull.timer /etc/systemd/system/'`",
        "`ssh mini 'sudo systemctl daemon-reload && sudo systemctl enable --now ansible-pull.timer'`",
        "Repeat on rig (OnBootSec=3min timer for wake-gated rig); verify `systemctl list-timers ansible-pull.timer`",
    ],
    "commands": [
        f"scp {REPO}/configs/ansible/ansible-pull.service {REPO}/configs/ansible/ansible-pull.timer mini:/tmp/",
        "ssh mini 'sudo systemctl enable --now ansible-pull.timer'",
        "ssh mini 'systemctl list-timers ansible-pull.timer'",
    ],
    "files": ["configs/ansible/ansible-pull.service", "configs/ansible/ansible-pull.timer", "configs/ansible/README.md"],
    "docs": D(("ansible-pull", "https://docs.ansible.com/ansible/latest/cli/ansible-pull.html"),),
    "verify": "ansible-pull.timer active on mini and rig; first run reports drift (check mode).",
}
O["docker-13"] = {
    "steps": [
        MAC_OPEN,
        P("docker-06", "docker-07", "docker-08", "docker-10", "docker-11", "docker-12", "glue-05"),
        "`ssh mini 'cd /opt/stacks && git init || true'` — remote = Forgejo URL from glue-05",
        "Commit compose + Caddyfile; **never** commit `.env` or `data/` dirs",
        "Document rebuild order in configs/git/repo-structure.md; push to Forgejo",
        "MacBook: clone from Forgejo and dry-run rebuild checklist",
    ],
    "commands": [
        "ssh mini 'cd /opt/stacks && git status'",
        "ssh mini 'cd /opt/stacks && git remote -v'",
    ],
    "files": ["configs/git/repo-structure.md"],
    "verify": "Forgejo shows all stack folders; no secrets in git history.",
}
O["glue-06"] = {
    "steps": [
        MAC_OPEN,
        P("docker-13"),
        "Follow configs/inventory/restore-runbook-template.md for one throwaway VM",
        "Target: bare OS → docker-01 → clone Forgejo → fill `.env` files → compose up in README order → <1 hr",
        "Record gaps; update runbook in Forgejo",
    ],
    "commands": [],
    "files": ["configs/inventory/restore-runbook-template.md"],
    "verify": "Rebuild drill completes under 1 hour; gaps documented.",
}
O["glue-07"] = {
    "steps": [
        MAC_OPEN,
        P("net-14", "glue-05"),
        "MacBook: `pipx install ansible` or brew install ansible",
        f"`cd {REPO}/configs/ansible && ansible-galaxy collection install -r requirements.yml`",
        "Wake rig if testing all hosts: `ssh mini 'bash ~/wake-rig.sh'`",
        f"`cd {REPO}/configs/ansible && ansible all -i inventory.ini -m ping`",
    ],
    "commands": [
        f"cd {REPO}/configs/ansible && ansible-galaxy collection install -r requirements.yml",
        f"cd {REPO}/configs/ansible && ansible all -i inventory.ini -m ping",
    ],
    "files": ["configs/ansible/README.md", "configs/ansible/inventory.ini"],
    "verify": "ansible ping all green (mini + rig; NAS/HA excluded by design).",
}
O["sbom-01"] = {
    "steps": [
        MAC_OPEN,
        P("docker-06", "docker-09"),
        "**GATE:** NAS RAM ≥20GB before Dependency-Track + Immich ML (apiserver wants 4GB+ alone).",
        CM,
        f"`scp -r {REPO}/configs/docker-stack/stacks/dependency-track nas:/tmp/dependency-track`",
        "`ssh nas 'sudo mkdir -p /volume1/docker/dependency-track && sudo rsync -a /tmp/dependency-track/ /volume1/docker/dependency-track/'`",
        "`ssh nas 'cd /volume1/docker/dependency-track && cp -n .env.example .env && docker compose up -d'`",
        "Browser :9010 → create Automation team API key for sbom-nightly",
    ],
    "commands": [
        f"scp -r {REPO}/configs/docker-stack/stacks/dependency-track nas:/tmp/dependency-track",
        "ssh nas 'cd /volume1/docker/dependency-track && docker compose up -d'",
    ],
    "files": ["configs/docker-stack/stacks/dependency-track/compose.yaml", "configs/docker-stack/stacks/dependency-track/.env.example"],
    "docs": D(("Dependency-Track Docker", "https://docs.dependencytrack.org/getting-started/deploy-docker/"),),
    "verify": "DepTrack UI loads at :9010 or Caddy vhost.",
}
O["sbom-02"] = {"steps": [P("sbom-01"), f"Install sbom-nightly on each host from {REPO}/scripts/inventory"], "commands": [f"scp {REPO}/scripts/inventory/sbom-nightly.sh mini:/opt/scripts/"], "files": ["scripts/inventory/sbom-nightly.sh"], "verify": "SBOM uploaded nightly."}
O["sbom-03"] = {"steps": [P("glue-05"), "etckeeper on mini/rig/nas"], "commands": [f"scp {REPO}/scripts/inventory/etckeeper-setup.sh mini:/tmp/"], "files": ["configs/inventory/etckeeper.conf"], "verify": "etc commits on apt change."}
O["sbom-04"] = {"steps": [P("glue-05"), "export-manifests.sh cron"], "commands": [f"scp {REPO}/scripts/inventory/export-manifests.sh mini:/opt/scripts/"], "files": ["scripts/inventory/export-manifests.sh"], "verify": "Manifest in git."}
O["sbom-05"] = {"steps": [P("sbom-02", "sbom-03", "sbom-04", "glue-06"), "Write restore runbooks per host", "Execute one full rebuild"], "commands": [], "files": ["configs/inventory/restore-runbook-template.md"], "verify": "Rebuild drill documented."}
O["sec-01"] = {"steps": ["Hardware key: Bitwarden, Proton, DSM, Tailscale, Forgejo", "TOTP: Immich, Plex, Seerr, HA, seedbox panel", "Store backup codes offline"], "commands": [], "files": [], "verify": "2FA on all crown jewels."}
O["sec-02"] = {"steps": [P("docker-01"), "daemon.json log limits on mini/rig/nas docker", "Restart docker; recreate containers"], "commands": ["ssh mini 'cat /etc/docker/daemon.json'", "ssh rig 'cat /etc/docker/daemon.json'"], "files": [], "verify": "Log max-size 10m."}
O["sec-05"] = {"steps": ["unattended-upgrades on mini", "pacman cadence on rig", "DSM auto security updates"], "commands": ["ssh mini 'sudo unattended-upgrade --dry-run -d'"], "files": [], "verify": "Security updates automatic."}
O["sec-03"] = {"steps": [P("nas-02", "nas-06", "docker-09"), "B2 Object Lock", "Deploy healthchecks", "Wire backup pings to ntfy"], "commands": ["ssh mini 'cd /opt/stacks/healthchecks && docker compose up -d'"], "files": ["configs/docker-stack/stacks/healthchecks/compose.yaml"], "verify": "Skipped backup alerts."}
O["sec-04"] = {"steps": [P("seed-01", "docker-06"), "CrowdSec on seedbox", "Caddy forward-auth for public apps"], "commands": ["ssh seedbox 'cscli metrics'"], "files": [], "verify": "CrowdSec banning."}

# media-04 tdarr on NAS
O["media-04"] = {"steps": [P("nas-10", "game-08"), CM, "Tdarr server on NAS; node on rig", "Scan test folder"], "commands": [f"scp -r {REPO}/configs/docker-stack/stacks/tdarr nas:/tmp/"], "files": ["configs/docker-stack/stacks/tdarr/compose.yaml"], "verify": "Transcode completes on rig node."}

# game tasks
O["game-01"] = {"steps": [f"LinuxGSM on mini per {REPO}/scripts/gaming/linuxgsm-quickstart.md", "Start light server", "Tailscale only exposure"], "commands": [f"scp {REPO}/scripts/gaming/linuxgsm-quickstart.md mini:/tmp/"], "files": ["scripts/gaming/linuxgsm-quickstart.md"], "verify": "Server starts on mini."}
O["game-02"] = {"steps": [P("game-08"), "Pelican on rig for heavy servers"], "commands": [], "files": [], "verify": "Panel manages instance."}
O["game-03"] = {"steps": [P("game-08"), "Heavy servers on rig via LinuxGSM/Pelican"], "commands": [], "files": [], "verify": "Minecraft modpack runs."}
O["game-04"] = {"steps": [P("game-01"), "No port forwards; friends use Tailscale"], "commands": ["ssh mini 'tailscale status'"], "files": [], "verify": "Friend joins via tailnet."}
O["game-05"] = {
    "steps": [
        MAC_OPEN,
        P("game-08"),
        "Wake rig if asleep: `ssh mini 'bash ~/wake-rig.sh'`",
        f"`scp {REPO}/scripts/gaming/sunshine-autostart-notes.md rig:~/`",
        "On rig: add LizardByte pacman repo; `sudo pacman -S sunshine cuda`",
        "`ssh rig 'loginctl enable-linger $USER'`; enable user unit app-dev.lizardbyte.app.Sunshine",
        "First-run UI via tunnel: `ssh -L 47990:localhost:47990 rig` → https://localhost:47990",
        "Set NVENC; add Desktop app; clients must stay on Trusted VLAN for mDNS (game-06)",
    ],
    "commands": [
        f"scp {REPO}/scripts/gaming/sunshine-autostart-notes.md rig:~/",
        "ssh rig 'systemctl --user enable --now app-dev.lizardbyte.app.Sunshine'",
        "ssh rig 'sunshine --version'",
    ],
    "files": ["scripts/gaming/sunshine-autostart-notes.md"],
    "docs": D(("Sunshine", "https://docs.lizardbyte.dev/projects/sunshine/latest/md_docs_2getting__started.html"),),
    "verify": "Sunshine streams desktop with NVENC; user unit survives reboot.",
}
O["game-06"] = {"steps": [P("game-05"), "Moonlight on phone/TV same VLAN", "Pair with PIN"], "commands": [], "files": [], "verify": "In-home stream works."}
O["game-07"] = {"steps": [P("game-05", "game-06"), "`tailscale ping rig --until-direct`"], "commands": ["tailscale ping rig --until-direct"], "files": [], "verify": "Remote stream direct."}
O["game-08"] = {"steps": [f"`scp {REPO}/scripts/gaming/enable-wol-cachyos.sh rig:~/`", f"`scp {REPO}/scripts/gaming/wake-rig.sh mini:~/`", "Test wake from mini"], "commands": [f"scp {REPO}/scripts/gaming/wake-rig.sh mini:~/", "ssh mini '~/wake-rig.sh'"], "files": ["scripts/gaming/enable-wol-cachyos.sh", "scripts/gaming/wake-rig.sh"], "verify": "rig wakes from off."}
O["game-09"] = {"steps": [P("game-08"), "systemd suspend after idle on rig"], "commands": ["ssh rig 'systemctl status suspend.target'"], "files": [], "verify": "rig suspends when idle."}
O["game-10"] = {"steps": [f"`scp {REPO}/scripts/gaming/gpu-power-tune.sh rig:~/`", "Install gpu-power-tune.service"], "commands": [f"scp {REPO}/scripts/gaming/gpu-power-tune.sh rig:~/"], "files": ["scripts/gaming/gpu-power-tune.sh", "scripts/gaming/gpu-power-tune.service"], "verify": "Power limit persists reboot."}
O["game-11"] = {"steps": [P("game-05"), "Dummy HDMI or sunshine_virt_display", "PipeWire virtual sink"], "commands": ["ssh rig 'sudo pacman -S evdi-dkms'"], "files": [], "verify": "Headless stream matches client res."}
O["game-12"] = {"steps": [P("read-02"), "Ludusavi + Syncthing saves"], "commands": ["ssh rig 'ludusavi backup --force'"], "files": [], "verify": "Save restores on laptop."}
O["game-13"] = {"steps": [P("game-05", "ha-17"), "OLLAMA_KEEP_ALIVE=0", "No inference during stream"], "commands": ["ssh rig 'nvidia-smi --query-gpu=memory.used --format=csv'"], "files": [], "verify": "VRAM free after inference."}
O["game-14"] = {"steps": [P("game-05"), "Lutris/Heroic on rig; RomM on mini optional"], "commands": ["ssh rig 'lutris --version'"], "files": [], "verify": "Non-Steam game streams."}
O["ai-01"] = {"steps": [P("ha-17"), "ComfyUI on rig on-demand", "Continue → LiteLLM", "Open WebUI RAG optional"], "commands": ["ssh rig 'git clone https://github.com/comfyanonymous/ComfyUI'"], "files": [], "verify": "Image gen via ComfyUI."}

# --- Post-process: pad thin tasks ---
def pad(task_id: str, extra_steps=None, extra_cmds=None):
    if task_id not in O:
        return
    if extra_steps:
        O[task_id].setdefault("steps", []).extend(extra_steps)
    if extra_cmds:
        O[task_id].setdefault("commands", []).extend(extra_cmds)

pad("nas-00b", ["DSM Storage Manager → verify pool healthy before continuing"], ["ssh nas 'synogetkeyvalue /etc/synoinfo.conf volume_count'"])
pad("nas-02", ["Store B2 application key in Bitwarden; scope to single bucket only"], ["ssh nas 'synogetkeyvalue /usr/syno/etc/synobackup.conf' 2>/dev/null || echo configure in DSM GUI"])
pad("ha-01", ["Photograph cable/serial for inventory", "Add to Homepage when deployed"], ["ping -c 2 homeassistant.local || ping -c 2 192.168.10.x"])
pad("ha-04", ["Restart Home Assistant Core after HACS install"], ["curl -sf http://homeassistant:8123/api/ || true"])
pad("read-04", ["Connect Kobo to MacBook USB for initial KOReader install only", "Disconnect USB — all sync is WiFi after setup", "Document OPDS URL in KOReader favorites"], [])
pad("read-05", ["On Kobo WiFi: open KOReader → OPDS → add http://192.168.10.10:8083/opds", "Download one test book; confirm cover renders"], [])
pad("read-06", ["In CWA admin enable KOSync; match username on Kobo plugin settings"], [])
pad("read-08", ["Wallabag URL http://macmini.<tailnet>:8200 — create API token in Wallabag settings"], [])
pad("read-09", ["Miniflux → Settings → API → create key; paste into KOReader news plugin"], [])
pad("betty-01", ["In Deluge: Preferences → Plugins → Label enabled"], ["ssh seedbox 'deluge-console info 2>/dev/null || echo configure labels in WebUI'"])
pad("nas-22", ["Test import: add manual torrent in Deluge with label sonarr; confirm Sonarr Activity shows import"], ["ssh nas 'docker logs sonarr --tail 30'"])
pad("seed-08", ["Document completion date in configs/seedbox/decommission-old-nas-torrent.md"], ["ssh mini 'docker ps -a | grep -i plex || echo moved to NAS'"])

for tid, t in list(O.items()):
    steps = t.get("steps", [])
    if not any("MacBook" in s for s in steps[:3]):
        steps.insert(0, MAC_OPEN)
        t["steps"] = steps
    if len(steps) < 5:
        t.setdefault("steps", []).append("From MacBook: confirm completion matches the verify block before checking this task done.")

OUT.write_text(json.dumps(O, indent=2))
print(f"Wrote {len(O)} overrides to {OUT}")
