#!/usr/bin/env python3
"""gen-script-pages.py — generate wiki man-pages from scripts/ (wiki build-out).

Walks scripts/**/*.{sh,py} and emits one SMALL, linked Markdown man-page per
script into wiki/docs/reference/scripts/<category>/<name>.md, plus a per-category
index and a top scripts index, plus the nav block in mkdocs.yml (between the
BEGIN/END GENERATED SCRIPTS NAV markers).

Design goals (operator, 2026-07-14): pages small enough for a local LLM's context,
DENSELY linked so an agent can traverse to what it needs. Each page = NAME / role,
PATH, SYNOPSIS (usage line), WHAT IT DOES (header comment), ENV (referenced vars),
SEE ALSO (sibling scripts + category + repo path). Deterministic — re-running on a
clean tree yields no diff.

Usage: python3 foss-setup/scripts/docs/gen-script-pages.py
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "scripts"
OUT = REPO / "wiki" / "docs" / "reference" / "scripts"
MKDOCS = REPO / "wiki" / "mkdocs.yml"

CAT_TITLES = {
    "backup": "Backup & restore", "docs": "Docs & tracker generators",
    "dotfiles": "Dotfiles", "gaming": "Gaming & streaming", "ha": "Home Assistant",
    "inventory": "Inventory & manifests", "media": "Media pipeline", "nas": "NAS tasks",
    "network": "Network", "reading": "Reading stack", "setup": "Host setup",
    "uptime-kuma": "Uptime Kuma",
}


def header_block(text, is_py):
    """Extract the leading comment/docstring block as (summary, body_lines)."""
    lines = text.splitlines()
    body = []
    if is_py:
        m = re.search(r'"""(.*?)"""', text, re.S)
        if m:
            body = [l.rstrip() for l in m.group(1).strip().splitlines()]
        else:
            for l in lines:
                if l.startswith("#!"):
                    continue
                if l.startswith("#"):
                    body.append(l.lstrip("#").rstrip())
                elif l.strip() == "":
                    if body:
                        break
                else:
                    break
    else:
        started = False
        for l in lines:
            if l.startswith("#!"):
                continue
            if l.startswith("#"):
                started = True
                body.append(l.lstrip("#").rstrip())
            elif started and l.strip() == "":
                body.append("")
            elif started:
                break
    # trim
    while body and body[0].strip() == "":
        body.pop(0)
    while body and body[-1].strip() == "":
        body.pop()
    summary = ""
    for b in body:
        s = b.strip()
        if s and not s.startswith("="):
            # "name.sh — summary" or just "summary"
            summary = re.sub(r'^[\w./@-]+\.(sh|py)\s*[—:-]\s*', '', s)
            break
    return summary, body


def usage_line(body, name):
    for i, b in enumerate(body):
        if re.search(r'\b(usage|run)\b\s*:', b, re.I) or b.strip().lower().startswith("usage"):
            u = re.sub(r'^\s*(usage|run)\s*:?\s*', '', b, flags=re.I).strip()
            if u:
                return u
    return ""


def env_vars(text):
    found = set(re.findall(r'\$\{?([A-Z][A-Z0-9_]{2,})\}?', text))
    skip = {"BASH_SOURCE", "PATH", "HOME", "PWD", "IFS", "PYEOF", "EOF"}
    return sorted(v for v in found if v not in skip)[:14]


def slug(p):
    return p.name.replace(".", "-")


def main():
    scripts = sorted(
        [p for p in SRC.rglob("*") if p.suffix in (".sh", ".py") and "__pycache__" not in str(p)],
        key=lambda p: (p.parent.name, p.name),
    )
    by_cat = {}
    for p in scripts:
        by_cat.setdefault(p.parent.name, []).append(p)

    OUT.mkdir(parents=True, exist_ok=True)
    # clean old generated pages
    for old in OUT.rglob("*.md"):
        old.unlink()

    for cat, ps in by_cat.items():
        (OUT / cat).mkdir(parents=True, exist_ok=True)
        for p in ps:
            text = p.read_text(errors="replace")
            is_py = p.suffix == ".py"
            summary, body = header_block(text, is_py)
            usage = usage_line(body, p.name)
            envs = env_vars(text)
            rel = p.relative_to(REPO)
            siblings = [q for q in ps if q != p]
            lines = [f"# `{p.name}`", ""]
            lines.append(f"> {summary}" if summary else "> _(no header summary)_")
            lines += ["", f"**Path:** `foss-setup/{rel}` · **Category:** [{CAT_TITLES.get(cat, cat)}](index.md) · **Type:** {'Python' if is_py else 'Bash'}", ""]
            if usage:
                lines += ["## Synopsis", "", "```", usage, "```", ""]
            lines += ["## What it does", ""]
            if body:
                lines += ["```text"] + body + ["```", ""]
            else:
                lines += ["_No header documentation in the script._", ""]
            if envs:
                lines += ["## Environment / variables referenced", "", ", ".join(f"`{e}`" for e in envs), ""]
            lines += ["## See also", ""]
            if siblings:
                lines += [f"- [`{q.name}`]({slug(q)}.md)" for q in siblings[:12]]
            lines += [f"- [{CAT_TITLES.get(cat, cat)} scripts](index.md) · [All scripts](../index.md)", ""]
            (OUT / cat / f"{slug(p)}.md").write_text("\n".join(lines))
        # per-category index
        idx = [f"# {CAT_TITLES.get(cat, cat)} scripts", "",
               f"`foss-setup/scripts/{cat}/` — {len(ps)} script(s).", "", "| Script | Role |", "|---|---|"]
        for p in ps:
            summary, _ = header_block(p.read_text(errors="replace"), p.suffix == ".py")
            idx.append(f"| [`{p.name}`]({slug(p)}.md) | {summary[:90] or '—'} |")
        idx += ["", "[← All scripts](../index.md)", ""]
        (OUT / cat / "index.md").write_text("\n".join(idx))

    # top scripts index
    top = ["# Scripts reference", "",
           "Man-pages for every operational script in `foss-setup/scripts/`, generated from each "
           "script's own header comment by `scripts/docs/gen-script-pages.py`. Small + linked so a "
           "human — or a local LLM — can traverse to the exact script without loading the whole tree.", "",
           "| Category | Scripts | |", "|---|---|---|"]
    for cat in sorted(by_cat):
        top.append(f"| **{CAT_TITLES.get(cat, cat)}** | {len(by_cat[cat])} | [open]({cat}/index.md) |")
    top += ["", f"_Total: {len(scripts)} scripts across {len(by_cat)} categories._", ""]
    (OUT / "index.md").write_text("\n".join(top))

    # nav injection
    nav = ["      # BEGIN GENERATED SCRIPTS NAV (managed by scripts/docs/gen-script-pages.py — do not edit by hand)",
           "      - Overview: reference/scripts/index.md"]
    for cat in sorted(by_cat):
        nav.append(f"      - {CAT_TITLES.get(cat, cat)}:")
        nav.append(f"          - Index: reference/scripts/{cat}/index.md")
        for p in by_cat[cat]:
            nav.append(f"          - {p.name}: reference/scripts/{cat}/{slug(p)}.md")
    nav.append("      # END GENERATED SCRIPTS NAV")
    navblock = "\n".join(nav)
    y = MKDOCS.read_text()
    if "BEGIN GENERATED SCRIPTS NAV" in y:
        y = re.sub(r"      # BEGIN GENERATED SCRIPTS NAV.*?      # END GENERATED SCRIPTS NAV",
                   navblock, y, flags=re.S)
    else:
        # insert a "Scripts reference" section under Operations (before Operations or at end of nav)
        y = y.rstrip() + "\n  - Scripts reference:\n" + navblock + "\n"
    MKDOCS.write_text(y)
    print(f"generated {len(scripts)} script pages in {len(by_cat)} categories -> {OUT}")


if __name__ == "__main__":
    sys.exit(main())
