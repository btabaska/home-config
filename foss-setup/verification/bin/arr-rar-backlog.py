#!/usr/bin/env python3
"""
arr-rar-backlog.py — fix-27 / M60 acceptance check.

M60's real concern: WANTED content that sits on disk only as an un-extracted RAR
set, which unpackerr (queue-driven — it polls the download queue, never the
library) can never reach. The raw "library rar dir with no video" count is noisy:
it also sees subtitle packs (`*.SUBPACK`) and RARs left redundantly next to an
episode whose real video was already imported elsewhere — neither is a
watchability problem.

This measures the ACTIONABLE backlog precisely and *arr-driven: Radarr movies that
are `hasFile=False` (wanted, missing) whose movie folder on disk contains a `.rar`/
`.r00` set. That is exactly "wanted movie stranded as an un-extractable archive".
The Sonarr/episode side of the class is covered by arr-file-quality.py (a sample or
rar tracked as the episodeFile is caught there).

A rising count means a new rar-only movie import stranded content — extract it in
place (see runbook) or re-grab. The post-fix-27 floor is the small set of honestly
un-recoverable movies (corrupt archives, RAR-contains-only-ISO, subs-only).

Prints:
  RARBACKLOG_OK  stranded=N <=N_max  [titles]
  RARBACKLOG_HIGH stranded=N > N_max  titles=...
  RARBACKLOG_ERR <reason>
"""
import argparse
import json
import os
import shlex
import subprocess
import sys
import urllib.request


def http_get(url, headers=None, timeout=45):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--radarr-url", default=os.environ.get("RADARR_URL", "http://192.168.10.4:7878"))
    ap.add_argument("--max", type=int, default=8, help="floor of known un-recoverable stranded movies")
    ap.add_argument("--movies-root", default="/volume2/movies", help="library path as the NAS sees it")
    ap.add_argument("--container-root", default="/movies", help="path as Radarr reports it")
    ap.add_argument("--timeout", type=int, default=45)
    args = ap.parse_args()
    rk = os.environ.get("RADARR_API_KEY")
    if not rk:
        print("RARBACKLOG_ERR missing RADARR_API_KEY")
        return 2
    try:
        movies = http_get(args.radarr_url.rstrip("/") + "/api/v3/movie", {"X-Api-Key": rk}, args.timeout)
    except Exception as e:
        print("RARBACKLOG_ERR radarr unreachable: %s" % e)
        return 2
    if not movies:
        print("RARBACKLOG_ERR radarr returned no movies")
        return 2
    wanted = [m for m in movies if not m.get("hasFile") and m.get("path")]
    # one NAS-side find over all wanted movie folders that still have a rar set
    folders = [m["path"].replace(args.container_root, args.movies_root, 1) for m in wanted]
    stranded = []
    if folders:
        # feed folders on stdin (one per line) — ssh flattens argv and would split
        # paths containing spaces ("The Intouchables 2011 …"). read -r preserves them.
        script = 'while IFS= read -r d; do ls "$d"/*.rar "$d"/*.r00 >/dev/null 2>&1 && echo "$d"; done'
        # ssh flattens argv into one remote-shell string, so quote the whole command
        remote = "bash -c " + shlex.quote(script)
        out = subprocess.run(["ssh", "nas", remote],
                             input="\n".join(folders) + "\n",
                             capture_output=True, text=True, timeout=120).stdout
        hits = set(l.strip() for l in out.splitlines() if l.strip())
        for m in wanted:
            if m["path"].replace(args.container_root, args.movies_root, 1) in hits:
                stranded.append("%s (%s)" % (m.get("title", "?"), m.get("year", "?")))
    n = len(stranded)
    titles = "; ".join(sorted(stranded))
    if n > args.max:
        print("RARBACKLOG_HIGH stranded=%d >%d titles=%s" % (n, args.max, titles))
        return 1
    print("RARBACKLOG_OK stranded=%d <=%d %s" % (n, args.max, ("[" + titles + "]") if titles else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
