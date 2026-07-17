#!/usr/bin/env python3
"""b2-bucket-guard — end-to-end B2 immutability + bucket-policy checks (fix-22).

Auths with the SCOPED read-only ops key (B2_OPS_KEY_ID / B2_OPS_KEY from
/etc/verification/env — never the master key, which was retired from the vault
2026-07-17). Two modes:

  --immutable  (regression for H20): proves the ransomware guarantee at the
      consumer end, not via config liveness —
        1. bucket-restic default retention is GOVERNANCE >= 30 days;
        2. the newest N upload versions each carry per-file GOVERNANCE
           retention with retainUntil in the future;
        3. an ACTUAL b2_delete_file_version attempt on the newest pack is
           refused with HTTP 401 (the vault key cannot delete a backup even
           if every config assertion above rots).
      The delete probe is safe by two independent layers: the ops key lacks
      deleteFiles, and the target file is under governance retention (a delete
      without an explicit bypassGovernance flag fails even for a capable key).
      Prints "IMMUTABLE ..." on success.

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
SAMPLE_VERSIONS = 5


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

    files = call(api, tok, "b2_list_file_versions",
                 {"bucketId": br["bucketId"],
                  "maxFileCount": SAMPLE_VERSIONS})["files"]
    uploads = [f for f in files if f["action"] == "upload"]
    if not uploads:
        fail("no upload versions found in bucket-restic")
    now_ms = time.time() * 1000
    for f in uploads:
        ret = (f.get("fileRetention") or {}).get("value") or {}
        if ret.get("mode") != "governance" \
                or (ret.get("retainUntilTimestamp") or 0) <= now_ms:
            fail(f"file {f['fileName']} not retention-locked: {json.dumps(ret)}")

    # the point of the whole exercise: an actual delete must be REFUSED
    probe = uploads[0]
    try:
        call(api, tok, "b2_delete_file_version",
             {"fileName": probe["fileName"], "fileId": probe["fileId"]})
        fail(f"DELETE SUCCEEDED on {probe['fileName']} — backups are NOT "
             "immutable, rotate the ops key and investigate NOW")
    except urllib.error.HTTPError as e:
        if e.code != 401:
            fail(f"delete probe got HTTP {e.code}, expected 401 unauthorized")
    print(f"IMMUTABLE default=gov/{period['duration']}d "
          f"sampled={len(uploads)} locked, delete-probe=401")


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
