#!/usr/bin/env python3
"""gen-wiki-services.py — generate wiki service pages from compose files (wiki-02).

Walks every compose stack in the repo:

  configs/docker-stack/stacks/*/compose.yaml      -> host: mini (adguard-nas -> nas)
  configs/docker-stack/*/docker-compose.yml       -> host: mini (wallabag)
  configs/nas/*/docker-compose.yml                -> host: nas

and emits one Markdown man-page per stack into wiki/docs/services/, plus a
generated services/index.md grouped by category, plus the nav block in
wiki/mkdocs.yml (between the BEGIN/END GENERATED SERVICES NAV markers).

Facts per stack: image + pin per service, host, ports, canonical URL
(https://<name>.tabaska.us convention, with known overrides), env var NAMES
from .env.example (never values), volumes, upstream doc links parsed from the
compose header comment.

Enrichment: if configs/docker-stack/service-catalog.yaml exists, its
category/url/description fields override the built-in maps (absence is fine).

Dependency-free: uses PyYAML when importable, otherwise falls back to a
minimal regex parser good enough for these simple compose files.

Usage:  python3 foss-setup/scripts/docs/gen-wiki-services.py
Output is deterministic (sorted) so re-running on a clean tree yields no diff.
"""

import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]  # .../foss-setup
WIKI_DOCS = REPO / "wiki" / "docs" / "services"
MKDOCS_YML = REPO / "wiki" / "mkdocs.yml"
CATALOG = REPO / "configs" / "docker-stack" / "service-catalog.yaml"

try:
    import yaml  # type: ignore
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False

# ---------------------------------------------------------------- metadata

# Known URL overrides (handoff key-URLs); everything else falls back to the
# https://<stack>.tabaska.us convention. None = no web UI / not proxied.
URL_OVERRIDES = {
    "adguard": "https://dns.tabaska.us",
    "adguard-nas": "http://192.168.10.4:3000 (LAN; secondary DNS itself is :53)",
    "caddy": None,  # caddy IS the proxy
    "unbound": None,
    "diun": None,
    "recyclarr": None,
    "kometa": None,
    "homepage": "https://home.tabaska.us",
    "miniflux": "https://rss.tabaska.us",
    "navidrome": "https://music.tabaska.us",
    "mealie": "https://recipes.tabaska.us",
    "paperless-ngx": "https://paperless.tabaska.us",
    "uptime-kuma": "https://uptime.tabaska.us",
    "dependency-track": "https://deptrack.tabaska.us",
    "immich": "https://immich.tabaska.us (LAN: http://192.168.10.4:2283)",
    "calibre-web-automated": "http://192.168.10.4:8083 (deliberately LAN/VPN-only)",
    "libreseerr": "https://libreseerr.tabaska.us (LAN: http://192.168.10.2:8789)",
    "media-automation": None,  # multi-app stack; per-service ports below
    "vaultwarden": "https://vault.tabaska.us",
}

CATEGORIES = {
    "Networking & Access": ["caddy", "adguard", "adguard-nas", "unbound"],
    "Media & Acquisition": [
        "seerr", "musicseerr", "libreseerr", "media-automation", "tautulli",
        "kometa", "maintainerr", "recyclarr", "tdarr", "pinchflat", "stash",
    ],
    "Photos & Reading": [
        "immich", "calibre-web-automated", "miniflux", "wallabag", "navidrome",
    ],
    "Documents & Life": ["paperless-ngx", "mealie"],
    "Monitoring & Ops": [
        "homepage", "uptime-kuma", "beszel", "ntfy", "diun", "healthchecks",
        "dockge", "dependency-track", "vaultwarden",
    ],
    "AI & Cameras": ["litellm", "frigate"],
}
FALLBACK_CATEGORY = "Uncategorized"

# ------------------------------------------------------------ compose parse


def parse_header(text):
    """First comment block -> (description, [doc urls])."""
    desc, urls = "", []
    for line in text.splitlines():
        if not line.startswith("#"):
            if line.strip():
                break
            continue
        body = line.lstrip("#").strip()
        if not desc and re.search(r"[A-Za-z]", body):
            desc = body
        urls += re.findall(r"https?://[^\s)\"']+", body)
    # de-dup, keep order
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return desc, out[:3]


def parse_compose_yaml(text):
    """Return {service: {image, ports[], volumes[]}} via PyYAML."""
    data = yaml.safe_load(text) or {}
    out = {}
    for name, svc in (data.get("services") or {}).items():
        if not isinstance(svc, dict):
            continue
        out[name] = {
            "image": svc.get("image") or ("(built from ./Dockerfile)" if svc.get("build") else ""),
            "ports": [str(p) for p in (svc.get("ports") or [])],
            "volumes": [str(v) for v in (svc.get("volumes") or [])],
        }
    return out


