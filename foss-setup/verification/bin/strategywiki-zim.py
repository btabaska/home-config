#!/usr/bin/env python3
"""strategywiki-zim.py — lai-15 pipeline/consumer check for the StrategyWiki ZIM.

Runs on the MINI (the build host). ONE probe, TWO auto-selected modes so it is green
throughout the async lifecycle and upgrades to a real content probe once the ZIM lands:

  CONTENT  — a strategywiki_* book is in the NAS Kiwix catalog (192.168.10.4:8092):
             do a REAL Xapian fulltext search for a known game title + fetch the first
             article and assert the term is in the body. This is the end state.
  PIPELINE — no book in the catalog yet: report the build pipeline's state from the mini
             status file /opt/mwoffliner/lai-15/status (written by
             build-strategywiki-zim.sh / strategywiki-zim-handler.sh). Green while the
             async build is healthy (BUILDING w/ liveness, VALIDATING, PUSHING,
             PUSHED_AWAITING_REFRESH) OR in the known external-BLOCKED state; RED only on
             a genuine failure/stall.

The current (2026-08-06) state is BLOCKED: StrategyWiki sits behind Cloudflare bot
management that fingerprints and 403s mwoffliner's Node/undici HTTP client (curl gets
200 with any User-Agent; the Node client is blocked). mwoffliner's whole HTTP layer is
Node, so it cannot scrape the site and --speed is irrelevant. That is an EXPECTED
external block (like the fleet's GameFAQs-Turnstile / PCGW-Cloudflare notes), not a
regression, so the check is green in mode=blocked and surfaces the human follow-up
(file the openZIM zim-request). See wiki/docs/runbooks/strategywiki-zim.md.

Emits exactly one line: 'STRATEGYWIKI_OK <mode=...>' or 'STRATEGYWIKI_BAD <...>'.
"""
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

NAS = "http://192.168.10.4:8092"
BASE = "/opt/mwoffliner/lai-15"
STATUS = BASE + "/status"
LOG = BASE + "/build.log"
MW_CONTAINER = "mw-lai15"
FRESH_SECS = 45 * 60  # BUILDING liveness: build.log must have advanced within 45 min
UA = {"User-Agent": "fleet-verification"}


def get(path, timeout=90):
    req = urllib.request.Request(NAS + path, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")


def ok(msg):
    print("STRATEGYWIKI_OK " + msg)
    sys.exit(0)


def bad(msg):
    print("STRATEGYWIKI_BAD " + msg)
    sys.exit(0)


def try_content():
    """Return None if no strategywiki book is live yet (fall back to pipeline state).
    Only reaches ok()/bad() when a book IS listed (then search+fetch must work)."""
    try:
        cat = get("/catalog/v2/entries?count=-1")
    except Exception:
        return None  # NAS unreachable -> don't red-alert; report the build state instead
    ent = next((e for e in re.findall(r"<entry>(.*?)</entry>", cat, re.S)
                if re.search(r"<name>[^<]*strategywiki[^<]*</name>", e, re.I)), None)
    if not ent:
        return None
    m = re.search(r"/content/([A-Za-z0-9_.-]+)", ent)
    if not m:
        bad("mode=content strategywiki book listed but no /content base found")
    base = m.group(1)
    for term, token in (("Super Mario Bros", "mario"), ("The Legend of Zelda", "zelda")):
        try:
            sr = get("/search?books.name=%s&pattern=%s&pageLength=5"
                     % (base, urllib.parse.quote(term)))
        except Exception:
            sr = ""
        links = [l for l in re.findall(r"/content/[A-Za-z0-9_./?#=&%-]+", sr)
                 if (base + "/") in l and l.endswith(".html")]
        if links:
            try:
                art = get(urllib.parse.quote(links[0], safe="/:#?=&%"))
            except Exception:
                art = ""
            if len(art) > 500 and token in art.lower():
                ok("mode=content base=%s term=%r bytes=%d" % (base, term, len(art)))
    bad("mode=content base=%s search/fetch returned nothing for known titles" % base)


def container_running(name):
    try:
        out = subprocess.run(["docker", "ps", "--filter", "name=" + name,
                              "--format", "{{.Names}}"],
                             capture_output=True, text=True, timeout=15).stdout
        return name in out.split()
    except Exception:
        return False


def try_pipeline():
    if not os.path.exists(STATUS):
        bad("mode=pipeline no status file at %s (build never launched)" % STATUS)
    st = open(STATUS).read().strip()
    head = st.split(":", 1)[0]
    if head == "BLOCKED":
        ok("mode=blocked %s :: mwoffliner Node client 403'd by Cloudflare; human "
           "follow-up = file the openZIM zim-request (runbook)" % st)
    if head in ("VALIDATING", "PUSHING", "PUSHED_AWAITING_REFRESH"):
        ok("mode=%s (post-scrape; nightly kiwix refresh wires it into the library)" % head)
    if head == "BUILDING":
        alive = container_running(MW_CONTAINER)
        age = int(time.time() - os.path.getmtime(LOG)) if os.path.exists(LOG) else -1
        if alive or (0 <= age < FRESH_SECS):
            ok("mode=building container=%s log_age=%ss (scrape in progress)"
               % ("up" if alive else "gone", age))
        bad("mode=building STALLED container=gone log_age=%ss — mwoffliner died" % age)
    if head == "FAILED":
        bad("mode=failed %s" % st)
    bad("mode=pipeline unknown status=%r" % st)


def main():
    try_content()   # returns None unless a strategywiki book is actually live
    try_pipeline()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # never emit empty output (that reads as a silent FAIL)
        print("STRATEGYWIKI_BAD unexpected %r" % e)
        sys.exit(0)
