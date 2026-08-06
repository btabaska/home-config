# `build-strategywiki-zim.sh`

> lai-15: scrape StrategyWiki into a ZIM via mwoffliner,

**Path:** `foss-setup/scripts/ai/build-strategywiki-zim.sh` · **Category:** [ai](index.md) · **Type:** Bash

## What it does

```text
 build-strategywiki-zim.sh — lai-15: scrape StrategyWiki into a ZIM via mwoffliner,
 then hand off to the completion handler (validate + push to the NAS Kiwix library).

 HOST: the MINI (Ubuntu Mac mini, 192.168.10.2) — it has passwordless docker; the NAS
 does NOT (no docker socket) and mwoffliner needs Node24+Redis, which the official
 openzim/mwoffliner image bundles: its ENTRYPOINT starts redis-server inside the
 container and auto-injects --redis, so we do NOT run a separate redis or pass --redis
 (doing so errors "Parameter '--redis' can only be used once"). The heavy scrape runs
 here to spare NAS I/O (a ~115G Wikipedia download runs on the NAS sequential queue).

 This is a MULTI-HOUR low-speed scrape. Launch it DETACHED and logged:
   nohup /opt/mwoffliner/lai-15/build-strategywiki-zim.sh \
         > /opt/mwoffliner/lai-15/build.log 2>&1 &
 It chains, all logged to build.log: mwoffliner (nopic, --speed 0.5, bundled redis) ->
 strategywiki-zim-handler.sh (zimcheck + stream to NAS /volume1/zim), which the nightly
 DSM "kiwix library refresh" (05:15) folds in.

 STATUS: $BASE/status is the machine-readable pipeline state the verification check
 (strategywiki-zim-present) reads. Values: BUILDING | VALIDATING | PUSHING |
 PUSHED_AWAITING_REFRESH:<file> | FAILED:<reason>. build.log's mtime is the liveness
 heartbeat while BUILDING.

 Canonical copy: foss-setup/scripts/ai/build-strategywiki-zim.sh (this file). The mini
 copy under /opt/mwoffliner/lai-15/ is a deploy artifact — data/ZIM never in git.
 Rebuild path + rationale: wiki/docs/runbooks/strategywiki-zim.md.
```

## Environment / variables referenced

`ADMIN_EMAIL`, `BASE`, `HANDLER`, `IMG`, `OUT`, `STATUS`

## See also

- [`build-gamefaqs-zim.py`](build-gamefaqs-zim-py.md)
- [`strategywiki-zim-handler.sh`](strategywiki-zim-handler-sh.md)
- [`wiki-rag-sync.py`](wiki-rag-sync-py.md)
- [ai scripts](index.md) · [All scripts](../index.md)
