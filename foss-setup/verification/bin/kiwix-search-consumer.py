#!/usr/bin/env python3
"""kiwix-search-consumer.py — CONSUMER-END probe for the NAS Kiwix ZIM library (lai-12).

Liveness lies twice here: the container answers 200 with an EMPTY library (library.xml
rebuild failed / /volume1/zim unmounted — kiwix-serve cannot hot-add ZIMs, the nightly
DSM refresh task owns the XML), and it answers 200 while search is broken for the books
people actually use. So this proves, from the mini over the LAN, the exact path a human
(kiwix.tabaska.us) or the AI stack (openzim-mcp, lai-13) takes:

  1. LIBRARY BREADTH — the OPDS catalog (/catalog/v2/entries?count=-1) must list at
     least MIN_BOOKS books (10; the first download tranche alone lands ~21). Catches
     the empty/half-wired library modes.
  2. SEARCH — adaptive to WHATEVER HAS LANDED (the library grows for days while the
     115G Wikipedia maxi trickles in; the check must stay green throughout):
       - The catalog entries carry each book's <name> and URL basename (from the
         /content/<base> link — /search books.name and /suggest content both want the
         BASENAME on this server, not the metadata name).
       - The probe runs a REAL fulltext /search on the first PRESENT book from
         FT_CANDIDATES (iFixit first — tranche-1 with a working Xapian index),
         falling through the list until one yields results. Detection is
         BEHAVIOR-based on purpose: the `_ftindex:` catalog tag is unreliable
         metadata (measured 2026-08-06: every book reports `_ftindex:no`, including
         iFixit/StackExchange whose embedded Xapian search demonstrably works —
         while the devdocs ZIMs genuinely have no fulltext index).
       - Fallback (no candidate landed / none searchable): the title-index /suggest
         endpoint on a devdocs book — still end-to-end (index -> path -> content),
         emits mode=suggest so a degraded library is visible in check output.
  3. FETCH — follows the first result to /content/... and requires the search term in
     the served article body: content serving proven, not just the index.

Timeouts are generous: the DS920+ answers slowly under sequential-download I/O.
"""

import re
import sys
import urllib.parse
import urllib.request

BASE = "http://192.168.10.4:8092"
MIN_BOOKS = 10
MIN_ARTICLE_BYTES = 1000

# (name-prefix, search pattern, must-contain term) — first PRESENT book that
# yields search results wins.
FT_CANDIDATES = [
    ("ifixit_en_all", "battery replacement", "battery"),
    ("serverfault.com_en", "ssh", "ssh"),
    ("unix.stackexchange.com_en", "ssh", "ssh"),
    ("superuser.com_en", "ssh", "ssh"),
    ("wiktionary_en", "linux", "linux"),
    ("wikipedia_en", "linux", "linux"),
]
SUGGEST_FALLBACK = ("devdocs_en_docker", "compose", "compose")


def get(path, timeout=60):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "fleet-verification"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def bad(msg):
    print("KIWIX_BAD " + msg)
    sys.exit(1)


def parse_catalog(cat):
    """-> list of dicts {name, base} in catalog order."""
    books = []
    for blk in re.findall(r"<entry>(.*?)</entry>", cat, re.S):
        m_name = re.search(r"<name>([^<]*)</name>", blk)
        m_base = re.search(r'href="/content/([^"/]+)"', blk)
        if m_name and m_base:
            books.append({"name": m_name.group(1), "base": m_base.group(1)})
    return books


def fetch_article(href, term):
    if href.startswith("/viewer#"):
        href = "/content/" + href[len("/viewer#"):]
    href = urllib.parse.quote(href, safe="/:#?=&%")
    try:
        art = get(href)
    except Exception as e:  # noqa: BLE001
        bad("article_fetch_failed url=%r err=%r" % (href, e))
    if len(art) < MIN_ARTICLE_BYTES or term not in art.lower():
        bad("article_content_bad url=%r bytes=%d term=%r present=%s"
            % (href, len(art), term, term in art.lower()))
    return len(art)


def try_search(base, pattern):
    """-> list of result hrefs (may be empty); None on transport error."""
    q = "/search?books.name=%s&pattern=%s&pageLength=10" % (
        base, urllib.parse.quote(pattern))
    try:
        html = get(q)
    except Exception:  # noqa: BLE001 - caller decides; 400 = book not searchable
        return None
    links = re.findall(r'href="([^"]+)"', html)
    return [l for l in links
            if ("/content/" in l or l.startswith("/viewer#")) and base in l]


def main():
    try:
        cat = get("/catalog/v2/entries?count=-1")
    except Exception as e:  # noqa: BLE001 - any transport failure is the finding
        bad("catalog_unreachable err=%r" % (e,))
    books = parse_catalog(cat)
    if len(books) < MIN_BOOKS:
        bad("library_too_small books=%d min=%d" % (len(books), MIN_BOOKS))
    by_prefix = lambda p: next((b for b in books if b["name"].startswith(p)), None)  # noqa: E731

    tried = []
    for prefix, pattern, term in FT_CANDIDATES:
        b = by_prefix(prefix)
        if not b:
            continue
        results = try_search(b["base"], pattern)
        if results:
            n = fetch_article(results[0], term)
            print("KIWIX_OK books=%d mode=search book=%s results=%d art_bytes=%d"
                  % (len(books), b["base"], len(results), n))
            return
        tried.append(b["base"])

    if tried:
        # fulltext books ARE present but none returned results — that is a finding,
        # not a reason to degrade to the title index.
        bad("search_no_results tried=%s" % ",".join(tried))

    # no fulltext candidate landed yet — title-index suggest on a devdocs book
    prefix, sterm, term = SUGGEST_FALLBACK
    b = by_prefix(prefix) or books[0]
    try:
        sug = get("/suggest?content=%s&term=%s" % (b["base"], urllib.parse.quote(sterm)))
    except Exception as e:  # noqa: BLE001
        bad("suggest_unreachable book=%s err=%r" % (b["base"], e))
    paths = re.findall(r'"path"\s*:\s*"([^"]+)"', sug)
    if not paths:
        bad("suggest_no_results book=%s body=%r" % (b["base"], sug[:160]))
    n = fetch_article("/content/%s/%s" % (b["base"], paths[0]), term)
    print("KIWIX_OK books=%d mode=suggest book=%s results=%d art_bytes=%d"
          % (len(books), b["base"], len(paths), n))


if __name__ == "__main__":
    main()
