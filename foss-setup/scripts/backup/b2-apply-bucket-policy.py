#!/usr/bin/env python3
"""b2-apply-bucket-policy — idempotently (re)apply the B2 bucket policy (fix-22).

The desired cloud state is code here so a rebuilt/replaced bucket can be
restored to policy instead of relying on memory of what the web console once
said. Verification of this state runs daily via
verification/bin/b2-bucket-guard.py; THIS script is the repair tool.

Policy (2026-07-17):
  bucket-restic       file lock ON, default retention GOVERNANCE 30d,
                      lifecycle daysFromHidingToDeleting=30. Existing upload
                      versions without retention get a 30d GOVERNANCE backfill
                      (--backfill).
  bucket-hyper-backup deliberately NO lock/retention — Hyper Backup Smart
                      Recycle rotation must delete old versions (accepted
                      M37); do not "fix" this without rethinking HB rotation.

Requires a key with writeBucketRetentions/writeFileRetentions — i.e. the B2
MASTER key, which was retired from the vault to offline storage 2026-07-17.
Pass it explicitly:
    B2_MASTER_KEY_ID=... B2_MASTER_KEY=... ./b2-apply-bucket-policy.py [--backfill]
The day-to-day vault ops key is read-only on purpose and will be rejected.
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

RETENTION_DAYS = 30


def call(api, tok, ep, body):
    req = urllib.request.Request(
        f"{api}/b2api/v3/{ep}", data=json.dumps(body).encode(),
        headers={"Authorization": tok, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=30))


def main():
    kid = os.environ.get("B2_MASTER_KEY_ID", "")
    key = os.environ.get("B2_MASTER_KEY", "")
    if not kid or not key:
        sys.exit("set B2_MASTER_KEY_ID + B2_MASTER_KEY (master key is offline, "
                 "not in the vault — see operations/secrets.md)")
    req = urllib.request.Request(
        "https://api.backblazeb2.com/b2api/v3/b2_authorize_account",
        headers={"Authorization": "Basic "
                 + base64.b64encode(f"{kid}:{key}".encode()).decode()})
    auth = json.load(urllib.request.urlopen(req, timeout=20))
    sapi = auth["apiInfo"]["storageApi"]
    api, tok, acct = sapi["apiUrl"], auth["authorizationToken"], auth["accountId"]
    caps = set(sapi.get("capabilities", []))
    need = {"writeBucketRetentions", "writeFileRetentions", "listFiles"}
    if not need <= caps:
        sys.exit(f"key lacks {sorted(need - caps)} — use the master key")

    buckets = {b["bucketName"]: b
               for b in call(api, tok, "b2_list_buckets",
                             {"accountId": acct})["buckets"]}
    br = buckets["bucket-restic"]
    lock = br["fileLockConfiguration"]["value"]
    dr = lock.get("defaultRetention") or {}
    period = dr.get("period") or {}
    if dr.get("mode") == "governance" and period.get("duration") == RETENTION_DAYS:
        print("bucket-restic default retention already governance/30d")
    else:
        call(api, tok, "b2_update_bucket", {
            "accountId": acct, "bucketId": br["bucketId"],
            "defaultRetention": {"mode": "governance",
                                 "period": {"duration": RETENTION_DAYS,
                                            "unit": "days"}}})
        print("bucket-restic default retention set to governance/30d")
    rules = br.get("lifecycleRules") or []
    if not any(r.get("daysFromHidingToDeleting") == 30 for r in rules):
        call(api, tok, "b2_update_bucket", {
            "accountId": acct, "bucketId": br["bucketId"],
            "lifecycleRules": [{"daysFromHidingToDeleting": 30,
                                "fileNamePrefix": ""}]})
        print("bucket-restic lifecycle set (hide->delete 30d)")

    if "--backfill" in sys.argv:
        retain_until = int((time.time() + RETENTION_DAYS * 86400) * 1000)
        updated = 0
        start = {}
        while True:
            page = call(api, tok, "b2_list_file_versions",
                        {"bucketId": br["bucketId"], "maxFileCount": 1000,
                         **start})
            for f in page["files"]:
                ret = (f.get("fileRetention") or {}).get("value") or {}
                if f["action"] != "upload" or ret.get("mode"):
                    continue
                call(api, tok, "b2_update_file_retention", {
                    "fileName": f["fileName"], "fileId": f["fileId"],
                    "fileRetention": {"mode": "governance",
                                      "retainUntilTimestamp": retain_until}})
                updated += 1
            if page.get("nextFileName"):
                start = {"startFileName": page["nextFileName"],
                         "startFileId": page["nextFileId"]}
            else:
                break
        print(f"backfill: {updated} unprotected versions locked for 30d")

    hb = buckets.get("bucket-hyper-backup")
    if hb and hb["fileLockConfiguration"]["value"]["isFileLockEnabled"]:
        print("WARNING: bucket-hyper-backup has file lock enabled — this "
              "contradicts the documented accepted state and may break "
              "Hyper Backup rotation")


if __name__ == "__main__":
    main()
