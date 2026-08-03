#!/usr/bin/env python3
"""Self-clean stale Sonarr/Radarr import-queue records (fix-54, SH2/SH9/SM4).

Background (2026-08-02 fleet sweep): the seedbox user quota hit EDQUOT, which
(a) dropped torrent payloads under live "Seeding" torrents and (b) blocked
deluge from persisting its Post-Import label relabel. The downstream effect was
Sonarr/Radarr looping "path does not exist / No files found eligible" for 3-4
DAYS on grabs that would never import, plus stale "Not an upgrade" and
wrong-map records piling up (16-17 stuck in Sonarr). Nothing self-cleaned them.

This reconciler is the generator-closer. Every run it removes queue records that
are PROVABLY safe to drop, and ONLY those:

  age(record) > MAX_AGE_HOURS (default 72h — transient/active grabs are never
  touched) AND trackedDownloadStatus == "warning" AND one of:

    * SATISFIED — the episode(s)/movie the grab is for already hasFile=True
      (imported from another release). The grab is a redundant duplicate.
      -> remove + blocklist, skipRedownload=true (do NOT re-grab; already have it).
      Covers Better.Off.Ted / A.Knight / HotD dupes and every "Not an upgrade".

    * DEAD-END — a terminal status message ("No files found are eligible",
      "path does not exist", "Not an upgrade", "Not a Custom Format upgrade")
      on a still-fileless item = the download is dead (payload gone / unusable).
      -> remove + blocklist, skipRedownload=false (let the arr re-search a clean
      copy; the dead release is blocklisted so it won't be re-picked).

Deliberately NOT auto-removed: wrong-series/wrong-movie maps ("matched ... by ID"
where the item is still fileless) — those can be a real release needing a manual
import decision, so they are left for a human.

Idempotent; caps removals per run (MAX_REMOVALS). Prints one summary line.
Exit 0 on success (even if it removed nothing); non-zero only on an API/config
error, so OnFailure=ntfy fires on a real break, not the steady state.

Env: SONARR_URL/SONARR_API_KEY, RADARR_URL/RADARR_API_KEY (required),
     MAX_AGE_HOURS (default 72), MAX_REMOVALS (default 25),
     DRY_RUN (set to 1 to log without deleting),
     HEALTHCHECKS_PING_URL (optional dead-man ping).
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

DRY = os.environ.get("DRY_RUN", "0") == "1"
MAX_AGE = float(os.environ.get("MAX_AGE_HOURS", "72")) * 3600
MAX_REMOVALS = int(os.environ.get("MAX_REMOVALS", "25"))
DEAD_END = (
    "no files found are eligible",
    "path does not exist",
    "not an upgrade",
    "not a custom format upgrade",
)

ARRS = []
for name, uenv, kenv, ver in (
    ("sonarr", "SONARR_URL", "SONARR_API_KEY", "v3"),
    ("radarr", "RADARR_URL", "RADARR_API_KEY", "v3"),
):
    url = os.environ.get(uenv)
    key = os.environ.get(kenv)
    if url and key:
        ARRS.append((name, url.rstrip("/"), ver, key))


def api(base, ver, key, path, method="GET", timeout=45, retries=4):
    # Sonarr/Radarr intermittently 401/500/time out under DB-lock / I/O
    # contention (API-key validation reads the locked DB -> spurious 401). A
    # transient blip must not page or abort the run — retry with backoff and
    # only surface the error if every attempt fails.
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(
            f"{base}/api/{ver}/{path}", method=method,
            headers={"X-Api-Key": key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                return json.loads(raw) if raw else None
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
            if attempt < retries - 1:
                time.sleep(4 * (attempt + 1))
    raise last


def age_seconds(added):
    try:
        t = datetime.fromisoformat(added.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - t).total_seconds()
    except Exception:
        return 0.0


def msgs_of(rec):
    out = []
    for sm in rec.get("statusMessages", []) or []:
        for m in sm.get("messages", []) or []:
            out.append(m.lower())
    if rec.get("errorMessage"):
        out.append(rec["errorMessage"].lower())
    return out


def satisfied(name, base, ver, key, rec):
    """True iff the media this record is for already has a file."""
    try:
        if name == "radarr":
            mid = rec.get("movieId")
            if not mid:
                return False
            return bool(api(base, ver, key, f"movie/{mid}").get("hasFile"))
        else:
            eid = rec.get("episodeId")
            if not eid:
                return False
            return bool(api(base, ver, key, f"episode/{eid}").get("hasFile"))
    except Exception:
        return False  # unknown -> treat as NOT satisfied (safer: won't skip-redownload)


def reconcile(name, base, ver, key):
    removed = wrongmap_skipped = 0
    q = api(base, ver, key, "queue?pageSize=500"
            "&includeUnknownSeriesItems=true&includeUnknownMovieItems=true")
    for rec in q.get("records", []):
        if removed >= MAX_REMOVALS:
            break
        if rec.get("trackedDownloadStatus") != "warning":
            continue
        if age_seconds(rec.get("added", "")) < MAX_AGE:
            continue
        msgs = msgs_of(rec)
        sat = satisfied(name, base, ver, key, rec)
        dead = any(any(d in m for d in DEAD_END) for m in msgs)
        wrongmap = any("matched" in m and "by id" in m for m in msgs)
        if wrongmap and not sat:
            wrongmap_skipped += 1
            continue  # leave wrong-series/movie maps for a human
        if not (sat or dead):
            continue
        skip_redl = "true" if sat else "false"  # re-search only dead-but-missing
        qid = rec.get("id")
        title = (rec.get("title") or "?")[:55]
        reason = "satisfied" if sat else "dead-end"
        if DRY:
            print(f"  DRY would-remove [{name}] {reason} skipRedl={skip_redl} "
                  f"qid={qid} {title}", file=sys.stderr)
            removed += 1
            continue
        try:
            api(base, ver, key,
                f"queue/{qid}?removeFromClient=true&blocklist=true"
                f"&skipRedownload={skip_redl}", method="DELETE", timeout=60)
            removed += 1
        except Exception as e:  # a slow deluge round-trip may time out; retried next run
            print(f"  WARN [{name}] delete qid={qid} failed "
                  f"({type(e).__name__}); will retry next run", file=sys.stderr)
    return removed, wrongmap_skipped


def ping(url):
    if not url:
        return
    try:
        urllib.request.urlopen(url, timeout=10).read()
    except Exception:
        pass


def main():
    if not ARRS:
        print("CONFIG_ERR no SONARR/RADARR url+key in env")
        sys.exit(1)
    total_removed = total_wrongmap = 0
    try:
        for name, base, ver, key in ARRS:
            r, w = reconcile(name, base, ver, key)
            total_removed += r
            total_wrongmap += w
    except Exception as e:  # noqa: BLE001 — any API failure is a real break
        print(f"API_ERR {type(e).__name__}: {e}")
        sys.exit(1)
    mode = "DRY " if DRY else ""
    print(f"{mode}RECONCILE_OK removed={total_removed} "
          f"wrongmap_left={total_wrongmap}")
    ping(os.environ.get("HEALTHCHECKS_PING_URL"))


if __name__ == "__main__":
    main()
