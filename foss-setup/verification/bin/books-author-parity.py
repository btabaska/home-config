#!/usr/bin/env python3
"""books-author-parity — bmig-06 C1/C4-class regression tripwire.

The 2026-07-20 books incident (program doc books-metadata-cutover-2026-07-20.md)
was, at its core, requests silently binding to records by the WRONG author:
the goodreads-era metadata returned junk candidates (C1) and libreseerr's
candidate walker stamped the requested author onto whatever it could add (C4).
The bmig-04 author gate prevents that at request time; this check proves the
outcome nightly at the consumer end — every stored non-error request's bound
Bookshelf record must still have an author that matches the request.

Match rule (mirrors the gate's spirit, one-directional for monitoring):
  1. token match — meaningful (len>=2, diacritic-folded) name tokens of one
     side are a subset of the other ("J.R.R. Tolkien" ~ "JRR Tolkien"), else
  2. alias pass — every requested-name token appears in the bound author's
     hardcover bio/overview (Feed: requested "Seanan McGuire", bound author
     "Mira Grant", whose bio names McGuire).

Requests older than BACKEND_CUTOVER reference retired-readarr book ids and are
skipped (same constant as request-layer-audit.py). Missing books (404) are
skipped here — request-layer-audit's false-complete rot check owns that class.

Backend URL/key come from libreseerr's own config (the consumer's view), like
request-layer-audit.py.

Usage: books-author-parity.py [--requests-file PATH]   (override = test hook)
Prints AUTHOR_PARITY_OK ... or AUTHOR_PARITY_BAD ... / CONFIG_ERR ...
"""
import argparse
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.request

LIBRESEERR_CONFIG = "/opt/stacks/libreseerr/data/config.json"
DEFAULT_REQUESTS = "/opt/stacks/libreseerr/data/requests.json"
BACKEND_CUTOVER = "2026-07-20T19:30:00"  # keep in sync with request-layer-audit.py


def tokens(name: str) -> frozenset:
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return frozenset(t for t in re.findall(r"[a-z0-9]+", s.lower()) if len(t) >= 2)


def api_or_404(base, key, path):
    req = urllib.request.Request(f"{base}/api/v1{path}", headers={"X-Api-Key": key})
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--requests-file", default=DEFAULT_REQUESTS)
    args = ap.parse_args()

    try:
        cfg = json.load(open(LIBRESEERR_CONFIG)).get("ebook") or {}
        base, key = cfg.get("url"), cfg.get("api_key")
    except Exception as e:  # noqa: BLE001
        print(f"CONFIG_ERR cannot read libreseerr backend config: {e}")
        return 2
    if not (base and key):
        print("CONFIG_ERR libreseerr ebook backend not configured")
        return 2
    try:
        reqs = json.load(open(args.requests_file))
    except Exception as e:  # noqa: BLE001
        print(f"CONFIG_ERR cannot read requests file: {e}")
        return 2

    authors: dict = {}  # authorId -> author record (cached across requests)
    bad, checked, legacy, gone = [], 0, 0, 0
    for r in reqs:
        book_id = r.get("readarr_book_id")
        requested = r.get("author") or ""
        if not book_id or r.get("status") == "error" or not requested:
            continue
        if (r.get("created_at") or "") < BACKEND_CUTOVER:
            legacy += 1
            continue
        book = api_or_404(base, key, f"/book/{book_id}")
        if book is None:
            gone += 1  # request-layer-audit owns false-complete rot
            continue
        checked += 1
        aid = book.get("authorId") or (book.get("author") or {}).get("id")
        if aid not in authors:
            authors[aid] = (api_or_404(base, key, f"/author/{aid}") or {}) if aid else {}
        bound = authors[aid].get("authorName") or book.get("authorTitle") or ""
        want, have = tokens(requested), tokens(bound)
        if want and have and (want <= have or have <= want):
            continue
        if want and want <= tokens(authors[aid].get("overview") or ""):
            continue
        title = r.get("title") or "?"
        bad.append(f"{title}(requested={requested} bound={bound or '?'})")

    if bad:
        print(f"AUTHOR_PARITY_BAD {len(bad)}: " + "; ".join(sorted(bad)))
        return 1
    print(f"AUTHOR_PARITY_OK checked={checked} legacy_skipped={legacy} gone={gone}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
