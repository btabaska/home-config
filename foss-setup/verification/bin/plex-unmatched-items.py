#!/usr/bin/env python3
"""
plex-unmatched-items.py — fix-28 (M32/M33) class check.

The 2026-07-16 audit found real, playable movies/shows sitting in Plex with NO
external-ID match (guid=local://, zero <Guid> children): 9 junk-titled movies
(Pirates/Fast&Furious/Star Trek packs, brace-years, mangled names) and TV shows
that fell to a local:// match (Delicious in Dungeon). Such items display with
mangled metadata, are invisible to guid-based availability sync (seerr), and — the
reason liveness monitoring missed them — Plex is "up" and the file is "playable",
so nothing was ever red.

This probes the CONSUMER end: enumerate the Movies + TV libraries and fail if any
item carries no external identifier (imdb/tmdb/tvdb). Scoped to the agent-backed
libraries ONLY (Movies=1, TV=2); the Music (3) and personal YouTube (4) libraries
are local-by-design and excluded.

Fails LOUDLY if Plex is unreachable or a section returns nothing (never a vacuous
pass on a down server). One line:
  UNMATCHED_OK   movies=M tv=T bad=0
  UNMATCHED_BAD  bad=N  e.g. movie:'title'(year) show:'title' ...
  UNMATCHED_ERR  <reason>
"""
import os, sys, urllib.request, xml.etree.ElementTree as ET

PLEX = os.environ.get("PLEX_URL", "http://192.168.10.4:32400").rstrip("/")
TOK = os.environ.get("PLEX_TOKEN")
SECTIONS = {"1": ("Video", "movie"), "2": ("Directory", "show")}

def get(path):
    r = urllib.request.Request(PLEX + path, headers={"X-Plex-Token": TOK, "Accept": "application/xml"})
    return ET.fromstring(urllib.request.urlopen(r, timeout=45).read())

def has_ext(it):
    if len(it.findall("Guid")) > 0:
        return True
    g = it.get("guid", "")
    return g.startswith(("plex://", "imdb://", "tmdb://", "tvdb://"))

def main():
    if not TOK:
        print("UNMATCHED_ERR missing PLEX_TOKEN in env"); return 2
    counts, bad = {}, []
    for sec, (tag, kind) in SECTIONS.items():
        try:
            root = get(f"/library/sections/{sec}/all?includeGuids=1")
        except Exception as e:
            print(f"UNMATCHED_ERR plex section {sec} unreachable: {e}"); return 2
        items = root.findall(tag)
        if not items:
            print(f"UNMATCHED_ERR plex section {sec} returned 0 items"); return 2
        counts[kind] = len(items)
        for it in items:
            if not has_ext(it):
                y = it.get("year")
                bad.append(f"{kind}:{it.get('title')!r}" + (f"({y})" if y else ""))
    m, t = counts.get("movie", 0), counts.get("show", 0)
    if bad:
        print(f"UNMATCHED_BAD bad={len(bad)} movies={m} tv={t} :: " + " ".join(bad[:25]))
        return 1
    print(f"UNMATCHED_OK movies={m} tv={t} bad=0")
    return 0

if __name__ == "__main__":
    sys.exit(main())
