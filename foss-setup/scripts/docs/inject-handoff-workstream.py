#!/usr/bin/env python3
"""Add Agent handoff prep tier + tasks to docs/index.html (idempotent)."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "docs" / "index.html"

HANDOFF_TASKS = [
    {
        "id": "handoff-01",
        "track": "agent-handoff",
        "title": "Verify SSH from MacBook to all four hosts",
        "host": "device",
        "type": "sync",
        "depends_on": ["prep-01", "net-14"],
        "estimate": "15 min",
        "required": False,
        "steps": [
            "From your MacBook (operator station), confirm `~/.ssh/config` has aliases from `configs/network/ssh-config.example` — `nas`, `mini`, `rig`, `seedbox`.",
            "Test each host: `ssh nas 'hostname'`, `ssh mini 'hostname'`, `ssh seedbox 'hostname'`.",
            "For the rig (often asleep): `RIG_MAC=<mac> ./scripts/gaming/wake-rig.sh && sleep 30 && ssh rig 'hostname'`.",
            "If any host fails, fix keys or Tailscale before starting agent work — see `configs/network/ssh-maintenance-access.md`.",
        ],
        "commands": [
            "ssh nas 'hostname'",
            "ssh mini 'hostname'",
            "ssh seedbox 'hostname'",
            "RIG_MAC=aa:bb:cc:dd:ee:ff ./scripts/gaming/wake-rig.sh && sleep 30 && ssh rig 'hostname'",
        ],
        "files": ["configs/network/ssh-config.example", "configs/network/ssh-maintenance-access.md"],
        "docs": [],
        "verify": "All four aliases return a hostname without password prompts (Tailscale SSH or homelab key).",
    },
    {
        "id": "handoff-02",
        "track": "agent-handoff",
        "title": "Create local secrets vault from template",
        "host": "device",
        "type": "sync",
        "depends_on": ["handoff-01"],
        "estimate": "5 min",
        "required": False,
        "steps": [
            "In `foss-setup/`: `cp .handoff-secrets.yaml.example .handoff-secrets.yaml`",
            "Restrict permissions: `chmod 600 .handoff-secrets.yaml`",
            "Confirm `.handoff-secrets.yaml` is gitignored (repo root `.gitignore`).",
            "You will fill sections in the next tasks — leave values blank for now.",
        ],
        "commands": [
            "cd ~/Documents/Home/foss-setup",
            "cp -n .handoff-secrets.yaml.example .handoff-secrets.yaml",
            "chmod 600 .handoff-secrets.yaml",
        ],
        "files": [".handoff-secrets.yaml.example"],
        "docs": [],
        "verify": "`.handoff-secrets.yaml` exists, mode 600, and is not tracked by git.",
    },
    {
        "id": "handoff-03",
        "track": "agent-handoff",
        "title": "Fill host inventory in secrets vault",
        "host": "device",
        "type": "sync",
        "depends_on": ["handoff-02"],
        "estimate": "10 min",
        "required": False,
        "steps": [
            "Open `.handoff-secrets.yaml` and set `_meta.tailnet` to your MagicDNS suffix (Tailscale admin → DNS).",
            "Fill `hosts.nas`, `hosts.mini`, `hosts.rig`, `hosts.seedbox` — LAN IPs match the Network tab (Trusted VLAN 10).",
            "Set `hosts.rig.wol_mac` from your rig NIC (used by `scripts/gaming/wake-rig.sh`).",
            "Optional: fill `hosts.ha` when HA Green is plugged in (192.168.10.13 reservation).",
        ],
        "commands": [
            "tailscale status --json | head",
            "ssh mini 'ip -4 addr show | grep 192.168.10'",
        ],
        "files": [".handoff-secrets.yaml.example"],
        "docs": [],
        "verify": "Every host you plan to hand off has ssh_user, LAN IP or tailnet name, and rig has wol_mac.",
    },
    {
        "id": "handoff-04",
        "track": "agent-handoff",
        "title": "Gather API keys from services already running",
        "host": "device",
        "type": "sync",
        "depends_on": ["handoff-03"],
        "estimate": "15 min",
        "required": False,
        "steps": [
            "From each *arr on the NAS (Sonarr :8989, Radarr :7878, Lidarr :8686, Readarr :8787, Prowlarr :9696): Settings → General → copy API key into `arr_api_keys` in the vault.",
            "Plex: copy claim token or copy `X-Plex-Token` into `plex.token` (NAS at :32400).",
            "Deluge on Betty: Web UI password → `deluge.password` (needed for remote path mappings).",
            "Skip keys for apps not deployed yet — the agent can generate those during deploy.",
        ],
        "commands": [
            "open http://192.168.10.4:8989",
            "open http://192.168.10.4:32400/web",
        ],
        "files": [".handoff-secrets.yaml.example"],
        "docs": [],
        "verify": "Vault has non-empty arr_api_keys for every *arr you use today, plus plex.token and deluge.password.",
    },
    {
        "id": "handoff-05",
        "track": "agent-handoff",
        "title": "Create Backblaze B2 bucket + application key",
        "host": "device",
        "type": "sync",
        "depends_on": ["handoff-03"],
        "estimate": "20 min",
        "required": False,
        "steps": [
            "Backblaze B2 console → Create bucket for NAS Hyper Backup (e.g. `homelab-nas-tier1`).",
            "Create a second bucket or prefix for restic on mini/rig (e.g. `homelab-restic`).",
            "Application Keys → create key scoped to those buckets (read + write).",
            "Paste `account_id` and `application_key` into `backblaze_b2` in the vault.",
            "Generate restic repo passwords: `openssl rand -base64 48` — one for mini, one for rig — store in vault AND your password manager.",
        ],
        "commands": [
            "openssl rand -base64 48",
        ],
        "files": ["scripts/backup/restic-backup.env.example"],
        "docs": [
            {"title": "restic + B2", "url": "https://www.backblaze.com/docs/cloud-storage-integrate-restic-with-backblaze-b2"},
        ],
        "verify": "Vault has B2 account_id, application_key, bucket names, and two unique restic passwords saved in your password manager too.",
    },
    {
        "id": "handoff-06",
        "track": "agent-handoff",
        "title": "(Optional) Add cloud creds for upcoming batches",
        "host": "device",
        "type": "async",
        "depends_on": ["handoff-03"],
        "estimate": "20 min",
        "required": False,
        "steps": [
            "Only fill sections you need for the batch you're about to run — skip the rest.",
            "**Off-site backup batch:** Hetzner Storage Box username (Borg, port 23).",
            "**Ops wave 2 (Caddy HTTPS):** Cloudflare API token with Zone.DNS edit.",
            "**sec-03:** Healthchecks.io ping URLs for restic/Borg dead-man switches.",
            "**Smart home batch:** UniFi Protect local creds, Hue bridge IP, Soulseek/slskd passwords.",
            "**Forgejo (glue-05):** admin username + strong password.",
        ],
        "commands": [],
        "files": [".handoff-secrets.yaml.example", "scripts/backup/borgmatic-config.yaml"],
        "docs": [],
        "verify": "Optional vault sections for your chosen batch are filled; empty sections are fine for later.",
    },
    {
        "id": "handoff-07",
        "track": "agent-handoff",
        "title": "Choose how sudo works during agent sessions",
        "host": "device",
        "type": "sync",
        "depends_on": ["handoff-02"],
        "estimate": "10 min",
        "required": False,
        "steps": [
            "Pick one approach and note it in the vault under each host's `sudo_mode`:",
            "**password** (recommended): store `sudo.mini_password` / `sudo.nas_password` in the vault — agent asks once per session; delete after cleanup.",
            "**present**: you stay at the MacBook and type sudo when prompted — slowest but no stored passwords.",
            "**nopasswd-snippet** (advanced): temporary narrow `/etc/sudoers.d/cursor-handoff` on mini only — remove in handoff-12.",
            "NAS DSM sudo often requires your DSM admin password for `ssh -t nas 'sudo ...'`.",
        ],
        "commands": [
            "ssh -t mini 'sudo -v'",
            "ssh -t nas 'sudo -v'",
        ],
        "files": ["configs/network/ssh-maintenance-access.md"],
        "docs": [],
        "verify": "You know which sudo_mode each host uses and the vault reflects it.",
    },
    {
        "id": "handoff-08",
        "track": "agent-handoff",
        "title": "Physical prep — do only when starting that track",
        "host": "device",
        "type": "async",
        "depends_on": [],
        "estimate": "30 min",
        "required": False,
        "steps": [
            "Not needed for the first agent batch (ops wave 1). Complete items when you reach the related rollout track:",
            "**Smart home (ha-02):** Plug HA Green into Trusted VLAN; UniFi DHCP reservation 192.168.10.13; enable Advanced SSH add-on.",
            "**Zigbee (ha-12):** Insert USB coordinator into HA Green (use a short USB-2 extension).",
            "**Tier-2 backup (nas-03):** Plug external HDD into NAS USB; note DSM mount path.",
            "**Gaming (game-11):** HDMI dummy plug on rig GPU if no monitor attached.",
            "Check off this task when you've read the list — individual items get checked when done.",
        ],
        "commands": [],
        "files": [],
        "docs": [],
        "verify": "You know which physical steps apply to which rollout track; hardware is ready before the agent starts that track.",
    },
    {
        "id": "handoff-09",
        "track": "agent-handoff",
        "title": "Pick your first agent batch in the rollout guide",
        "host": "device",
        "type": "sync",
        "depends_on": ["handoff-04", "handoff-07"],
        "estimate": "5 min",
        "required": False,
        "steps": [
            "Click **AI handoff only** in the header filter to see delegatable rollout tasks.",
            "Recommended first batch — **Ops wave 1:** `docker-07` AdGuard → `docker-08` Dockge → `docker-09` ntfy → `docker-10` Beszel → `glue-05` Forgejo (all compose deploys on mini).",
            "Alternative if backbone first: `nas-01` snapshots + `glue-01` UPS/NUT.",
            "Write the task IDs you want in `_meta.notes` in the vault so the agent has a explicit scope.",
        ],
        "commands": [],
        "files": [],
        "docs": [],
        "verify": "You have a short ordered list of rollout task IDs for the first agent session.",
    },
    {
        "id": "handoff-10",
        "track": "agent-handoff",
        "title": "Start a Cursor agent session (share path, not secrets)",
        "host": "device",
        "type": "sync",
        "depends_on": ["handoff-09"],
        "estimate": "5 min",
        "required": False,
        "steps": [
            "Open Cursor on the MacBook with this repo at `~/Documents/Home/foss-setup`.",
            "Tell the agent: vault file path (`foss-setup/.handoff-secrets.yaml`), first batch task IDs, and that SSH aliases work.",
            "**Do not paste vault contents into chat** — the agent reads the file locally.",
            "Approve SSH/sudo commands when prompted. Agent runs from your MacBook via `ssh mini` / `ssh nas` etc.",
            "Let the agent check off rollout tasks in this guide as it completes them (or export progress when done).",
        ],
        "commands": [],
        "files": [".handoff-secrets.yaml.example"],
        "docs": [],
        "verify": "Agent session is running with vault path shared and first batch scope agreed.",
    },
    {
        "id": "handoff-11",
        "track": "agent-handoff",
        "title": "15-minute verification window after each batch",
        "host": "device",
        "type": "sync",
        "depends_on": ["handoff-10"],
        "estimate": "15 min",
        "required": False,
        "steps": [
            "When the agent finishes a deploy batch, block 15 minutes for spot-checks.",
            "**E2E media (seed-07):** request something in Seerr; confirm playback in Plex.",
            "**E2E music (seed-10):** request in MusicSeerr; confirm in Plex or Navidrome.",
            "**Smart home:** Hue link button, HomeKit pairing code, or 'yes that played' — agent will tell you exactly when.",
            "Reply with one-word confirmations in chat; no need to debug logs yourself unless something fails.",
        ],
        "commands": [],
        "files": [],
        "docs": [],
        "verify": "You completed spot-checks for the batch or filed a short failure note for the agent to fix.",
    },
    {
        "id": "handoff-12",
        "track": "agent-handoff",
        "title": "Post-sprint cleanup — delete vault and rotate keys",
        "host": "device",
        "type": "async",
        "depends_on": ["handoff-10"],
        "estimate": "10 min",
        "required": False,
        "steps": [
            "Delete `foss-setup/.handoff-secrets.yaml` (or shred: `rm -P .handoff-secrets.yaml`).",
            "Revoke or rotate B2 application keys created only for the handoff sprint; issue new scoped keys if backups keep running.",
            "Remove any temporary `/etc/sudoers.d/cursor-handoff` on mini.",
            "Export rollout progress JSON (header → Export progress) before closing the browser tab.",
            "Rotate any sudo passwords that were stored in the vault during the sprint.",
        ],
        "commands": [
            "rm -f ~/Documents/Home/foss-setup/.handoff-secrets.yaml",
            "ssh mini 'sudo rm -f /etc/sudoers.d/cursor-handoff'",
        ],
        "files": [],
        "docs": [],
        "verify": "Vault file gone, temp sudoers gone, B2 keys rotated if applicable, progress exported.",
    },
]


def patch_tier_meta(text: str) -> str:
    tier = json.loads(re.search(r'id="tierMeta">\s*(\{.*?\})\s*</script>', text, re.S).group(1))
    if "handoff" not in tier:
        tier = {
            "handoff": {
                "title": "Agent handoff prep",
                "sub": "One-time checklist (~1–2 hrs) before delegating purple AI handoff tasks. Secrets stay in a local file on your MacBook — never paste into chat.",
            },
            **tier,
        }
        text = re.sub(
            r'(<script type="application/json" id="tierMeta">\s*)\{.*?\}(\s*</script>)',
            lambda m: m.group(1) + json.dumps(tier, ensure_ascii=False) + m.group(2),
            text,
            count=1,
            flags=re.S,
        )
    return text


def patch_track_meta(text: str) -> str:
    track = json.loads(re.search(r'id="trackMeta">\s*(\{.*?\})\s*</script>', text, re.S).group(1))
    if "agent-handoff" not in track:
        track["agent-handoff"] = {
            "tier": "handoff",
            "order": 0,
            "title": "Agent handoff prep",
            "sub": "SSH check → secrets vault → optional B2/creds → sudo mode → pick batch → run agent → verify → cleanup.",
        }
        text = re.sub(
            r'(<script type="application/json" id="trackMeta">\s*)\{.*?\}(\s*</script>)',
            lambda m: m.group(1) + json.dumps(track, indent=2, ensure_ascii=False) + "\n" + m.group(2),
            text,
            count=1,
            flags=re.S,
        )
    return text


def patch_tasks(text: str) -> str:
    m = re.search(r'(<script type="application/json" id="taskData">\s*)(\[.*?\])(\s*</script>)', text, re.S)
    tasks = json.loads(m.group(2))
    by_id = {t["id"]: t for t in tasks}
    for t in HANDOFF_TASKS:
        by_id[t["id"]] = t
    # handoff tasks first in array for readability, then rest stable order
    handoff_ids = [t["id"] for t in HANDOFF_TASKS]
    rest = [t for t in tasks if t["id"] not in handoff_ids]
    merged = [by_id[i] for i in handoff_ids] + rest
    new_json = json.dumps(merged, ensure_ascii=False, separators=(",", ":"))
    return text[: m.start(2)] + new_json + text[m.end(2) :]


def patch_tier_order(text: str) -> str:
    old = 'const TIER_ORDER = ["backbone", "workstreams", "operations", "enhancements"];'
    new = 'const TIER_ORDER = ["handoff", "backbone", "workstreams", "operations", "enhancements"];'
    if old in text:
        text = text.replace(old, new, 1)
    return text


def patch_intro(text: str) -> str:
    card = (
        '        <div class="wscard gate"><div class="ws-label">0 · Agent handoff</div>'
        "<h4>Prep vault + SSH</h4>"
        "<p>12-task checklist before delegating purple <b>AI handoff</b> rollout tasks. Finish the <b>Agent handoff prep</b> track first.</p>"
        '<div class="ws-meta">~1–2 hrs · one time</div></div>\n'
    )
    if "0 · Agent handoff" not in text:
        text = text.replace(
            '      <div class="ws-grid">\n        <div class="wscard gate"><div class="ws-label">A · Backbone finish</div>',
            '      <div class="ws-grid">\n' + card + '        <div class="wscard gate"><div class="ws-label">A · Backbone finish</div>',
            1,
        )
    intro_note = (
        ' <b>Delegating to an AI agent?</b> Start with the <b>Agent handoff prep</b> tier above the backbone — '
        "then filter <b>AI handoff only</b> for rollout tasks the agent can run."
    )
    if "Delegating to an AI agent" not in text:
        text = text.replace(
            'Click any task for steps, commands, config files, and a concrete "done when" check.</p>',
            'Click any task for steps, commands, config files, and a concrete "done when" check.' + intro_note + "</p>",
            1,
        )
    legend = (
        '      <span><i class="dot" style="background:#c4b5fd"></i> <b>AI handoff</b> — agent can run via SSH/sudo with minimal input</span>\n'
    )
    if "AI handoff</b> — agent can run" not in text:
        text = text.replace(
            '      <span><i class="dot" style="background:var(--sync)"></i> <b>Synchronous</b>',
            legend + '      <span><i class="dot" style="background:var(--sync)"></i> <b>Synchronous</b>',
            1,
        )
    return text


def main() -> None:
    text = HTML.read_text()
    text = patch_tier_meta(text)
    text = patch_track_meta(text)
    text = patch_tasks(text)
    text = patch_tier_order(text)
    text = patch_intro(text)
    HTML.write_text(text)
    print(f"Injected {len(HANDOFF_TASKS)} handoff tasks into {HTML}")


if __name__ == "__main__":
    main()
