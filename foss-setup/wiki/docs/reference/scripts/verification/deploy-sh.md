# `deploy.sh`

> Deploy the verification suite to mini:/opt/verification — reproducibly, from git.

**Path:** `foss-setup/scripts/verification/deploy.sh` · **Category:** [verification](index.md) · **Type:** Bash

## Synopsis

```
scripts/verification/deploy.sh            # deploy
```

## What it does

```text
 Deploy the verification suite to mini:/opt/verification — reproducibly, from git.

 WHY THIS SCRIPT EXISTS (quality-gate M38/M53)
 ---------------------------------------------
 The suite is NOT self-contained under foss-setup/verification/. Four scripts it
 runs live canonically elsewhere in the repo and are copied into
 /opt/verification/bin at deploy time:
   scripts/gaming/mc-status-ping.py             -> checks.d/rig.yaml  playit-java-public
   scripts/gaming/mc-bedrock-ping.py            -> checks.d/rig.yaml  playit-bedrock-public
   scripts/ai/wiki-rag-sync.py                  -> wiki-rag-sync.service ExecStart
   scripts/media/window-maint-unpackerr-rclone.sh -> window-maint units
 The old README deploy — `rsync -a --delete foss-setup/verification/ -> /opt/
 verification/` — would DELETE all four (they are not under verification/),
 breaking two live checks and a service. This script assembles a COMPLETE
 staging tree (verification/ + those four) so `--delete` is safe, strips macOS
 ._* / __pycache__ / *.pyc junk, and REFUSES to deploy if any /opt/verification/
 bin/<x> a check or unit references is not in the tree.

 Usage:  scripts/verification/deploy.sh            # deploy
         MINI=othername scripts/verification/deploy.sh
 Idempotent — safe to re-run. Requires rsync + ssh; mini has passwordless sudo.
```

## Environment / variables referenced

`EXTERNAL_BIN`, `MINI`, `REPO`, `SRC`, `STAGE`, `VERIFY_DAILY_PING_URL`

## See also

- [`stack-mirror-check.sh`](stack-mirror-check-sh.md)
- [`tracker-count-check.py`](tracker-count-check-py.md)
- [`tracker-integrity.py`](tracker-integrity-py.md)
- [`unit-drift-check.sh`](unit-drift-check-sh.md)
- [verification scripts](index.md) · [All scripts](../index.md)
