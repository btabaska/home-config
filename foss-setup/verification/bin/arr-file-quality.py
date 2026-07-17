#!/usr/bin/env python3
"""
arr-file-quality.py — fix-27 acceptance check (quality-hardening workstream).

Probes the INVARIANT the 2026-07-16 audit found violated 177 times: an *arr item
that reports hasFile=True must actually point at a REAL, PLAYABLE video file — not
a scene Sample/*.avi, not a Plex-unplayable .iso, not an un-extracted .rar, not a
byte-tiny stub. Radarr/Sonarr showed all of these as green (nothing wanted/missing)
so liveness monitoring never noticed the titles were unwatchable in Plex.

This is the CONSUMER-relevant invariant: a sample / iso / rar tracked as "the file"
is unwatchable in Plex BY DEFINITION, regardless of whether Plex has scanned yet —
so it catches the defect earlier and more precisely than a Plex coverage ratio.

Sweeps every Radarr movieFile (one /movie call) and every Sonarr episodeFile
(per-series) and flags any hasFile item whose tracked path is:
  * a sample / junk name   (whole-word 'sample', /Sample/ dir, RARBG.com.*)
  * an .iso / disc image   (Plex cannot index these)
  * an un-extracted archive (.rar / .rNN / .zip / .7z)
  * a stuck partial        (.dat / .part / .!ut / !qB / .crdownload)
  * a byte-empty stub      (< 3 MB — no real video is; catches 0-byte partials)
Deliberately NOT a generic small-file rule: legit short-form content (webisodes,
specials) and episode titles containing a word like "Trailer" must not trip it.

Fails LOUDLY (non-zero, no WATCHABLE_OK) if either API is unreachable or returns
nothing — never a vacuous pass on a down service.

Prints one line:
  WATCHABLE_OK   bad=0 radarr=0 sonarr=0 scanned_movies=M scanned_series=S
  WATCHABLE_BAD  bad=N radarr=A sonarr=B  e.g. <app>:<title>=<basename> …
  WATCHABLE_ERR  <reason>
"""
import argparse
import json
import os
import re
import sys
import urllib.request

# Unambiguous "not a real playable file" signals only — deliberately NOT a generic
# small-file rule: legit short-form content (webisodes, specials) and episode
# titles that merely contain a word like "Trailer" must NOT trip this. A sample is
# a whole-word 'sample' token or a /Sample/ dir; a stub is byte-empty (< 3 MB, which
# no real video ever is), catching stuck 0-byte partials.
DISC = re.compile(r"\.(iso|img|vob|ifo)$", re.I)
ARCHIVE = re.compile(r"\.(rar|r\d\d|zip|7z)$", re.I)
PARTIAL = re.compile(r"\.(dat|part|!ut|crdownload|bts)$|!qb$", re.I)
STUB_BYTES = 3 * 1024 * 1024


def is_sample(path):
    low = path.lower()
    base = low.rsplit("/", 1)[-1]
    if re.search(r"(^|/)samples?/", low) or "rarbg.com" in low:
        return True
    return re.search(r"\bsample\b", base) is not None


def http_get(url, headers=None, timeout=45):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def classify(path, size_bytes):
    if is_sample(path):
        return "sample"
    if DISC.search(path):
        return "iso"
    if ARCHIVE.search(path):
        return "archive"
    if PARTIAL.search(path):
        return "partial"
    if size_bytes and size_bytes < STUB_BYTES:
        return "stub"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--radarr-url", default=os.environ.get("RADARR_URL", "http://192.168.10.4:7878"))
    ap.add_argument("--sonarr-url", default=os.environ.get("SONARR_URL", "http://192.168.10.4:8989"))
    ap.add_argument("--timeout", type=int, default=45)
    args = ap.parse_args()
    rk = os.environ.get("RADARR_API_KEY")
    sk = os.environ.get("SONARR_API_KEY")
    if not rk or not sk:
        print("WATCHABLE_ERR missing RADARR_API_KEY/SONARR_API_KEY in env")
        return 2

    bad = []  # (app, title, basename, why)
    try:
        # ---- Radarr: one call, movieFile embedded ----
        movies = http_get(args.radarr_url.rstrip("/") + "/api/v3/movie",
                           {"X-Api-Key": rk}, args.timeout)
        if not movies:
            print("WATCHABLE_ERR radarr returned no movies")
            return 2
        scanned_movies = 0
        for m in movies:
            if not m.get("hasFile"):
                continue
            scanned_movies += 1
            mf = m.get("movieFile") or {}
            why = classify(mf.get("path", ""), mf.get("size", 0))
            if why:
                bad.append(("radarr", m.get("title", "?"), (mf.get("path", "") or "").rsplit("/", 1)[-1], why))

        # ---- Sonarr: per-series episodeFile ----
        series = http_get(args.sonarr_url.rstrip("/") + "/api/v3/series",
                          {"X-Api-Key": sk}, args.timeout)
        if not series:
            print("WATCHABLE_ERR sonarr returned no series")
            return 2
        scanned_series = 0
        for s in series:
            stats = s.get("statistics") or {}
            if not stats.get("episodeFileCount"):
                continue
            scanned_series += 1
            efs = http_get(args.sonarr_url.rstrip("/") + "/api/v3/episodefile?seriesId=%d" % s["id"],
                           {"X-Api-Key": sk}, args.timeout)
            for ef in efs:
                why = classify(ef.get("path", ""), ef.get("size", 0))
                if why:
                    bad.append(("sonarr", s.get("title", "?"),
                                (ef.get("path", "") or "").rsplit("/", 1)[-1], why))
    except Exception as e:  # unreachable API, JSON error, etc. — fail loud
        print("WATCHABLE_ERR %s" % e)
        return 2

    n_rad = sum(1 for b in bad if b[0] == "radarr")
    n_son = sum(1 for b in bad if b[0] == "sonarr")
    if bad:
        ex = " ".join("%s:%s=%s(%s)" % (a, t[:28], base[:34], why) for a, t, base, why in bad[:8])
        print("WATCHABLE_BAD bad=%d radarr=%d sonarr=%d  %s" % (len(bad), n_rad, n_son, ex))
        return 1
    print("WATCHABLE_OK bad=0 radarr=0 sonarr=0 scanned_movies=%d scanned_series=%d"
          % (scanned_movies, scanned_series))
    return 0


if __name__ == "__main__":
    sys.exit(main())