def parse_compose_regex(text):
    """Minimal fallback parser for simple compose files (no PyYAML)."""
    out = {}
    lines = text.splitlines()
    in_services, svc, key = False, None, None
    svc_indent = None
    for raw in lines:
        line = raw.split(" #")[0].rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        if re.match(r"^services:\s*$", line):
            in_services, svc = True, None
            continue
        if in_services and indent == 0 and line.endswith(":"):
            in_services = False  # networks:/volumes: top-level
            continue
        if not in_services:
            continue
        m = re.match(r"^(\s+)([A-Za-z0-9._-]+):\s*$", line)
        if m and (svc_indent is None or len(m.group(1)) <= svc_indent):
            svc_indent = len(m.group(1))
            svc = m.group(2)
            out[svc] = {"image": "", "ports": [], "volumes": []}
            key = None
            continue
        if svc is None:
            continue
        m = re.match(r"^\s+image:\s*(\S.*)$", line)
        if m:
            out[svc]["image"] = m.group(1).strip().strip("'\"")
            key = None
            continue
        if re.match(r"^\s+build[:\s]", line) and not out[svc]["image"]:
            out[svc]["image"] = "(built from ./Dockerfile)"
        m = re.match(r"^\s+(ports|volumes):\s*$", line)
        if m:
            key = m.group(1)
            continue
        m = re.match(r"^\s+-\s*(\S.*)$", line)
        if m and key:
            out[svc][key].append(m.group(1).strip().strip("'\""))
            continue
        if re.match(r"^\s+[A-Za-z0-9._-]+:", line):
            key = None
    return out


def parse_env_example(path):
    names = []
    if not path.exists():
        return names
    for line in path.read_text().splitlines():
        m = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=", line)
        if m and m.group(1) not in names:
            names.append(m.group(1))
    return names


# ---------------------------------------------------------------- catalog


def load_catalog():
    """Optional configs/docker-stack/service-catalog.yaml enrichment."""
    if not CATALOG.exists():
        return {}
    try:
        text = CATALOG.read_text()
        if HAVE_YAML:
            data = yaml.safe_load(text) or {}
        else:
            return {}
        # accept either {services: {name: {...}}} or {name: {...}}
        services = data.get("services", data)
        return services if isinstance(services, dict) else {}
    except Exception as exc:  # tolerate a malformed/partial catalog
        print(f"[gen-wiki-services] WARN: could not read {CATALOG}: {exc}", file=sys.stderr)
        return {}


# ---------------------------------------------------------------- discover


def discover():
    stacks = []
    patterns = [
        (REPO / "configs" / "docker-stack" / "stacks", "compose.yaml", "mini"),
        (REPO / "configs" / "docker-stack", "docker-compose.yml", "mini"),
        (REPO / "configs" / "nas", "docker-compose.yml", "nas"),
    ]
    for base, fname, host in patterns:
        if not base.is_dir():
            continue
        for d in sorted(base.iterdir()):
            if not d.is_dir() or d.name in ("stacks", "alternatives"):
                continue
            f = d / fname
            if f.exists():
                h = "nas" if d.name.endswith("-nas") else host
                stacks.append({"name": d.name, "path": f, "host": h})
    return stacks


# ---------------------------------------------------------------- render


def render_page(st, catalog):
    name, path, host = st["name"], st["path"], st["host"]
    text = path.read_text()
    desc, doc_urls = parse_header(text)
    services = parse_compose_yaml(text) if HAVE_YAML else parse_compose_regex(text)
    env_names = parse_env_example(path.parent / ".env.example")
    cat_entry = catalog.get(name, {}) if isinstance(catalog.get(name, {}), dict) else {}

    if "url" in cat_entry:
        url = cat_entry["url"]
    elif name in URL_OVERRIDES:
        url = URL_OVERRIDES[name]
    else:
        url = f"https://{name}.tabaska.us"
    desc = cat_entry.get("description", desc) or name
    rel = path.relative_to(REPO)

    lines = [
        f"# {name}",
        "",
        f"{desc}",
        "",
        "| | |",
        "|---|---|",
        f"| **Host** | [{host}](../hosts/{'mini' if host == 'mini' else 'nas'}.md) |",
        f"| **URL** | {url if url else '— (no web UI / not proxied)'} |",
        f"| **Source** | `foss-setup/{rel}` |",
    ]
    if doc_urls:
        links = " · ".join(f"<{u}>" for u in doc_urls)
        lines.append(f"| **Upstream docs** | {links} |")
    lines += ["", "## Containers", ""]
    lines += ["| Service | Image (pinned) | Ports |", "|---|---|---|"]
    for sname in services:
        svc = services[sname]
        img = svc["image"] or "—"
        ports = ", ".join(f"`{p}`" for p in svc["ports"]) or "—"
        lines.append(f"| `{sname}` | `{img}` | {ports} |")

    vol_rows = [(s, v) for s in services for v in services[s]["volumes"]]
    if vol_rows:
        lines += ["", "## Volumes", ""]
        lines += ["| Service | Volume |", "|---|---|"]
        for s, v in vol_rows:
            lines.append(f"| `{s}` | `{v}` |")

    if env_names:
        lines += [
            "",
            "## Environment (`.env`)",
            "",
            "Variable names from `.env.example` — real values live in `.env` on "
            "the host, sourced from the vault (never committed):",
            "",
        ]
        lines += [f"- `{n}`" for n in env_names]

    lines += [
        "",
        "## Operations",
        "",
        "```bash",
    ]
    if host == "mini":
        lines += [
            f"ssh mini 'cd /opt/stacks/{name} && docker compose ps'",
            f"ssh mini 'cd /opt/stacks/{name} && docker compose logs --tail 50'",
            f"ssh mini 'cd /opt/stacks/{name} && docker compose pull && docker compose up -d'",
        ]
    else:
        lines += [
            f"# NAS stack — manage via DSM Container Manager (project: {name})",
            f"# or over SSH (sudo required): cd /volume1/docker/{name} && sudo docker compose ps",
        ]
    lines += [
        "```",
        "",
        "Update procedure: [Runbooks → Update images](../runbooks/update-images.md). "
        "Full add/change loop: [Runbooks → Add a service](../runbooks/add-a-service.md).",
        "",
        "*Generated by `scripts/docs/gen-wiki-services.py` — do not edit by hand; "
        "edit the compose file and regenerate.*",
        "",
    ]
    return "\n".join(lines)


