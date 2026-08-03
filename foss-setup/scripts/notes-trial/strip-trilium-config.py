#!/usr/bin/env python3
"""Remove the read-27 Trilium artifacts from a Caddyfile / Homepage services.yaml /
verification coverage manifest. Idempotent: if the artifact is already gone, it is a no-op.

Used by teardown-trilium.sh to revert the live config on the mini, but each transform is a
pure text edit so it can be run/tested against the repo mirrors too, e.g.:

    python3 strip-trilium-config.py \\
      --caddyfile configs/docker-stack/stacks/caddy/caddy/Caddyfile \\
      --homepage  configs/docker-stack/stacks/homepage/config/services.yaml \\
      --coverage  verification/coverage/mini.containers \\
      --check                 # report-only, exit 3 if anything still present, write nothing
"""
import argparse
import sys


def strip_caddy(text: str) -> str:
    """Drop the `trilium.{$DOMAIN} { ... }` vhost block plus its comment header and one
    preceding blank separator line. Keyed off the site line and its own closing brace so
    neighbouring blocks are never touched."""
    lines = text.splitlines(keepends=True)
    site = next((k for k, l in enumerate(lines) if l.strip() == "trilium.{$DOMAIN} {"), None)
    if site is None:
        return text
    # walk backwards over the block's own contiguous comment header
    start = site
    k = site - 1
    while k >= 0 and lines[k].lstrip().startswith("#"):
        start = k
        k -= 1
    # drop a single blank separator line above the header
    if start - 1 >= 0 and lines[start - 1].strip() == "":
        start -= 1
    # the closing brace is the first `}` on its own line at/after the site line
    end = next(k for k in range(site, len(lines)) if lines[k].strip() == "}")
    del lines[start:end + 1]
    return "".join(lines)


def strip_homepage(text: str) -> str:
    """Drop the 5-line `- Trilium:` tile block from the Life Apps group."""
    lines = text.splitlines(keepends=True)
    out, i, n = [], 0, len(lines)
    while i < n:
        if lines[i].strip() == "- Trilium:" and "trilium.tabaska.us" in "".join(lines[i:i + 6]):
            base = len(lines[i]) - len(lines[i].lstrip())
            i += 1
            # consume the tile's more-indented child lines
            while i < n and (lines[i].strip() == "" or (len(lines[i]) - len(lines[i].lstrip())) > base):
                i += 1
            continue
        out.append(lines[i])
        i += 1
    return "".join(out)


def strip_coverage(text: str) -> str:
    """Drop the standalone `trilium` container line from a coverage manifest."""
    return "".join(l for l in text.splitlines(keepends=True) if l.strip() != "trilium")


TRANSFORMS = {"caddyfile": strip_caddy, "homepage": strip_homepage, "coverage": strip_coverage}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--caddyfile")
    ap.add_argument("--homepage")
    ap.add_argument("--coverage")
    ap.add_argument("--check", action="store_true",
                    help="report only; write nothing; exit 3 if any artifact remains")
    args = ap.parse_args()

    remaining = False
    for kind in ("caddyfile", "homepage", "coverage"):
        path = getattr(args, kind)
        if not path:
            continue
        try:
            original = open(path).read()
        except FileNotFoundError:
            print(f"  {kind}: {path} not found (skipped)")
            continue
        stripped = TRANSFORMS[kind](original)
        if stripped == original:
            print(f"  {kind}: no Trilium artifact ({path})")
            continue
        if args.check:
            remaining = True
            print(f"  {kind}: Trilium artifact STILL PRESENT ({path})")
        else:
            open(path, "w").write(stripped)
            print(f"  {kind}: Trilium artifact removed ({path})")
    return 3 if (args.check and remaining) else 0


if __name__ == "__main__":
    sys.exit(main())
