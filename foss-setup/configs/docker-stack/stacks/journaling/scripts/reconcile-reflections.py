#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""journal-reflection reconciler (fix-67 / SM37).

The journal-analyze n8n loop only fires on `memos.memo.created`. A #journal tag
ADDED BY EDITING a memo after it was created arrives as `memos.memo.updated`,
which the Guard node drops by design — so that entry is silently never analyzed
(memo 36, 2026-07-23, was lost exactly this way). This reconciler is the safety
net: it periodically finds every top-level #journal memo that has NO reflection
comment and re-injects a `created`-shaped event into the journal webhook, which
analyzes it and posts the reflection.

Idempotent by construction: a memo that already carries a 🧭 Reflection comment
is skipped, so this also self-heals ANY missed webhook (not just edited-in tags).
Best-effort/degrade-safe: when the coach model is unavailable (rig GPU
contention) the workflow posts nothing and the memo is simply retried next run.
A young memo (< MIN_AGE_S) is left to the live webhook to avoid double-posting.

Reads MEMOS_API_TOKEN from /opt/stacks/journaling/.env (override with env). Talks
to memos + n8n on localhost. Prints one RECONCILE_OK summary line.

Deployed at /opt/stacks/journaling/scripts/reconcile-reflections.py; run hourly
by the mini host timer journal-reflection-reconcile.timer (doc-only mirror under
foss-setup/configs/host/mini/journal-reflection-reconcile/).
task_id: fix-67
"""
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request

MEMOS = os.environ.get("MEMOS_BASE", "http://localhost:5230")
N8N = os.environ.get("N8N_WEBHOOK", "http://localhost:5678/webhook/journal")
ENVF = os.environ.get("JOURNAL_ENV", "/opt/stacks/journaling/.env")
# 🧭 **Reflection** — the header every analyzer comment starts with.
SENTINEL = "\U0001f9ed **Reflection**"
MIN_AGE_S = int(os.environ.get("RECONCILE_MIN_AGE_S", "900"))  # skip memos < 15 min old


def token():
    for line in open(ENVF, encoding="utf-8"):
        line = line.strip()
        if line.startswith("MEMOS_API_TOKEN="):
            return line.split("=", 1)[1]
    print("RECONCILE_FAIL: MEMOS_API_TOKEN not in " + ENVF)
    sys.exit(1)


def get(url, tok):
    r = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok})
    return json.load(urllib.request.urlopen(r, timeout=15))


def list_journal_memos(tok):
    out, page = [], ""
    while True:
        u = MEMOS + "/api/v1/memos?pageSize=200" + (("&pageToken=" + page) if page else "")
        d = get(u, tok)
        for m in d.get("memos", []):
            if "journal" in (m.get("tags") or []):
                out.append(m)
        page = d.get("nextPageToken") or ""
        if not page:
            return out


def has_reflection(name, tok):
    uid = name.split("/")[-1]
    d = get(MEMOS + "/api/v1/memos/" + uid + "/comments", tok)
    return any(SENTINEL in (c.get("content") or "") for c in d.get("memos", []))


def analyzable_body(content):
    """Mirror the Guard's drop rule: strip #hashtags + whitespace; empty => the
    workflow would drop it, so re-injecting it forever is pointless."""
    body = content or ""
    for tok_ in body.split():
        if tok_.startswith("#"):
            body = body.replace(tok_, " ")
    return bool(body.strip())


def parse_ts(m):
    t = m.get("createTime") or ""
    try:
        return datetime.datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=datetime.timezone.utc
        ).timestamp()
    except Exception:
        return 0.0


def inject(m):
    body = json.dumps(
        {
            "activityType": "memos.memo.created",
            "memo": {"name": m["name"], "content": m.get("content", ""), "tags": ["journal"]},
        }
    ).encode("utf-8")
    r = urllib.request.Request(
        N8N, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    urllib.request.urlopen(r, timeout=60).read()


def main():
    tok = token()
    memos = list_journal_memos(tok)
    now = time.time()
    reflected = injected = skipped_fresh = skipped_stub = 0
    for m in memos:
        if has_reflection(m["name"], tok):
            reflected += 1
            continue
        if now - parse_ts(m) < MIN_AGE_S:
            skipped_fresh += 1  # too new; the live webhook is probably handling it
            continue
        if not analyzable_body(m.get("content", "")):
            skipped_stub += 1  # no analyzable body — the Guard would drop it anyway
            continue
        try:
            inject(m)
            injected += 1
            time.sleep(3)  # serialize injections — a single GPU serves the coach model
        except Exception as e:  # noqa: BLE001
            print("RECONCILE_WARN inject failed for %s: %s" % (m.get("name"), e), file=sys.stderr)
    print(
        "RECONCILE_OK total_journal=%d reflected=%d injected=%d skipped_fresh=%d skipped_stub=%d"
        % (len(memos), reflected, injected, skipped_fresh, skipped_stub)
    )


if __name__ == "__main__":
    main()
