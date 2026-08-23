#!/usr/bin/env python3
"""b2-bucket-guard — end-to-end B2 immutability + bucket-policy checks (fix-22).

Auths with the SCOPED read-only ops key (B2_OPS_KEY_ID / B2_OPS_KEY from
/etc/verification/env — never the master key, which was retired from the vault
2026-07-17). Two modes:

  --immutable  (regression for H20 / fix-82): proves the ROLLING-30d ransomware
      guarantee at the consumer end, not via config liveness. B2 default
      retention re-stamps only NEW uploads for 30 days; nothing re-stamps
      never-rewritten files, and the delete-capable master key is offline
      (retired 2026-07-17), so versions older than the retention window
      intentionally decay to unprotected. The immutability guarantee is
      therefore ROLLING: every backup uploaded within the last <retention>
      days is governance-locked (operator decision fix-82, 2026-08-23 — see
      wiki/docs/runbooks/backup-restore.md). This check asserts:
        1. bucket-restic default retention is GOVERNANCE >= 30 days;
        2. a backup was uploaded recently (rolling window is live);
        3. EVERY upload version within the retention window carries governance
           retention with retainUntil in the future — a RECENT upload that is
           not locked is the actionable regression (the rolling guarantee
           broke); versions older than the window that have decayed are counted
           and reported as the DOCUMENTED ACCEPTED state, not a failure;
        4. an ACTUAL b2_delete_file_version attempt on the newest (locked) pack
           is refused with HTTP 401.
      The old sampling bug (fix-82 / UM13): it sampled the lexicographically
      FIRST 5 file versions (always the long-decayed mini/config), so it both
      false-failed on the accepted decay AND could have missed a real regression
      of the newest uploads. This version scans all versions and partitions by
      upload age, so it measures the rolling window directly.
      The delete probe is safe by two independent layers: the ops key lacks
      deleteFiles, and the target file is under governance retention.
      Prints "IMMUTABLE-ROLLING ..." on success.

  --policy  (class check for L58/M37): the cloud-surface coverage manifest.
      Every bucket in the account must appear in EXPECTED below with the
      documented lock/lifecycle state — an unknown bucket (the bucket-rustic
      typo class) or drifted policy fails. bucket-hyper-backup is asserted in
      its DOCUMENTED ACCEPTED state (no lock: retention would break Hyper
      Backup Smart Recycle rotation — decision 2026-07-17, see
      wiki/docs/runbooks/backup-restore.md). Prints "POLICY-OK ...".
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

# Cloud coverage manifest: bucket name -> required state. Adding/retiring a B2
# bucket means updating this dict (tripwire mandate), the same commit as the
# bucket change.
EXPECTED = {
    "bucket-restic": {
        "lock_enabled": True,
        "retention_mode": "governance",
        "retention_min_days": 30,
        "lifecycle_hide_to_delete_days": 30,
    },
    "bucket-hyper-backup": {
        # ACCEPTED unlocked (M37): Hyper Backup rotation must delete old
        # versions; guard is the scoped vault key + HB client-side encryption.
        "lock_enabled": False,
        "retention_mode": None,
    },
}

FORBIDDEN_CAPS = {"deleteFiles", "deleteBuckets", "bypassGovernance",
                  "writeFiles", "writeBuckets", "writeKeys", "deleteKeys",
                  "writeFileRetentions", "writeBucketRetentions"}


def fail(msg):
    print(f"BAD {msg}")
    sys.exit(1)


def b2_auth():
    kid = os.environ.get("B2_OPS_KEY_ID", "")
    key = os.environ.get("B2_OPS_KEY", "")
    if not kid or not key:
        fail("B2_OPS_KEY_ID/B2_OPS_KEY not set in environment")
    req = urllib.request.Request(
        "https://api.backblazeb2.com/b2api/v3/b2_authorize_account",
        headers={"Authorization": "Basic "
                 + base64.b64encode(f"{kid}:{key}".encode()).decode()})
    try:
        auth = json.load(urllib.request.urlopen(req, timeout=20))
    except Exception as e:  # noqa: BLE001 - any auth failure is the same verdict
        fail(f"B2 authorize failed: {e}")
    sapi = auth["apiInfo"]["storageApi"]
    return sapi["apiUrl"], auth["authorizationToken"], auth["accountId"], \
        set(sapi.get("capabilities", []))


def call(api, tok, ep, body):
    req = urllib.request.Request(
        f"{api}/b2api/v3/{ep}", data=json.dumps(body).encode(),
        headers={"Authorization": tok, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=30))


def get_buckets(api, tok, acct):
    return {b["bucketName"]: b
            for b in call(api, tok, "b2_list_buckets",
                          {"accountId": acct})["buckets"]}


def check_immutable(api, tok, acct, caps):
    leaked = caps & FORBIDDEN_CAPS
    if leaked:
        fail(f"ops key holds dangerous capabilities: {sorted(leaked)} "
             "— it must be read-only (recreate per runbook)")
    buckets = get_buckets(api, tok, acct)
    br = buckets.get("bucket-restic") or fail("bucket-restic missing")
    lock = br["fileLockConfiguration"]["value"]
    if not lock["isFileLockEnabled"]:
        fail("bucket-restic file lock DISABLED")
    dr = lock.get("defaultRetention") or {}
    period = dr.get("period") or {}
    if dr.get("mode") != "governance" or period.get("unit") != "days" \
            or (period.get("duration") or 0) < 30:
        fail(f"bucket-restic default retention drifted: {json.dumps(dr)} "
             "(want governance >= 30 days)")

    # ROLLING-30d model (fix-82): scan ALL upload versions once, partition by
    # upload age relative to the default-retention window, and assert every
    # in-window upload is governance-locked. Old decayed versions are the
    # documented accepted state (master key offline — no re-lock path).
    now_ms = time.time() * 1000
    window_days = period["duration"]
    window_ms = window_days * 86400 * 1000
    total = recent_locked = expired_old = 0
    recent_unlocked = []
    newest = None
    start = {}
    while True:
        page = call(api, tok, "b2_list_file_versions",
                    {"bucketId": br["bucketId"], "maxFileCount": 1000, **start})
        for f in page["files"]:
            if f["action"] != "upload":
                continue
            total += 1
            ts = f.get("uploadTimestamp") or 0
            if newest is None or ts > (newest.get("uploadTimestamp") or 0):
                newest = f
            ret = (f.get("fileRetention") or {}).get("value") or {}
            locked = ret.get("mode") == "governance" \
                and (ret.get("retainUntilTimestamp") or 0) > now_ms
            if now_ms - ts <= window_ms:
                if locked:
                    recent_locked += 1
                else:
                    recent_unlocked.append(f["fileName"])
            elif not locked:
                expired_old += 1
        nfn = page.get("nextFileName")
        if not nfn:
            break
        start = {"startFileName": nfn, "startFileId": page["nextFileId"]}

    if total == 0:
        fail("no upload versions found in bucket-restic")
    newest_age_h = (now_ms - (newest.get("uploadTimestamp") or 0)) / 3600000
    if newest_age_h > 48:
        fail(f"newest bucket-restic upload is {newest_age_h:.0f}h old — the "
             "rolling backup may have stopped (nothing to keep immutable)")
    if recent_unlocked:
        fail(f"{len(recent_unlocked)} upload(s) within the {window_days}d rolling "
             f"window are NOT governance-locked — rolling immutability BROKEN "
             f"(e.g. {recent_unlocked[0]})")

    # the point of the whole exercise: an actual delete of the newest (locked)
    # pack must be REFUSED
    try:
        call(api, tok, "b2_delete_file_version",
             {"fileName": newest["fileName"], "fileId": newest["fileId"]})
        fail(f"DELETE SUCCEEDED on {newest['fileName']} — backups are NOT "
             "immutable, rotate the ops key and investigate NOW")
    except urllib.error.HTTPError as e:
        if e.code != 401:
            fail(f"delete probe got HTTP {e.code}, expected 401 unauthorized")
    print(f"IMMUTABLE-ROLLING default=gov/{window_days}d recent_locked={recent_locked} "
          f"newest_age={newest_age_h:.1f}h delete-probe=401 "
          f"(accepted decay: {expired_old} version(s) >{window_days}d unprotected — "
          "master key offline, see runbook)")


def check_policy(api, tok, acct, _caps):
    buckets = get_buckets(api, tok, acct)
    problems = []
    for name in sorted(set(buckets) - set(EXPECTED)):
        problems.append(f"UNKNOWN bucket '{name}' (typo/orphan class — "
                        "add to EXPECTED or delete)")
    for name in sorted(set(EXPECTED) - set(buckets)):
        problems.append(f"expected bucket '{name}' MISSING")
    for name, want in EXPECTED.items():
        b = buckets.get(name)
        if not b:
            continue
        lock = b["fileLockConfiguration"]["value"]
        if lock["isFileLockEnabled"] != want["lock_enabled"]:
            problems.append(f"{name}: lock_enabled={lock['isFileLockEnabled']} "
                            f"want {want['lock_enabled']}")
        dr = lock.get("defaultRetention") or {}
        if want["retention_mode"] is None:
            if dr.get("mode"):
                problems.append(f"{name}: unexpected default retention "
                                f"{json.dumps(dr)} (would break HB rotation)")
        else:
            period = dr.get("period") or {}
            if dr.get("mode") != want["retention_mode"] \
                    or (period.get("duration") or 0) < want["retention_min_days"]:
                problems.append(f"{name}: retention drifted {json.dumps(dr)}")
        if "lifecycle_hide_to_delete_days" in want:
            rules = b.get("lifecycleRules") or []
            if not any(r.get("daysFromHidingToDeleting")
                       == want["lifecycle_hide_to_delete_days"] for r in rules):
                problems.append(f"{name}: lifecycle drifted {json.dumps(rules)}")
    if problems:
        fail("; ".join(problems))
    print(f"POLICY-OK buckets={sorted(buckets)}")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in ("--immutable", "--policy"):
        print("usage: b2-bucket-guard.py --immutable|--policy", file=sys.stderr)
        sys.exit(2)
    api, tok, acct, caps = b2_auth()
    if mode == "--immutable":
        check_immutable(api, tok, acct, caps)
    else:
        check_policy(api, tok, acct, caps)


if __name__ == "__main__":
    main()
