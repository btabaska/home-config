#!/usr/bin/env python3
"""gen-wiki-services.py — generate wiki service pages from compose files (wiki-02).

Walks every compose stack in the repo:

  configs/docker-stack/stacks/*/<compose file>    -> host: mini (adguard-nas -> nas)
  configs/nas/*/<compose file>                    -> host: nas

(<compose file> = compose.yaml | compose.yml | docker-compose.yml, first match —
mirrors keep each stack's live filename, e.g. forgejo + wallabag use
docker-compose.yml/compose.yaml respectively.)

and emits one Markdown man-page per stack into wiki/docs/services/, plus a
generated services/index.md grouped by category, plus the nav block in
wiki/mkdocs.yml (between the BEGIN/END GENERATED SERVICES NAV markers).

Facts per stack: image + pin per service, host, ports, canonical URL
(https://<name>.tabaska.us convention, with known overrides), env var NAMES
from .env.example (never values), volumes, upstream doc links parsed from the
compose header comment.

Enrichment: if configs/docker-stack/service-catalog.yaml exists, its
category/url/description/notes fields override the built-in maps, and two
optional prose fields render extra sections (absence is fine):
  about:       prose block  -> "## About"  (after the metadata table)
  troubleshoot: list of {symptom, fix} (or strings) -> "## Troubleshooting"
                (after Environment, before Operations)

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
ENRICH = REPO / "configs" / "docker-stack" / "service-enrichment.yaml"

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
    "immich": "https://immich.tabaska.us (LAN: http://192.168.10.4:2283)",
    "calibre-web-automated": "http://192.168.10.4:8083 (deliberately LAN/VPN-only)",
    "libreseerr": "https://libreseerr.tabaska.us (LAN: http://192.168.10.2:8789)",
    "media-automation": None,  # multi-app stack; per-service ports below
    "vaultwarden": "https://vault.tabaska.us",
    "forgejo": "https://git.tabaska.us",
    "beszel": "https://status.tabaska.us",
    "healthchecks": "https://health.tabaska.us",
    "amp": "https://amp.tabaska.us",
    "palworld": None,   # game server (UDP; public path via playit) — no web UI
    "playit": None,     # tunnel agent
    "bedrock-connect": None,  # UDP 19132 console gateway
    "bgutil-pot": None,  # PO-token sidecar for metube/pinchflat
}

CATEGORIES = {
    "Networking & Access": ["caddy", "adguard", "adguard-nas", "unbound"],
    "Media & Acquisition": [
        "seerr", "musicseerr", "libreseerr", "media-automation", "tautulli",
        "kometa", "recyclarr", "pinchflat", "stash",
    ],
    "Photos & Reading": [
        "immich", "calibre-web-automated", "miniflux", "wallabag", "navidrome",
    ],
    "Documents & Life": ["paperless-ngx", "mealie"],
    "Monitoring & Ops": [
        "homepage", "uptime-kuma", "beszel", "ntfy", "diun", "healthchecks",
        "dockge", "vaultwarden",
    ],
    "AI & Cameras": ["frigate"],
}
FALLBACK_CATEGORY = "Uncategorized"

# ------------------------------------------------------------ compose parse


STATUS_RE = re.compile(r"^(REMOVED FROM PLAN|RETIRED|NOT DEPLOYED|DEPRECATED)\b", re.I)


def parse_header(text):
    """First comment block -> (status, description, [doc urls]).

    A leading REMOVED FROM PLAN / RETIRED / NOT DEPLOYED / DEPRECATED line is
    the stack's status banner, kept separate so the page still gets the real
    one-line description underneath it.
    """
    status, desc, urls = "", "", []
    for line in text.splitlines():
        if not line.startswith("#"):
            if line.strip():
                break
            continue
        body = line.lstrip("#").strip()
        if not status and not desc and STATUS_RE.match(body):
            status = body
            continue
        if not desc and re.search(r"[A-Za-z]", body):
            desc = body
        urls += [
            u for u in re.findall(r"https?://[^\s)\"']+", body)
            if "<" not in u and "{" not in u  # skip placeholder hosts
        ]
    # de-dup, keep order
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return status, desc, out[:3]


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


def _read_services_yaml(path):
    """Parse a {services: [{name:..}]} / {services: {name:{}}} / {name:{}} file
    into a {name: {...}} dict. Returns {} on any problem."""
    if not path.exists() or not HAVE_YAML:
        return {}
    try:
        data = yaml.safe_load(path.read_text()) or {}
        services = data.get("services", data)
        if isinstance(services, list):
            services = {
                e["name"]: e for e in services if isinstance(e, dict) and e.get("name")
            }
        return services if isinstance(services, dict) else {}
    except Exception as exc:  # tolerate a malformed/partial file
        print(f"[gen-wiki-services] WARN: could not read {path}: {exc}", file=sys.stderr)
        return {}


def load_catalog():
    """Merge service-catalog.yaml (homepage-surface facts) with the optional
    sibling service-enrichment.yaml (wiki prose: about / troubleshoot, keyed by
    STACK name). Enrichment fields win / add; a stack absent from the catalog but
    present in enrichment still gets an entry."""
    services = _read_services_yaml(CATALOG)
    for name, extra in _read_services_yaml(ENRICH).items():
        if isinstance(services.get(name), dict) and isinstance(extra, dict):
            services[name] = {**services[name], **extra}
        elif isinstance(extra, dict):
            services[name] = extra
    return services


# ---------------------------------------------------------------- discover


def discover():
    stacks = []
    # Mirrors keep each stack's LIVE compose filename (compose.yaml vs
    # docker-compose.yml differs per stack — forgejo/wallabag use the latter),
    # so try the standard names in order rather than fixing one per tree.
    # fix-41 folded the former special-case locations (configs/git/forgejo,
    # configs/docker-stack/wallabag) into configs/docker-stack/stacks/.
    compose_names = ("compose.yaml", "compose.yml", "docker-compose.yml")
    patterns = [
        (REPO / "configs" / "docker-stack" / "stacks", "mini"),
        (REPO / "configs" / "nas", "nas"),
        (REPO / "configs" / "gaming", "rig"),
    ]
    seen = set()
    for base, host in patterns:
        if not base.is_dir():
            continue
        for d in sorted(base.iterdir()):
            if not d.is_dir() or d.name == "alternatives":
                continue
            # One page per stack NAME; first tree wins (stacks/ before nas/), so
            # the NAS's own diun mirror doesn't stomp the mini diun page.
            if d.name in seen:
                continue
            f = next((d / n for n in compose_names if (d / n).exists()), None)
            if f is not None:
                h = "nas" if d.name.endswith("-nas") else host
                seen.add(d.name)
                stacks.append({"name": d.name, "path": f, "host": h})
    return stacks


# ---------------------------------------------------------------- render


def render_page(st, catalog):
    name, path, host = st["name"], st["path"], st["host"]
    text = path.read_text()
    status, desc, doc_urls = parse_header(text)
    services = parse_compose_yaml(text) if HAVE_YAML else parse_compose_regex(text)
    env_names = parse_env_example(path.parent / ".env.example")
    cat_entry = catalog.get(name, {}) if isinstance(catalog.get(name, {}), dict) else {}

    # The catalog describes the LIVE deployment; for a stack that is not
    # deployed (status banner), the dir location is the only truth we have.
    if not status and cat_entry.get("host"):
        host = str(cat_entry["host"])

    if status:
        url = None  # a not-deployed/removed stack has no live URL
    elif "url" in cat_entry:
        url = cat_entry["url"]
    elif name in URL_OVERRIDES:
        url = URL_OVERRIDES[name]
    else:
        url = f"https://{name}.tabaska.us"
    desc = cat_entry.get("description", desc) or name
    rel = path.relative_to(REPO)

    lines = [f"# {name}", ""]
    if status:
        lines += [f"**{status}**", ""]
    host_link = f"[{host}](../hosts/{host}.md)" if host in ("mini", "nas", "rig") else host
    lines += [
        f"{desc}",
        "",
        "| | |",
        "|---|---|",
        f"| **Host** | {host_link} |",
        f"| **URL** | {url if url else '— (no web UI / not proxied)'} |",
        f"| **Source** | `foss-setup/{rel}` |",
    ]
    if cat_entry.get("notes"):
        lines.append(f"| **Notes** | {cat_entry['notes']} |")
    if doc_urls:
        links = " · ".join(f"<{u}>" for u in doc_urls)
        lines.append(f"| **Upstream docs** | {links} |")

    about = cat_entry.get("about")
    if about:
        lines += ["", "## About", "", str(about).strip()]

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

    troubleshoot = cat_entry.get("troubleshoot")
    if troubleshoot:
        lines += ["", "## Troubleshooting", ""]
        if isinstance(troubleshoot, list):
            for item in troubleshoot:
                if isinstance(item, dict):
                    sym = str(item.get("symptom", "")).strip()
                    fix = str(item.get("fix", "")).strip()
                    lines.append(f"- **{sym}** — {fix}" if sym else f"- {fix}")
                else:
                    lines.append(f"- {str(item).strip()}")
        else:
            lines.append(str(troubleshoot).strip())

    lines += [
        "",
        "## Operations",
        "",
        "```bash",
    ]
    if host in ("mini", "rig"):
        dc = "sudo docker compose" if host == "rig" else "docker compose"
        lines += [
            f"ssh {host} 'cd /opt/stacks/{name} && {dc} ps'",
            f"ssh {host} 'cd /opt/stacks/{name} && {dc} logs --tail 50'",
            f"ssh {host} 'cd /opt/stacks/{name} && {dc} pull && {dc} up -d'",
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
        "(`configs/docker-stack/stacks/`, `configs/nas/`, `configs/gaming/`) by "
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
            status = st.get("status", "")
            if status:
                m = STATUS_RE.match(status)
                marker = f" *({m.group(1).lower()})*" if m else ""
                url = "—"
                host = st["host"]
            else:
                marker = ""
                if "url" in entry:
                    url = entry["url"]
                elif name in URL_OVERRIDES:
                    url = URL_OVERRIDES[name]
                else:
                    url = f"https://{name}.tabaska.us"
                url = url or "—"
                host = entry.get("host", st["host"])
            lines.append(f"| [{name}]({name}.md){marker} | {host} | {url} |")
        lines.append("")
    lines += [
        "Not compose-managed in this repo (so not listed above): **Plex** "
        "(native NAS package), **slskd + Deluge** (seedbox — see "
        "[seedbox](../hosts/seedbox.md)), and the **rig AI stack** (litellm, "
        "open-webui, mcpo — compose lives in the separate `local-ai-tooling` "
        "repo; see [rig](../hosts/rig.md)).",
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
        st["status"], _, _ = parse_header(st["path"].read_text())
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
