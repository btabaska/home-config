#!/usr/bin/env python3
"""media-05 consumer probe: prove Jellyfin actually SERVES playable media, not just that
the container is up. Authenticates with an API key, asserts the Movies + TV libraries
contain real items, and range-GETs one movie's stream to prove the file is readable and
served end-to-end (a green /health tells you nothing about whether a title will play).

Emits one line:  JELLYFIN_OK movies=<n> episodes=<n> songs=<n> stream=<code> title="<t>"
             or  JELLYFIN_FAIL <reason>
Exit 0 only on JELLYFIN_OK.

Env / args:
  --url    Jellyfin base (default $JELLYFIN_URL or http://nas:8096)
  --key    API key       (default $JELLYFIN_API_KEY)
  --min-movies    floor for MovieCount   (default 25)
  --min-episodes  floor for EpisodeCount (default 25)
"""
import argparse, json, os, sys, urllib.request, urllib.error

def get(url, key, timeout=15, headers=None, rng=None):
    h = {"X-Emby-Token": key}
    if headers:
        h.update(headers)
    if rng:
        h["Range"] = rng
    r = urllib.request.Request(url, headers=h)
    resp = urllib.request.urlopen(r, timeout=timeout)
    return resp

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("JELLYFIN_URL", "http://nas:8096"))
    ap.add_argument("--key", default=os.environ.get("JELLYFIN_API_KEY", ""))
    ap.add_argument("--min-movies", type=int, default=25)
    ap.add_argument("--min-episodes", type=int, default=25)
    a = ap.parse_args()
    base = a.url.rstrip("/")
    if not a.key:
        print("JELLYFIN_FAIL no-api-key (set JELLYFIN_API_KEY)"); return 1

    # 1. library counts — proves the scan populated real content
    try:
        counts = json.load(get(base + "/Items/Counts", a.key))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
        print("JELLYFIN_FAIL counts-unreachable %s" % e); return 1
    movies = counts.get("MovieCount", 0)
    episodes = counts.get("EpisodeCount", 0)
    songs = counts.get("SongCount", 0)
    if movies < a.min_movies:
        print("JELLYFIN_FAIL movies=%d < %d (library empty/broken scan)" % (movies, a.min_movies)); return 1
    if episodes < a.min_episodes:
        print("JELLYFIN_FAIL episodes=%d < %d (tv library empty/broken scan)" % (episodes, a.min_episodes)); return 1

    # 2. pick one movie with a real media source (file path + size)
    try:
        q = "/Items?IncludeItemTypes=Movie&Recursive=true&Limit=1&Fields=MediaSources&SortBy=Random"
        items = json.load(get(base + q, a.key)).get("Items", [])
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
        print("JELLYFIN_FAIL items-query-failed %s" % e); return 1
    if not items:
        print("JELLYFIN_FAIL no-movie-items-returned"); return 1
    item = items[0]
    iid = item.get("Id")
    title = (item.get("Name") or "?")[:40]
    srcs = item.get("MediaSources") or []
    if not srcs or not srcs[0].get("Size"):
        print('JELLYFIN_FAIL no-media-source title="%s"' % title); return 1

    # 3. range-GET the stream — proves the file is readable and served (real playback)
    stream_url = base + "/Videos/%s/stream?static=true&api_key=%s" % (iid, a.key)
    try:
        resp = get(stream_url, a.key, rng="bytes=0-2047")
        code = resp.status
        chunk = resp.read(2048)
    except urllib.error.HTTPError as e:
        code = e.code; chunk = b""
    except urllib.error.URLError as e:
        print('JELLYFIN_FAIL stream-unreachable %s title="%s"' % (e, title)); return 1
    if code not in (200, 206) or len(chunk) == 0:
        print('JELLYFIN_FAIL stream code=%s bytes=%d title="%s"' % (code, len(chunk), title)); return 1

    print('JELLYFIN_OK movies=%d episodes=%d songs=%d stream=%d title="%s"'
          % (movies, episodes, songs, code, title))
    return 0

if __name__ == "__main__":
    sys.exit(main())
