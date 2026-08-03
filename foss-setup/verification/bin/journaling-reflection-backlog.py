#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""journaling-reflection-backlog (fix-67 / SM37) — consumer-end class check.

Every real #journal entry should end up with a 🧭 Reflection comment. The
journal-analyze loop only fires on memos.memo.created, so a #journal tag added
by EDIT (a memos.memo.updated event, dropped by the Guard) never gets analyzed —
memo 36 was lost exactly this way. The reconciler (journal-reflection-reconcile
timer) backfills those; this check verifies the OUTCOME: no top-level #journal
memo older than 24h is still missing its reflection.

The 24h grace lets the hourly reconciler + the nightly free-GPU window (immich-ml
is off 01-07) clear the backlog, so this does NOT false-positive during day-time
GPU contention (a fresh entry waiting on an evicted coach model is < 24h old).
Stubs with no analyzable body (only the tag) are excluded — the Guard drops those
and they can never earn a reflection.

Reads MEMOS_API_TOKEN from the runner env (/etc/verification/env). Prints
REFLECTION_BACKLOG=<n> [names]. expect ^REFLECTION_BACKLOG=0$.
task_id: fix-67
"""
import datetime
import json
import os
import sys
import urllib.request

MEMOS = os.environ.get("MEMOS_BASE", "http://localhost:5230")
TOK = os.environ.get("MEMOS_API_TOKEN", "")
SENTINEL = "\U0001f9ed **Reflection**"
MAX_AGE_S = 24 * 3600


def get(url):
    r = urllib.request.Request(url, headers={"Authorization": "Bearer " + TOK})
    return json.load(urllib.request.urlopen(r, timeout=15))


def analyzable(content):
    body = content or ""
    for t in body.split():
        if t.startswith("#"):
            body = body.replace(t, " ")
    return bool(body.strip())


def parse_ts(m):
    t = m.get("createTime") or ""
    try:
        return datetime.datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=datetime.timezone.utc
        ).timestamp()
    except Exception:
        return 0.0


def main():
    if not TOK:
        print("REFLECTION_BACKLOG=ERR MEMOS_API_TOKEN unset")
        sys.exit(1)
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    backlog, page = [], ""
    while True:
        d = get(MEMOS + "/api/v1/memos?pageSize=200" + (("&pageToken=" + page) if page else ""))
        for m in d.get("memos", []):
            if "journal" not in (m.get("tags") or []):
                continue
            if now - parse_ts(m) < MAX_AGE_S:
                continue
            if not analyzable(m.get("content", "")):
                continue
            uid = m["name"].split("/")[-1]
            c = get(MEMOS + "/api/v1/memos/" + uid + "/comments")
            if not any(SENTINEL in (x.get("content") or "") for x in c.get("memos", [])):
                backlog.append(uid)
        page = d.get("nextPageToken") or ""
        if not page:
            break
    print("REFLECTION_BACKLOG=%d%s" % (len(backlog), (" " + ",".join(backlog)) if backlog else ""))


if __name__ == "__main__":
    main()
