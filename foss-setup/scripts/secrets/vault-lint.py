#!/usr/bin/env python3
"""vault-lint.py — the vault-completeness class check (fix-23, quality-gate M26/M44/M45).

The incident class: a service is live on a host with working credentials in its own
config, but the handoff vault (.handoff-secrets.yaml) says '' — so the "ALL credentials
live in the vault" mandate silently breaks and disaster recovery loses the credential
(soulseek.* empty while slskd ran on betty; forgejo admin empty while Forgejo was the
deploy control plane; whisparr key only in config.xml).

This must run on the macbook — the vault never leaves it — so it cannot be a
verification/checks.d check (the runner lives on the mini). It is wired into
publish-deploy.sh instead: every publish lints the vault and fails loudly on empty keys.

Keys that are INTENTIONALLY empty (service not deployed / credential genuinely N/A)
belong in ALLOW_EMPTY with a reason, not silently blank.
"""
import sys
from pathlib import Path

import yaml

VAULT = Path(__file__).resolve().parents[2] / ".handoff-secrets.yaml"

# key-path -> why it is allowed to be empty
ALLOW_EMPTY = {
    "emporia.username": "Emporia Vue not integrated yet (no service consumes it)",
    "emporia.password": "Emporia Vue not integrated yet (no service consumes it)",
    "roborock.username": "Roborock integration retired from HA",
    "roborock.password": "Roborock integration retired from HA",
    "unifi_protect.host": "UniFi Protect not deployed",
    "unifi_protect.username": "UniFi Protect not deployed",
    "unifi_protect.password": "UniFi Protect not deployed",
    "sudo.mini_password": "mini has passwordless sudo by design",
    "hetzner_storage_box.username": "Hetzner storage box never adopted — B2 is the offsite target",
    "vesync.username": "future smart-home roadmap item, not integrated",
    "vesync.password": "future smart-home roadmap item, not integrated",
    "withings.client_id": "future smart-home roadmap item, not integrated",
    "withings.client_secret": "future smart-home roadmap item, not integrated",
}


def main() -> int:
    data = yaml.safe_load(VAULT.read_text())
    empties = []

    def walk(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                if str(k).startswith("_"):  # _meta and friends are structural, not secrets
                    continue
                walk(v, f"{path}.{k}" if path else str(k))
        elif node is None or (isinstance(node, str) and node.strip() == ""):
            empties.append(path)

    walk(data)
    bad = [p for p in empties if p not in ALLOW_EMPTY]
    stale_allows = [p for p in ALLOW_EMPTY if p not in empties]

    for p in stale_allows:
        print(f"vault-lint: NOTE stale ALLOW_EMPTY entry (key now set or gone): {p}")
    if bad:
        for p in bad:
            print(f"vault-lint: EMPTY vault key: {p} (populate it or add to ALLOW_EMPTY with a reason)")
        print(f"vault-lint: FAIL — {len(bad)} unexplained empty key(s)")
        return 1
    print(f"vault-lint: OK — no unexplained empty keys ({len(ALLOW_EMPTY)} documented exceptions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