def category_of(name, catalog):
    entry = catalog.get(name)
    if isinstance(entry, dict) and entry.get("category"):
        return str(entry["category"])
    for cat, names in CATEGORIES.items():
        if name in names:
            return cat
    return FALLBACK_CATEGORY


def render_index(stacks, catalog, by_cat):
    lines = [
        "# Services",
        "",
        f"{len(stacks)} compose stacks, generated from the repo "
        "(`configs/docker-stack/` and `configs/nas/`) by "
        "`scripts/docs/gen-wiki-services.py`. If a page here disagrees with a "
        "compose file, regenerate — the compose file wins.",
        "",
    ]
    for cat in sorted(by_cat):
        lines += [f"## {cat}", ""]
        lines += ["| Stack | Host | URL |", "|---|---|---|"]
        for st in by_cat[cat]:
            name = st["name"]
            entry = catalog.get(name, {}) if isinstance(catalog.get(name, {}), dict) else {}
            url = entry.get("url", URL_OVERRIDES.get(name, f"https://{name}.tabaska.us"))
            url = url if url else "—"
            lines.append(f"| [{name}]({name}.md) | {st['host']} | {url} |")
        lines.append("")
    lines += [
        "Not compose-managed (so not listed above): **Plex** (native NAS "
        "package), **slskd + Deluge** (seedbox, provider-managed/native — see "
        "[seedbox](../hosts/seedbox.md)), **Forgejo** (runs from `/opt/stacks` "
        "on the mini).",
        "",
        "*Generated — do not edit by hand.*",
        "",
    ]
    return "\n".join(lines)


def update_nav(by_cat):
    begin = "      # BEGIN GENERATED SERVICES NAV (managed by scripts/docs/gen-wiki-services.py — do not edit by hand)"
    end = "      # END GENERATED SERVICES NAV"
    text = MKDOCS_YML.read_text()
    b, e = text.find(begin), text.find(end)
    if b < 0 or e < 0:
        print("[gen-wiki-services] WARN: nav markers not found in mkdocs.yml — nav not updated", file=sys.stderr)
        return
    block = [begin, "      - Overview: services/index.md"]
    for cat in sorted(by_cat):
        block.append(f"      - {cat}:")
        for st in by_cat[cat]:
            block.append(f"          - {st['name']}: services/{st['name']}.md")
    new = text[:b] + "\n".join(block) + "\n" + text[e:]
    MKDOCS_YML.write_text(new)


def main():
    catalog = load_catalog()
    stacks = discover()
    if not stacks:
        print("[gen-wiki-services] ERROR: no stacks found", file=sys.stderr)
        return 1
    WIKI_DOCS.mkdir(parents=True, exist_ok=True)

    by_cat = {}
    for st in stacks:
        by_cat.setdefault(category_of(st["name"], catalog), []).append(st)
    for cat in by_cat:
        by_cat[cat].sort(key=lambda s: s["name"])

    # drop stale generated pages
    expected = {f"{st['name']}.md" for st in stacks} | {"index.md"}
    for f in WIKI_DOCS.glob("*.md"):
        if f.name not in expected:
            f.unlink()

    for st in stacks:
        (WIKI_DOCS / f"{st['name']}.md").write_text(render_page(st, catalog))
    (WIKI_DOCS / "index.md").write_text(render_index(stacks, catalog, by_cat))
    update_nav(by_cat)

    yaml_mode = "PyYAML" if HAVE_YAML else "regex-fallback"
    cat_mode = "catalog" if catalog else "built-in categories (no service-catalog.yaml)"
    print(f"[gen-wiki-services] {len(stacks)} stacks -> {WIKI_DOCS} ({yaml_mode}, {cat_mode})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
