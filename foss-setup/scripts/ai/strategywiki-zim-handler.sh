#!/bin/sh
# strategywiki-zim-handler.sh — lai-15 completion handler (runs on the MINI, invoked by
# build-strategywiki-zim.sh once mwoffliner exits 0).
#
# Steps, each logged to the parent build.log and reflected in $BASE/status:
#   1. locate the produced .zim in $OUT
#   2. VALIDATING — zimcheck integrity + checksum (kiwix-tools, same image+digest the
#      NAS refresh script pins) — a corrupt ZIM must never reach the library
#   3. PUSHING    — stream to NAS /volume1/zim/.incoming over ssh (SFTP/scp are disabled
#      on the NAS), md5-verify, then atomic mv into /volume1/zim (same volume)
#   4. PUSHED_AWAITING_REFRESH:<file> — the nightly DSM "kiwix library refresh" (05:15)
#      rebuilds library.xml and bounces kiwix-serve; the file is then live LAN/tailnet
#      (kiwix.tabaska.us + NAS :8092) and openzim-mcp sees it via the rig RO mount.
#
# NAS filename is normalized to strategywiki_en_all_nopic_<YYYY-MM>.zim regardless of
# what mwoffliner named the file, so the verification check + runbook match.
set -u

BASE=/opt/mwoffliner/lai-15
OUT=$BASE/out
STATUS=$BASE/status
NAS=btabaska@192.168.10.4
SSH="ssh -o BatchMode=yes -o ConnectTimeout=20 -o StrictHostKeyChecking=accept-new"
# kiwix-tools 3.8.2 (has zimcheck) — same digest the NAS kiwix-library-refresh.sh pins.
TOOLS=ghcr.io/kiwix/kiwix-tools:3.8.2@sha256:40ab5f450231836321d6a1e417006033db5883f883d08e85b246d2ecf8840a75
DEST_NAME="strategywiki_en_all_nopic_$(date +%Y-%m).zim"

say() { printf '[%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*"; }
setstatus() { printf '%s\n' "$1" > "$STATUS"; }

zim=$(ls -1t "$OUT"/*.zim 2>/dev/null | head -1)
if [ -z "$zim" ] || [ ! -s "$zim" ]; then
  setstatus "FAILED:no_zim_output"; say "handler: no non-empty .zim in $OUT"; exit 1
fi
say "handler: produced ZIM $zim ($(du -h "$zim" | cut -f1))"

setstatus VALIDATING
if docker run --rm -v "$OUT":/out "$TOOLS" zimcheck -i -c "/out/$(basename "$zim")"; then
  say "handler: zimcheck integrity+checksum OK"
else
  setstatus "FAILED:zimcheck"; say "handler: zimcheck FAILED for $zim"; exit 1
fi

setstatus PUSHING
md5_local=$(md5sum "$zim" | cut -d' ' -f1)
say "handler: streaming to NAS .incoming/$DEST_NAME (md5=$md5_local)"
if ! $SSH "$NAS" "cat > /volume1/zim/.incoming/$DEST_NAME" < "$zim"; then
  setstatus "FAILED:nas_push"; say "handler: NAS stream failed"; exit 1
fi
md5_remote=$($SSH "$NAS" "md5sum /volume1/zim/.incoming/$DEST_NAME 2>/dev/null" | cut -d' ' -f1)
if [ "$md5_local" != "$md5_remote" ]; then
  setstatus "FAILED:md5_mismatch"
  say "handler: md5 mismatch local=$md5_local remote=$md5_remote — removing partial"
  $SSH "$NAS" "rm -f /volume1/zim/.incoming/$DEST_NAME"
  exit 1
fi
say "handler: md5 verified on NAS ($md5_remote); atomic mv into /volume1/zim"
$SSH "$NAS" "mv /volume1/zim/.incoming/$DEST_NAME /volume1/zim/$DEST_NAME"

setstatus "PUSHED_AWAITING_REFRESH:$DEST_NAME"
say "handler: DONE — $DEST_NAME on NAS /volume1/zim."
say "handler: nightly kiwix refresh (05:15) folds it into library.xml automatically."
say "handler: force it live now (optional, needs vault sudo.rig? no — NAS vault pw):"
say "  printf '%s\\n' \"\$PW\" | ssh nas 'sudo -S sh /volume1/docker/kiwix/kiwix-library-refresh.sh'"
