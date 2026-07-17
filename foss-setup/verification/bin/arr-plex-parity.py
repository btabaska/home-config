#!/usr/bin/env python3
"""
arr-plex-parity.py — fix-28 (M33) class check.

The 2026-07-16 audit found *arr series that were green (files on disk, 100%
monitored) yet MISSING or wrong in Plex, so unwatchable: Over the Garden Wall
(per-part 'PartNN' filenames -> Plex never built the show, 0 hits) and a wrong
Sonarr series mapped over 'Where Are You!' files. Liveness never caught it
because Sonarr/Radarr and Plex were all "up".

This is the strict, ZERO-TOLERANCE per-item complement to arr-plex-journey.py:
that check passes on a coverage RATIO (>= min-ratio), so a handful of unmatched
items — exactly the 9 movies + 4 shows this audit found — stayed under the ratio
and never tripped it. Here EVERY *arr item that has files on disk must be
represented by a PLAYABLE Plex item, or it fails.

"Represented" = Plex has an item sharing an external id (tmdb/imdb for movies,
tvdb/imdb for series) OR the same normalized title (with year +/-2 for movies).
The title fallback is deliberate: a movie/show present in Plex under a *different*
external id (dual TMDB/TVDB records, imdb-only matches, festival-vs-release year
drift) is still watchable and is NOT the defect this guards — the defect is an
item ABSENT from Plex entirely (no id AND no title hit), which is exactly what
Over the Garden Wall and the wrong-mapped Scooby set looked like.

Items imported within SETTLE_HOURS (default 24) are excluded so normal Plex scan
lag on a fresh import is never a false positive (mirrors arr-plex-journey).

Fails LOUDLY if any API is unreachable/empty. One line:
  PARITY_OK    radarr=M sonarr=S missing=0 excluded_recent=E
  PARITY_BAD   missing=N  e.g. movie:'title'(year) show:'title' ...
  PARITY_ERR   <reason>
"""
import os, re, sys, json, urllib.request, datetime, xml.etree.ElementTree as ET

PLEX = os.environ.get("PLEX_URL", "http://192.168.10.4:32400").rstrip("/")
TOK = os.environ.get("PLEX_TOKEN")
RAD = (os.environ.get("RADARR_URL", "http://192.168.10.4:7878").rstrip("/"), os.environ.get("RADARR_API_KEY"))
SON = (os.environ.get("SONARR_URL", "http://192.168.10.4:8989").rstrip("/"), os.environ.get("SONARR_API_KEY"))
SETTLE_HOURS = float(os.environ.get("PARITY_SETTLE_HOURS", "24"))

def norm(t):
    t = (t or "").lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "", t)

def recent(iso):
    """True if an ISO8601 timestamp is within SETTLE_HOURS of now (scan-lag window)."""
    if not iso:
        return False
    try:
        dt = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        age = (datetime.datetime.now(datetime.timezone.utc) - dt).total_seconds()
        return 0 <= age < SETTLE_HOURS * 3600
    except Exception:
        return False

def plex(path):
    r = urllib.request.Request(PLEX + path, headers={"X-Plex-Token": TOK, "Accept": "application/xml"})
    return ET.fromstring(urllib.request.urlopen(r, timeout=60).read())

def arr(base, key, path):
    r = urllib.request.Request(base + path, headers={"X-Api-Key": key, "Accept": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=90))

def plex_index(section, tag):
    root = plex(f"/library/sections/{section}/all?includeGuids=1")
    items = root.findall(tag)
    ext, titles = set(), {}
    for it in items:
        for g in it.findall("Guid"):
            ext.add(g.get("id"))
        nt = norm(it.get("title"))
        y = it.get("year")
        titles.setdefault(nt, set()).add(int(y) if (y or "").isdigit() else None)
    return items, ext, titles

def main():
    if not (TOK and RAD[1] and SON[1]):
        print("PARITY_ERR missing PLEX_TOKEN/RADARR_API_KEY/SONARR_API_KEY in env"); return 2
    try:
        m_items, m_ext, m_titles = plex_index("1", "Video")
        t_items, t_ext, t_titles = plex_index("2", "Directory")
    except Exception as e:
        print(f"PARITY_ERR plex unreachable: {e}"); return 2
    if not m_items or not t_items:
        print("PARITY_ERR plex movie/tv section returned 0 items"); return 2
    try:
        movies = arr(RAD[0], RAD[1], "/api/v3/movie")
        series = arr(SON[0], SON[1], "/api/v3/series")
    except Exception as e:
        print(f"PARITY_ERR arr unreachable: {e}"); return 2
    if not movies or not series:
        print("PARITY_ERR radarr/sonarr returned 0 items"); return 2

    missing, excluded = [], 0
    for m in movies:
        if not m.get("hasFile"):
            continue
        ids = {f"tmdb://{m.get('tmdbId')}", f"imdb://{m.get('imdbId')}"}
        if ids & m_ext:
            continue
        nt, yr = norm(m.get("title")), m.get("year")
        yrs = m_titles.get(nt)
        if yrs and any(y is None or (yr and abs(y - yr) <= 2) for y in yrs):
            continue
        if recent((m.get("movieFile") or {}).get("dateAdded")):
            excluded += 1; continue
        missing.append(f"movie:{m.get('title')!r}({m.get('year')})")
    for s in series:
        if s.get("statistics", {}).get("episodeFileCount", 0) <= 0:
            continue
        ids = {f"tvdb://{s.get('tvdbId')}", f"imdb://{s.get('imdbId')}"}
        if ids & t_ext:
            continue
        if norm(s.get("title")) in t_titles:
            continue
        if recent(s.get("added")):   # brand-new series not yet Plex-scanned
            excluded += 1; continue
        missing.append(f"show:{s.get('title')!r}")

    if missing:
        print(f"PARITY_BAD missing={len(missing)} radarr={len(movies)} sonarr={len(series)} excluded_recent={excluded} :: " + " ".join(missing[:25]))
        return 1
    print(f"PARITY_OK radarr={len(movies)} sonarr={len(series)} missing=0 excluded_recent={excluded}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
