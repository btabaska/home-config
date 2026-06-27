#!/usr/bin/env python3
"""Tighten required baseline: per-task `required` flag, gap tasks, dependency fixes."""
import json
import re
from pathlib import Path

HTML = Path(__file__).resolve().parents[2] / "docs" / "index.html"

# Foundational only — without these, multiple downstream feature tasks fail on blank hosts.
REQUIRED_IDS = {
    "prep-01",
    "net-00", "net-01", "net-02", "net-03", "net-04", "net-05", "net-06",
    "net-07", "net-08", "net-11", "net-13", "net-14",
    "nas-00a", "nas-00b", "nas-00c", "nas-00d", "nas-01", "nas-prep-01",
    "docker-01", "docker-02",
}

NEW_TASKS = {
    "prep-01": {
        "id": "prep-01",
        "track": "desktop",
        "title": "Operator station: clone foss-setup and verify SSH/scp",
        "host": "device",
        "type": "sync",
        "depends_on": [],
        "estimate": "10 min",
        "steps": [
            "On your MacBook: ensure Xcode Command Line Tools are installed (`xcode-select --install` if `git` is missing).",
            "Clone or copy this repo to `~/Documents/Home/foss-setup` (USB/offline copy is fine until Forgejo exists in the ops track).",
            "Confirm SSH client tools work: `ssh -V` and `scp` are available.",
            "All later tasks assume you run `scp`/`ssh` from this MacBook once Tailscale and SSH keys land in net-14.",
        ],
        "commands": [
            "mkdir -p ~/Documents/Home",
            "test -d ~/Documents/Home/foss-setup && echo ok || echo 'clone repo first'",
            "ssh -V",
        ],
        "files": ["README.md"],
        "docs": [],
        "verify": "The foss-setup repo exists at ~/Documents/Home/foss-setup and ssh/scp run without error.",
    },
    "nas-prep-01": {
        "id": "nas-prep-01",
        "track": "nas-foundation",
        "title": "Enable Container Manager on the NAS (Docker/Compose prerequisite)",
        "host": "NAS",
        "type": "sync",
        "depends_on": ["nas-00c", "net-08"],
        "estimate": "10 min",
        "steps": [
            "On your MacBook browser: sign in to DSM at the NAS LAN or Tailscale address.",
            "Package Center → search **Container Manager** → Install (DSM 7.2+).",
            "Open Container Manager once to accept terms and confirm the daemon starts.",
            "For CLI deploys from net-14: Control Panel → Terminal & SNMP → Enable SSH service (if not already).",
            "Verify: Container Manager shows Container / Project tabs with no errors.",
        ],
        "commands": [
            "ssh nas 'docker version 2>/dev/null || /usr/local/bin/docker version'",
            "ssh nas 'docker compose version 2>/dev/null || /usr/local/bin/docker compose version'",
        ],
        "files": [],
        "docs": [
            {
                "title": "Synology Container Manager",
                "url": "https://www.synology.com/en-us/dsm/feature/docker",
            }
        ],
        "verify": "Container Manager is installed and `docker version` succeeds on the NAS (via DSM or ssh).",
    },
    "nas-28": {
        "id": "nas-28",
        "track": "media-pipeline",
        "title": "Apply TRaSH quality profiles + naming via Recyclarr (Ubuntu → NAS *arrs)",
        "host": "Ubuntu",
        "type": "sync",
        "depends_on": ["nas-22", "docker-02"],
        "estimate": "30-45 min",
        "steps": [
            "On your MacBook: open this task's verify block and keep the repo at ~/Documents/Home/foss-setup handy.",
            "Prerequisite: nas-22, docker-01, docker-02 complete.",
            "Recyclarr runs on the Mac mini and pushes TRaSH Guides profiles + Plex-friendly naming to Sonarr/Radarr on the NAS.",
            "`scp -r ~/Documents/Home/foss-setup/configs/docker-stack/stacks/recyclarr mini:/tmp/recyclarr`",
            "`ssh mini 'sudo rsync -a /tmp/recyclarr/ /opt/stacks/recyclarr/'`",
            "Edit config/recyclarr.yml: NAS base_url http://192.168.10.10:8989 / :7878 + API keys from each *arr → Settings → General.",
            "`ssh mini 'cd /opt/stacks/recyclarr && cp -n .env.example .env && docker compose run --rm recyclarr sync'`",
            "Schedule weekly recyclarr sync (cron or Diun-triggered).",
        ],
        "commands": [
            "scp -r ~/Documents/Home/foss-setup/configs/docker-stack/stacks/recyclarr mini:/tmp/recyclarr",
            "ssh mini 'sudo rsync -a /tmp/recyclarr/ /opt/stacks/recyclarr/'",
            "ssh mini 'cd /opt/stacks/recyclarr && docker compose run --rm recyclarr sync'",
        ],
        "files": [
            "configs/docker-stack/stacks/recyclarr/compose.yaml",
            "configs/docker-stack/stacks/recyclarr/config/recyclarr.yml",
            "configs/docker-stack/stacks/recyclarr/.env.example",
        ],
        "docs": [
            {"title": "Recyclarr getting started", "url": "https://recyclarr.dev/guide/getting-started/"},
            {"title": "TRaSH Sonarr naming", "url": "https://trash-guides.info/Sonarr/Sonarr-recommended-naming-scheme/"},
        ],
        "verify": "recyclarr sync exits 0; Sonarr/Radarr show TRaSH quality profiles and plex-tmdb naming enabled.",
    },
}

DEP_FIXES = {
    "docker-01": ["prep-01", "net-14"],
    "glue-01": ["net-08", "net-14"],
    "nas-08": ["nas-01", "nas-prep-01"],
    "nas-09": ["nas-00c", "nas-prep-01"],
    "nas-21": ["nas-20", "nas-prep-01"],
    "doc-01": ["nas-01", "nas-prep-01"],
    "seed-05": ["docker-03", "nas-22", "nas-28"],
    "seed-07": ["seed-05", "nas-25", "nas-10"],
}

INSERT_AFTER = {
    "prep-01": None,  # first task overall
    "nas-prep-01": "nas-00c",
    "nas-28": "nas-22",
}


def main():
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

    for tid, body in NEW_TASKS.items():
        if tid not in by_id:
            by_id[tid] = body

    for tid, deps in DEP_FIXES.items():
        if tid in by_id:
            by_id[tid]["depends_on"] = deps

    for tid, t in by_id.items():
        t["required"] = tid in REQUIRED_IDS

    # Rebuild ordered list: insert new tasks at anchors
    ids = [t["id"] for t in tasks if t["id"] in by_id]
    for new_id, after in INSERT_AFTER.items():
        if new_id in ids:
            continue
        if after is None:
            ids.insert(0, new_id)
        elif after in ids:
            ids.insert(ids.index(after) + 1, new_id)
        else:
            ids.append(new_id)

    tasks_out = [by_id[i] for i in ids]
    new_json = json.dumps(tasks_out, separators=(",", ":"))
    text = text[: m.start(2)] + new_json + text[m.end(2) :]

    # Replace REQUIRED Set with per-task flag reader
    text = re.sub(
        r"  // Required =.*?  const isRequired = id => REQUIRED\.has\(id\);\n",
        "  const isRequired = t => !!t.required;\n",
        text,
        count=1,
        flags=re.S,
    )

    HTML.write_text(text)
    req_count = sum(1 for t in tasks_out if t.get("required"))
    print(f"Updated {len(tasks_out)} tasks; {req_count} marked required")
    print("Required:", ", ".join(sorted(REQUIRED_IDS)))


if __name__ == "__main__":
    main()
