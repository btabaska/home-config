#!/bin/sh
# build-strategywiki-zim.sh — lai-15: scrape StrategyWiki into a ZIM via mwoffliner,
# then hand off to the completion handler (validate + push to the NAS Kiwix library).
#
# HOST: the MINI (Ubuntu Mac mini, 192.168.10.2) — it has passwordless docker; the NAS
# does NOT (no docker socket) and mwoffliner needs Node24+Redis, which the official
# openzim/mwoffliner image bundles: its ENTRYPOINT starts redis-server inside the
# container and auto-injects --redis, so we do NOT run a separate redis or pass --redis
# (doing so errors "Parameter '--redis' can only be used once"). The heavy scrape runs
# here to spare NAS I/O (a ~115G Wikipedia download runs on the NAS sequential queue).
#
# This is a MULTI-HOUR low-speed scrape. Launch it DETACHED and logged:
#   nohup /opt/mwoffliner/lai-15/build-strategywiki-zim.sh \
#         > /opt/mwoffliner/lai-15/build.log 2>&1 &
# It chains, all logged to build.log: mwoffliner (nopic, --speed 0.5, bundled redis) ->
# strategywiki-zim-handler.sh (zimcheck + stream to NAS /volume1/zim), which the nightly
# DSM "kiwix library refresh" (05:15) folds in.
#
# STATUS: $BASE/status is the machine-readable pipeline state the verification check
# (strategywiki-zim-present) reads. Values: BUILDING | VALIDATING | PUSHING |
# PUSHED_AWAITING_REFRESH:<file> | FAILED:<reason>. build.log's mtime is the liveness
# heartbeat while BUILDING.
#
# Canonical copy: foss-setup/scripts/ai/build-strategywiki-zim.sh (this file). The mini
# copy under /opt/mwoffliner/lai-15/ is a deploy artifact — data/ZIM never in git.
# Rebuild path + rationale: wiki/docs/runbooks/strategywiki-zim.md.
set -u

BASE=/opt/mwoffliner/lai-15
OUT=$BASE/out
STATUS=$BASE/status
HANDLER=$BASE/strategywiki-zim-handler.sh

MW=mw-lai15
# mwoffliner 1.17.5 (latest stable 2026-08), digest-pinned.
IMG=ghcr.io/openzim/mwoffliner:1.17.5@sha256:5dd08aedd15e2d08dc7ae22b51db097b378c2ce26643c666a363d1ca4dd9e57b
ADMIN_EMAIL=btabaska@gmail.com

mkdir -p "$OUT"
say() { printf '[%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*"; }
setstatus() { printf '%s\n' "$1" > "$STATUS"; }

setstatus BUILDING
say "lai-15 StrategyWiki ZIM build starting"
say "image=$IMG  speed=0.5  format=nopic  mwUrl=https://strategywiki.org/"

# Clean any stale prior run (idempotent re-launch).
docker rm -f "$MW" >/dev/null 2>&1 || true

# PREFLIGHT — the load-bearing gotcha (2026-08-06). StrategyWiki sits behind
# Cloudflare bot management that fingerprints and 403s Node's TLS/HTTP2 stack: curl
# (host AND in-container, any User-Agent) gets 200, but mwoffliner's entire HTTP layer
# is Node/undici -> 403 on the very first API reachability check, so --speed is
# irrelevant. Probe that exact client here: if it 403s, set a clean BLOCKED status and
# exit (no cryptic mwoffliner rc=2). If StrategyWiki ever drops the Node-fingerprint
# block, this passes and the build proceeds unchanged. See the runbook 'Blocked by
# Cloudflare' section.
say "preflight: probing MediaWiki API from the mwoffliner Node client…"
api=$(docker run --rm --entrypoint node "$IMG" -e \
  "fetch('https://strategywiki.org/w/api.php?action=query&meta=siteinfo&format=json&formatversion=2&maxlag=5').then(r=>console.log(r.status)).catch(()=>console.log('ERR'))" \
  2>/dev/null | tail -1)
if [ "$api" != "200" ]; then
  setstatus "BLOCKED:cloudflare_node_tls_fingerprint_${api}"
  say "PREFLIGHT BLOCKED: StrategyWiki API returns '$api' to the Node client (Cloudflare"
  say "  fingerprint block). curl gets 200 but mwoffliner is Node -> hard block. Nothing"
  say "  to build. Human follow-up: file the openZIM zim-request (runbook). Exiting."
  exit 3
fi
say "preflight OK: API reachable from the Node client (Cloudflare block cleared?) — building"

# The scrape. The image's entrypoint runs its own redis + injects --redis, so this is
# a single container. Choices (see runbook for full rationale):
#   --speed 0.5  polite: half the default parallel-request rate. StrategyWiki is a
#                small volunteer-run wiki (MediaWiki 1.41, open API) and we are not in
#                a hurry (async background job).
#   --format nopic  text + tables only, no images/video/audio. Strategy guides are
#                predominantly prose/tables; screenshots bloat the ZIM 3-5x for
#                marginal value. Keeps it small (~1.5GB est) + matches the fleet's
#                wiktionary nopic choice. Fulltext index is KEPT (no
#                --withoutZimFullTextIndex) so kiwix /search + openzim-mcp work.
# mwUrl base is enough: mwoffliner auto-detects the API path (/w/api.php) and article
# path (/wiki/) from siteinfo — both confirmed against StrategyWiki's API.
# --cpus caps CPU so the 49-container mini fleet is not starved; low speed keeps RAM
# bounded on the RAM-tight box.
docker run --name "$MW" --cpus=2 -v "$OUT":/out "$IMG" mwoffliner \
  --mwUrl=https://strategywiki.org/ \
  --adminEmail="$ADMIN_EMAIL" \
  --outputDirectory=/out \
  --format=nopic \
  --speed=0.5 \
  --customZimTags='strategywiki;games;guides' \
  --verbose
rc=$?
say "mwoffliner exited rc=$rc"

docker rm -f "$MW" >/dev/null 2>&1 || true

if [ "$rc" -ne 0 ]; then
  setstatus "FAILED:mwoffliner_rc_$rc"
  say "BUILD FAILED (mwoffliner rc=$rc) — see log above."
  exit "$rc"
fi

# Validate + push to the NAS. Handler owns the rest of the status machine.
sh "$HANDLER"
