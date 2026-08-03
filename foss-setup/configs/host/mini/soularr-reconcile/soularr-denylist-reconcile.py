#!/usr/bin/env python3
"""Prune soularr's failed-import denylist against live Lidarr state (fix-56).

Background (2026-08-02 fleet sweep SM29, a fix-40 regression):
soularr (ghcr.io/mrusse/soularr:1.2.2) keeps a persistent denylist at
/volume1/docker/soularr/failed_imports.json. When an import fails it appends the
album id via add_to_failed_import_denylist(); every later cycle it logs
"Skipping failed import album" and never re-searches it. The upstream code has
NO path that ever REMOVES an entry (verified in /app/soularr.py) — so the file
is a monotonically growing dead-letter that collects two kinds of rot:

  * GHOSTS — an album that later completed via another path (a torrent grab, a
    manual import, or a re-request) but whose stale entry lingers forever (e.g.
    the Eminem 5030 entry fix-40 cleared by hand; on 2026-08-02 the JSON held
    Paradise 10/10, Hybrid Theory 15/15, Underclass Hero 16/16 — all complete).
  * ABANDONED — an album the operator has since unmonitored (soularr won't act
    on an unmonitored album anyway, so the entry is dead weight).

fix-40 only cleared the file once and added the nas-soularr-failed-imports-fresh
tripwire; it added no prevention, so the backlog re-accumulated and Camera +
Heat Waves aged past the 3-day staleness threshold, cycling indefinitely.

This reconciler is the generator-closer. Every run it removes ONLY entries that
are provably safe to drop — the album, per live Lidarr, is one of:
  * COMPLETE   (trackFileCount >= totalTrackCount, total > 0) — succeeded; or
  * UNMONITORED (operator/pipeline gave up) — soularr's skip is moot; or
  * DELETED     (404 — album no longer exists in Lidarr).
A monitored + still-incomplete album is LEFT in the denylist (soularr should not
retry a known-bad import) — that is exactly the genuinely-stuck case the
nas-soularr-failed-imports-fresh check is meant to surface for a human after 3
days, and soularr-denylist-no-ghosts catches ghost re-accumulation before then.

The denylist lives on the NAS; soularr runs on the NAS; this reconciler runs on
the mini (which has passwordless ssh to nas and the Lidarr key) following the
media-07 lidarr-reconcile pattern. The prune is applied NAS-side in one python
invocation that deletes only the named keys from the CURRENT file (so a soularr
cycle that appends a new entry mid-run is not clobbered), then atomically
os.replace()s it.

Env: LIDARR_API_KEY (required), LIDARR_URL (default http://192.168.10.4:8686),
NAS_SSH (default "nas"), DENYLIST_PATH (default the NAS soularr path),
HEALTHCHECKS_PING_URL (optional dead-man ping).

Prints one line; exit 0 on success (whether or not it pruned anything), non-zero
only on an API/ssh/config error, so OnFailure=ntfy fires on a real break.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("LIDARR_URL", "http://192.168.10.4:8686").rstrip("/") + "/api/v1"
KEY = os.environ.get("LIDARR_API_KEY")
NAS = os.environ.get("NAS_SSH", "nas")
DENYLIST = os.environ.get("DENYLIST_PATH", "/volume1/docker/soularr/failed_imports.json")

RETRY_STATUS = {500, 502, 503, 504}
MAX_TRIES = 4  # 2s,4s,8s backoff then a final try (~14s worst case) — tolerate a lock blip


def api(path):
    """GET Lidarr; retry transient 5xx (NAS SQLite-lock blips, fix-55). Returns
    the parsed body, or None on a 404 (album deleted)."""
    last = None
    for attempt in range(1, MAX_TRIES + 1):
        req = urllib.request.Request(BASE + path, headers={"X-Api-Key": KEY,
                                                            "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            last = e
            if e.code in RETRY_STATUS and attempt < MAX_TRIES:
                time.sleep(min(2 ** attempt, 15)); continue
            raise
        except urllib.error.URLError as e:
            last = e
            if attempt < MAX_TRIES:
                time.sleep(min(2 ** attempt, 15)); continue
            raise
    if last:  # pragma: no cover
        raise last


def read_denylist():
    out = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
                          NAS, "cat", DENYLIST],
                         capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        if "No such file" in out.stderr:
            return {}
        raise RuntimeError(f"ssh cat denylist failed: {out.stderr.strip()}")
    txt = out.stdout.strip()
    return json.loads(txt) if txt else {}


def prune_remote(keys):
    """Delete exactly these keys from the CURRENT NAS file (race-safe against a
    concurrent soularr append), atomically. Returns the list actually removed."""
    # Pipe the program via stdin to `python3 -` so no shell (local or remote)
    # re-parses code that contains parens/quotes. Keys are embedded as a JSON
    # literal; the reader script itself takes no stdin data.
    remote = (
        "import json,os,tempfile\n"
        f"p={json.dumps(DENYLIST)}\n"
        f"prune=set({json.dumps(keys)})\n"
        "d=json.load(open(p)) if os.path.exists(p) else {}\n"
        "removed=[k for k in list(d) if k in prune]\n"
        "for k in removed: d.pop(k)\n"
        "fd,tmp=tempfile.mkstemp(dir=os.path.dirname(p))\n"
        "f=os.fdopen(fd,'w'); json.dump(d,f,indent=2); f.close()\n"
        "os.chmod(tmp,0o664); os.replace(tmp,p)\n"
        "print('REMOTE_PRUNED '+','.join(removed))\n"
    )
    out = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
                          NAS, "python3", "-"],
                         input=remote, capture_output=True, text=True, timeout=40)
    if out.returncode != 0:
        raise RuntimeError(f"remote prune failed: {out.stderr.strip()}")
    lines = out.stdout.strip().splitlines()
    for line in reversed(lines):
        if line.startswith("REMOTE_PRUNED"):
            payload = line[len("REMOTE_PRUNED"):].strip()
            return payload.split(",") if payload else []
    return []


def classify(entry_id):
    """Return a drop-reason string if the album is safe to drop, else None."""
    a = api(f"/album/{entry_id}")
    if a is None:
        return "deleted"
    if not a.get("monitored"):
        return "unmonitored"
    st = a.get("statistics", {}) or {}
    tot = st.get("totalTrackCount") or st.get("trackCount") or 0
    if tot > 0 and st.get("trackFileCount", 0) >= tot:
        return "complete"
    return None


def main():
    if not KEY:
        print("CONFIG_ERR missing LIDARR_API_KEY"); sys.exit(1)
    try:
        denylist = read_denylist()
    except Exception as e:  # noqa: BLE001
        print(f"NAS_ERR {type(e).__name__}: {e}"); sys.exit(1)

    if not denylist:
        print("RECONCILE_OK denylist_empty pruned=0"); _ping(); return

    to_drop = {}
    try:
        for k in list(denylist):
            reason = classify(k)
            if reason:
                title = denylist[k].get("title", k)
                to_drop[k] = f"{title}({reason})"
    except Exception as e:  # noqa: BLE001 — any Lidarr failure is a real break
        print(f"API_ERR {type(e).__name__}: {e}"); sys.exit(1)

    if not to_drop:
        print(f"RECONCILE_OK kept={len(denylist)} pruned=0 (all monitored+incomplete)")
        _ping(); return

    try:
        removed = prune_remote(list(to_drop))
    except Exception as e:  # noqa: BLE001
        print(f"NAS_ERR {type(e).__name__}: {e}"); sys.exit(1)

    kept = len(denylist) - len(removed)
    print(f"RECONCILE_OK kept={kept} pruned={len(removed)}: "
          + "; ".join(to_drop[k] for k in removed if k in to_drop))
    _ping()


def _ping():
    url = os.environ.get("HEALTHCHECKS_PING_URL")
    if not url:
        return
    try:
        urllib.request.urlopen(url, timeout=10).read()
    except Exception:  # noqa: BLE001
        print("WARN: healthchecks ping failed")


if __name__ == "__main__":
    main()
