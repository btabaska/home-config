#!/usr/bin/env python3
"""homepage-tiles-resolve — fix-29 / M17 class guard.

A homepage tile whose siteMonitor/widget points at a *bare docker-DNS name*
(e.g. http://maintainerr:6246) is only reachable if a container by that name is
running on the shared docker network. When the container is retired but the tile
is left behind, homepage cannot resolve the name -> `getaddrinfo EAI_AGAIN` on
every dashboard view (M17: 264 such errors in 96h from the dead Maintainerr
tile). This is a config->reality reconciliation: it flags any bare-name tile that
has no running container behind it. IP/FQDN targets (NAS, seedbox, external
vhosts) are monitored elsewhere and skipped — this guards the retired-container
class specifically.

Prints  DEAD_TILES=NONE  (green) or  DEAD_TILES=<kind:host,...>  (fail).
"""
import re
import subprocess
import sys

import yaml

CFG = "/opt/stacks/homepage/config/services.yaml"


def bare_host(url):
    """Return the hostname iff it is a bare docker-DNS name (no dot, not an IP,
    not localhost); else None (IP/FQDN/external -> not our class)."""
    m = re.match(r"https?://([^:/]+)", url or "")
    if not m:
        return None
    h = m.group(1)
    if h == "localhost" or "." in h:  # FQDN or dotted; IPs contain dots too
        return None
    return h


def collect(node, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "siteMonitor" and isinstance(v, str):
                out.append(("siteMonitor", v))
            elif k == "url" and isinstance(v, str) and v.startswith("http"):
                out.append(("widget.url", v))
            else:
                collect(v, out)
    elif isinstance(node, list):
        for x in node:
            collect(x, out)


def main():
    try:
        cfg = yaml.safe_load(open(CFG))
    except Exception as e:  # noqa: BLE001
        print(f"DEAD_TILES=ERROR_READING_CONFIG ({e})")
        return 1
    running = set(
        subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True,
        ).stdout.split()
    )
    tiles = []
    collect(cfg, tiles)
    dead = []
    for kind, url in tiles:
        h = bare_host(url)
        if h and h not in running:
            dead.append(f"{kind}:{h}")
    print("DEAD_TILES=" + (",".join(sorted(set(dead))) if dead else "NONE"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
