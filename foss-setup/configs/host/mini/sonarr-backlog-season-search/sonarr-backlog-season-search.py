#!/usr/bin/env python3
"""One THROTTLED Sonarr season search per run — the safe backlog clearer.

Replaces the 2026-08-10 sonarr-backlog-sweep (torn down 2026-08-11), which fired
per-episode EpisodeSearch batches (~150 indexer queries/hour). That burned the
IPTorrents 600-queries/24h budget — over-budget searches return 0 through
Prowlarr, so the backlog LOOKED unsearchable — and its queue-janitor ran during
the NAS SQLite lock storm. See memory/runlog 2026-08-11.

Strategy (learned from the 2026-08-11 fix): old shows complete via SEASON
PACKS. One SeasonSearch can net an entire season (39 episodes in the validation
run) for a handful of indexer queries. So each run picks the single
highest-yield season — most missing monitored episodes, aired > MIN_AGE_DAYS
(RSS owns the recent stuff), not attempted within COOLDOWN_DAYS — fires ONE
SeasonSearch, records it, exits. At the 2-hour timer cadence that is at most 12
season searches/day, a small slice of the shared IPT budget alongside RSS.

Guards — the run SKIPs (exit 0, one SKIP line) when:
  * a Search command is already queued/running in Sonarr (don't stack searches)
  * the queue holds > MAX_QUEUE_WARNINGS warning items (imports are in trouble;
    pouring more grabs in makes it worse)
  * nothing qualifies (backlog clear or everything cooling down) -> DONE_OK
A real API/config error exits 1 so OnFailure=ntfy-notify@ fires.

State: $STATE_DIRECTORY/state.json  {"searched": {"<seriesId>-<season>": epoch}}
Env:   SONARR_API_KEY (required), SONARR_URL (default http://192.168.10.4:8989),
       COOLDOWN_DAYS (14), MIN_AGE_DAYS (7), MAX_QUEUE_WARNINGS (15),
       HEALTHCHECKS_PING_URL (optional dead-man ping).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("SONARR_URL", "http://192.168.10.4:8989").rstrip("/") + "/api/v3"
KEY = os.environ.get("SONARR_API_KEY")
COOLDOWN = float(os.environ.get("COOLDOWN_DAYS", "14")) * 86400
MIN_AGE = float(os.environ.get("MIN_AGE_DAYS", "7")) * 86400
MAX_WARN = int(os.environ.get("MAX_QUEUE_WARNINGS", "15"))
STATE_DIR = os.environ.get("STATE_DIRECTORY", "/var/lib/sonarr-backlog-season-search")
STATE = os.path.join(STATE_DIR, "state.json")

RETRY_STATUS = {500, 502, 503, 504}
MAX_TRIES = 4


def api(path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    last = None
    for attempt in range(1, MAX_TRIES + 1):
        req = urllib.request.Request(
            BASE + path, data=data, method=method,
            headers={"X-Api-Key": KEY, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            last = e
            if e.code in RETRY_STATUS and attempt < MAX_TRIES:
                time.sleep(min(2 ** attempt, 15))
                continue
            raise
        except urllib.error.URLError as e:
            last = e
            if attempt < MAX_TRIES:
                time.sleep(min(2 ** attempt, 15))
                continue
            raise
    if last:  # pragma: no cover
        raise last


def load_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"searched": {}}


def save_state(state):
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE)


def main():
    if not KEY:
        print("CONFIG_ERR missing SONARR_API_KEY")
        return 1

    # Guard 1: a search is already queued/running — don't stack.
    for c in api("/command") or []:
        if c.get("status") in ("queued", "started") and "Search" in (c.get("name") or ""):
            print(f"SKIP search-already-running name={c.get('name')} id={c.get('id')}")
            return 0

    # Guard 2: import trouble — queue full of warnings.
    q = api("/queue?page=1&pageSize=200")
    warn = sum(1 for r in q.get("records", [])
               if r.get("trackedDownloadStatus") == "warning")
    if warn > MAX_WARN:
        print(f"SKIP queue-warnings={warn} > {MAX_WARN} — clear imports first")
        return 0

    # Collect missing monitored episodes, old enough that RSS won't cover them.
    now = time.time()
    counts = {}   # (seriesId, season) -> missing count
    titles = {}   # seriesId -> title
    page = 1
    while page <= 10:
        d = api(f"/wanted/missing?page={page}&pageSize=500"
                "&sortKey=airDateUtc&sortDirection=ascending&includeSeries=true&monitored=true")
        recs = d.get("records", [])
        for e in recs:
            season = e.get("seasonNumber", 0)
            if season <= 0:
                continue  # specials: rarely in packs, poor query value
            air = e.get("airDateUtc")
            if air:
                try:
                    aired = time.mktime(time.strptime(air[:19], "%Y-%m-%dT%H:%M:%S"))
                    if now - aired < MIN_AGE:
                        continue
                except ValueError:
                    pass
            sid = e["seriesId"]
            counts[(sid, season)] = counts.get((sid, season), 0) + 1
            if e.get("series"):
                titles[sid] = e["series"].get("title", "?")
        if page * 500 >= d.get("totalRecords", 0) or not recs:
            break
        page += 1

    state = load_state()
    searched = state.setdefault("searched", {})
    candidates = [(n, sid, season) for (sid, season), n in counts.items()
                  if now - searched.get(f"{sid}-{season}", 0) > COOLDOWN]
    if not candidates:
        print(f"DONE_OK nothing-to-search seasons_missing={len(counts)} (all cooling down or clear)")
        return 0

    # Highest yield first; stable tie-break keeps rotation deterministic.
    n, sid, season = max(candidates, key=lambda c: (c[0], -c[1], -c[2]))
    cmd = api("/command", method="POST",
              body={"name": "SeasonSearch", "seriesId": sid, "seasonNumber": season})
    searched[f"{sid}-{season}"] = now
    save_state(state)
    print(f"SEARCHED series={titles.get(sid, sid)!r} season={season} "
          f"missing={n} commandId={cmd.get('id')} candidates={len(candidates)}")

    ping = os.environ.get("HEALTHCHECKS_PING_URL")
    if ping:
        try:
            urllib.request.urlopen(ping, timeout=10)
        except OSError:
            pass  # dead-man ping is best-effort
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.HTTPError as e:
        print(f"API_ERR HTTP {e.code} {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"API_ERR URLError: {e.reason}")
        sys.exit(1)
    except Exception as e:  # noqa: BLE001 — one line for the journal, nonzero for ntfy
        print(f"API_ERR {type(e).__name__}: {e}")
        sys.exit(1)
