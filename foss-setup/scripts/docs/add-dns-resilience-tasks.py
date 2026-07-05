#!/usr/bin/env python3
"""Add dns-02..dns-05 resilience tasks + update dns-01 (idempotent)."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "docs" / "index.html"
AI_MAP = ROOT / "scripts" / "docs" / "ai-handoff-map.json"

text = HTML.read_text()
m = re.search(
    r'(<script type="application/json" id="taskData">\s*)(\[.*?\])(\s*</script>)',
    text,
    re.S,
)
if not m:
    raise SystemExit("taskData block not found")

tasks = json.loads(m.group(2))
by_id = {t["id"]: t for t in tasks}

# --- Update dns-01 (core only; resilience split out) --------------------------------
by_id["dns-01"]["title"] = (
    "DNS core on mini (Unbound + AdGuard upstream + tabaska.us rewrites)"
)
by_id["dns-01"]["steps"] = [
    "Prerequisite: docker-07 (AdGuard) complete.",
    "**Core (done):** Unbound on mini; AdGuard upstream `unbound:5335`; `*.tabaska.us` rewrites.",
    "Verify: `dig @192.168.10.2 google.com +short` and `dig @192.168.10.2 home.tabaska.us +short`.",
    "**Do not** point UniFi DHCP at AdGuard-only DNS until **dns-03** (fail-open chain) is live.",
    "Resilience work is **dns-02 → dns-05** — see configs/network/dns-resilience-plan.md.",
]
by_id["dns-01"]["commands"] = [
    "dig @192.168.10.2 google.com +short",
    "dig @192.168.10.2 home.tabaska.us +short",
    "ssh mini 'docker ps --filter name=adguardhome --filter name=unbound --format \"{{.Names}}: {{.Status}}\"'",
]
by_id["dns-01"]["files"] = [
    "configs/docker-stack/stacks/unbound/compose.yaml",
    "configs/docker-stack/stacks/adguard/compose.yaml",
    "configs/network/dns-resilience-plan.md",
]
by_id["dns-01"]["verify"] = (
    "Mini AdGuard resolves public + internal names. Resilience tasks dns-02–dns-05 still required "
    "before AdGuard is the sole DHCP DNS."
)

# --- New tasks --------------------------------------------------------------------
by_id["dns-02"] = {
    "id": "dns-02",
    "track": "ops",
    "title": "Deploy NAS secondary AdGuard + mirror rewrites (DHCP DNS #2)",
    "host": "NAS",
    "type": "sync",
    "depends_on": ["dns-01", "docker-07"],
    "estimate": "30-45 min",
    "required": False,
    "steps": [
        "Read configs/network/dns-resilience-plan.md — secondary must **not** depend on mini Unbound.",
        "Copy stack: `scp -r ~/Documents/Home/foss-setup/configs/docker-stack/stacks/adguard-nas nas:/tmp/adguard-nas`",
        "`ssh nas 'sudo mkdir -p /volume1/docker/adguard-nas && sudo rsync -a /tmp/adguard-nas/ /volume1/docker/adguard-nas/'`",
        "Container Manager → Project → create from compose at /volume1/docker/adguard-nas/compose.yaml → Start.",
        "First-run wizard at http://192.168.10.4:3000 — upstream: `tls://1.1.1.1` and `tls://9.9.9.9` (DoT).",
        "Mini AdGuard → Settings → Export settings; import rewrites/blocklists to NAS instance.",
        "Mirror every `*.tabaska.us → 192.168.10.2` DNS rewrite from mini.",
        "Test: `dig @192.168.10.4 google.com +short` and `dig @192.168.10.4 home.tabaska.us +short`.",
    ],
    "commands": [
        "scp -r ~/Documents/Home/foss-setup/configs/docker-stack/stacks/adguard-nas nas:/tmp/adguard-nas",
        "ssh nas 'sudo rsync -a /tmp/adguard-nas/ /volume1/docker/adguard-nas/'",
        "dig @192.168.10.4 google.com +short",
        "dig @192.168.10.4 home.tabaska.us +short",
    ],
    "files": [
        "configs/docker-stack/stacks/adguard-nas/compose.yaml",
        "configs/docker-stack/stacks/adguard-nas/README.md",
        "configs/network/dns-resilience-plan.md",
    ],
    "docs": [
        {
            "title": "AdGuard Home Docker",
            "url": "https://github.com/AdguardTeam/AdGuardHome/wiki/Docker",
        },
    ],
    "verify": "NAS AdGuard (:53 on 192.168.10.4) resolves public names and tabaska.us rewrites with mini stopped.",
}

by_id["dns-03"] = {
    "id": "dns-03",
    "track": "ops",
    "title": "UniFi DHCP fail-open DNS chain (mini → NAS → gateway)",
    "host": "device",
    "type": "sync",
    "depends_on": ["dns-02"],
    "estimate": "15 min",
    "required": False,
    "steps": [
        "Prerequisite: dns-02 (NAS AdGuard live and tested).",
        "Dream Wall → Settings → Networks → for **Trusted, IoT, Guest, Work** (each client VLAN):",
        "DHCP → DNS Server: **#1** `192.168.10.2` (mini), **#2** `192.168.10.4` (NAS), **#3** `192.168.10.1` (gateway).",
        "Save each network. Optionally set lease time to 1 h once to speed client migration, then restore 24 h.",
        "**Incident note (2026-07-03):** AdGuard-only DHCP with no fallback took the house offline when the mini rebooted.",
        "Run `./scripts/network/dns-resilience-verify.sh` from the MacBook.",
    ],
    "commands": ["./scripts/network/dns-resilience-verify.sh"],
    "files": ["configs/network/dns-resilience-plan.md"],
    "docs": [],
    "verify": "Each client VLAN DHCP lists three DNS servers in order; verify script passes.",
}

by_id["dns-04"] = {
    "id": "dns-04",
    "track": "ops",
    "title": "DNS outage runbook + automated verify script",
    "host": "device",
    "type": "async",
    "depends_on": ["dns-03"],
    "estimate": "15 min",
    "required": False,
    "steps": [
        "Script already in repo: `scripts/network/dns-resilience-verify.sh` (checks mini, NAS, gateway resolvers).",
        "Runbook in `configs/network/dns-resilience-plan.md` § Outage runbook — bookmark for incidents.",
        "Drill: `ssh mini 'cd /opt/stacks/adguard && docker compose stop'` → confirm NAS + gateway still resolve → restart AdGuard.",
        "Optional: add dns-resilience-verify to Uptime Kuma or a weekly cron on the MacBook.",
    ],
    "commands": [
        "./scripts/network/dns-resilience-verify.sh",
        "ssh mini 'cd /opt/stacks/adguard && docker compose stop'",
        "./scripts/network/dns-resilience-verify.sh",
        "ssh mini 'cd /opt/stacks/adguard && docker compose start'",
    ],
    "files": [
        "scripts/network/dns-resilience-verify.sh",
        "configs/network/dns-resilience-plan.md",
    ],
    "docs": [],
    "verify": "Verify script passes; mini-stop drill confirms NAS and gateway still resolve google.com.",
}

by_id["dns-05"] = {
    "id": "dns-05",
    "track": "ops",
    "title": "NAT :53 redirect + DoH blocking (only after fail-open chain)",
    "host": "device",
    "type": "async",
    "depends_on": ["dns-04"],
    "estimate": "20-30 min",
    "required": False,
    "steps": [
        "**Gate:** dns-03 fail-open chain verified. Do NOT enable if mini or NAS secondary is unstable.",
        "Dream Wall → Settings → Traffic Management / Firewall → NAT: redirect outbound UDP/TCP 53 to mini AdGuard.",
        "Block known DoH provider endpoints (Cloudflare, Google, etc.) so clients cannot bypass filtering.",
        "Re-run dns-resilience-verify.sh; simulate mini outage — confirm NAS still reachable.",
        "Accept tradeoff: redirect hardens bypass resistance but makes mini outage more painful if NAS secondary fails.",
    ],
    "commands": ["./scripts/network/dns-resilience-verify.sh"],
    "files": ["configs/network/dns-resilience-plan.md"],
    "docs": [
        {
            "title": "UniFi traffic rules",
            "url": "https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi",
        },
    ],
    "verify": "Outbound :53 redirected; DoH endpoints blocked; fail-open chain still passes with mini stopped.",
}

# Insert new tasks after dns-01 (preserve order)
ids = [t["id"] for t in tasks]
insert_block = ["dns-02", "dns-03", "dns-04", "dns-05"]
if "dns-01" in ids:
    for tid in insert_block:
        if tid in ids:
            ids.remove(tid)
    idx = ids.index("dns-01") + 1
    for i, tid in enumerate(insert_block):
        ids.insert(idx + i, tid)
else:
    for tid in insert_block:
        if tid not in ids:
            ids.append(tid)

# Apply updates preserving track/required from existing tasks
for tid in ids:
    if tid in by_id:
        if tid in {t["id"] for t in tasks}:
            old = next(t for t in tasks if t["id"] == tid)
            for k in ("track", "required", "phase"):
                if k in old and k not in by_id[tid]:
                    by_id[tid][k] = old[k]
        if "track" not in by_id[tid]:
            by_id[tid]["track"] = "ops"
        if "required" not in by_id[tid]:
            by_id[tid]["required"] = False

tasks_out = [by_id[i] for i in ids if i in by_id]
new_json = json.dumps(tasks_out, separators=(",", ":"))
HTML.write_text(text[: m.start(2)] + new_json + text[m.end(2) :])
print(f"Updated {HTML}: {len(tasks_out)} tasks")

# --- Update ai-handoff-map.json ---------------------------------------------------
ai = json.loads(AI_MAP.read_text())
ai["_meta"]["updated"] = "2026-07-03"
ai["auto"]["dns-01"] = "Unbound + AdGuard core on mini (done); resilience is dns-02–dns-05"
ai["auto"]["dns-02"] = "NAS secondary AdGuard compose + rewrite mirror"
ai["auto"]["dns-04"] = "dns-resilience-verify.sh + outage drill"
ai["assisted"]["dns-03"] = "UniFi DHCP fail-open DNS chain — GUI on Dream Wall"
ai["assisted"]["dns-05"] = "NAT :53 redirect + DoH blocking — UniFi GUI; gated on dns-04"
# Remove dns-01 from auto if it implied full hardening
AI_MAP.write_text(json.dumps(ai, indent=2) + "\n")
print(f"Updated {AI_MAP}")

# --- Patch aiHandoffMap inline in HTML -------------------------------------------
hm = re.search(
    r'(<script type="application/json" id="aiHandoffMap">)(.*?)(</script>)',
    HTML.read_text(),
    re.S,
)
if hm:
    HTML.write_text(
        HTML.read_text()[: hm.start(2)]
        + json.dumps(ai, separators=(",", ":"))
        + HTML.read_text()[hm.end(2) :]
    )
    print("Synced aiHandoffMap in index.html")

# --- Update static DNS panel in HTML ---------------------------------------------
html = HTML.read_text()
old_panel = (
    '<p class="panel-sub" style="margin-bottom:6px">Client → <b>AdGuard Home</b> (ad/tracker block) '
    "→ <b>Unbound</b> (recursive + DNSSEC) → root servers. A firewall NAT rule redirects all outbound "
    ":53 to the resolver and <b>blocks known DoH endpoints</b> so nothing bypasses the filter. "
    "AdGuard on the NAS is the DHCP secondary.</p>"
)
new_panel = (
    '<p class="panel-sub" style="margin-bottom:6px">Client DHCP DNS chain (fail-open): '
    "<b>#1 mini AdGuard</b> → <b>#2 NAS AdGuard</b> → <b>#3 gateway</b>. "
    "Mini path: AdGuard → Unbound (recursive + DNSSEC). NAS secondary uses independent DoT upstream. "
    "NAT :53 redirect + DoH blocking (<b>dns-05</b>) only after the three-tier chain is verified — "
    "see <code>configs/network/dns-resilience-plan.md</code>.</p>"
)
if old_panel in html:
    html = html.replace(old_panel, new_panel)
    HTML.write_text(html)
    print("Updated DNS panel in index.html")
