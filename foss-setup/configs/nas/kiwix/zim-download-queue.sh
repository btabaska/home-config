#!/bin/sh
# zim-download-queue.sh — lai-12 sequential ZIM fetcher for the NAS Kiwix library.
# Live copy: /volume1/docker/kiwix/zim-download-queue.sh (repo: foss-setup/configs/nas/kiwix/).
#
# Run as btabaska (NO sudo needed — /volume1/zim is btabaska:users):
#   nohup sh /volume1/docker/kiwix/zim-download-queue.sh >/dev/null 2>&1 &
#
# Design (deliberate):
#  - STRICTLY one download at a time + nice -n 19: NAS-heavy parallel I/O causes
#    observer effects on the rest of the fleet (fleet-sweep lesson) and hammers
#    the WAN. Sequential is the rule for this box.
#  - wget -c resumes into /volume1/zim/.incoming/, then an ATOMIC same-volume mv
#    into /volume1/zim/ on success — the library refresh script and kiwix-serve
#    only ever see COMPLETE .zim files.
#  - Idempotent: anything already in /volume1/zim is skipped, so re-running after
#    a reboot/interruption resumes exactly where it stopped (wget -c continues a
#    partial file left in .incoming/).
#  - Queue order = smallest/most-useful first: devdocs (tiny, unblock the e2e
#    check) -> iFixit -> sysadmin StackExchange -> wiktionary -> game wikis ->
#    Wikipedia en maxi LAST (115G; /volume1 had 11T free at build 2026-08-06).
#  - Versions are pinned filenames (kiwix.org keeps ~2 back-versions). Refreshing
#    later = update the names here, re-run, and let the nightly library refresh
#    pick the new files up; delete superseded ZIMs by hand afterwards.
#  - NO wikiHow (pulled from the kiwix library Jan 2025, permanently gone).
# Log: /volume1/docker/kiwix/logs/zim-download.log
set -u

ZIM=/volume1/zim
INC=$ZIM/.incoming
LOG=/volume1/docker/kiwix/logs/zim-download.log
BASE=https://download.kiwix.org/zim
LOCK=$INC/.queue.lock

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*" >> "$LOG"; }

# single-instance guard (mkdir is atomic); stale lock = no wget running
if ! mkdir "$LOCK" 2>/dev/null; then
    if ps ax | grep '[w]get -c' >/dev/null 2>&1; then
        log "another queue run is active — exiting"; exit 0
    fi
    log "stale lock (no wget running) — taking over"
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT INT TERM

# QUEUE: <subdir>/<filename> one per line, download order top to bottom.
QUEUE="
devdocs/devdocs_en_docker_2026-07.zim
devdocs/devdocs_en_bash_2026-04.zim
devdocs/devdocs_en_python_2026-08.zim
devdocs/devdocs_en_git_2026-07.zim
devdocs/devdocs_en_javascript_2026-07.zim
devdocs/devdocs_en_typescript_2026-07.zim
devdocs/devdocs_en_node_2026-08.zim
devdocs/devdocs_en_postgresql_2026-08.zim
devdocs/devdocs_en_sqlite_2026-07.zim
devdocs/devdocs_en_nginx_2026-04.zim
devdocs/devdocs_en_redis_2026-04.zim
devdocs/devdocs_en_jq_2026-07.zim
devdocs/devdocs_en_http_2026-07.zim
devdocs/devdocs_en_html_2026-07.zim
devdocs/devdocs_en_css_2026-07.zim
devdocs/devdocs_en_go_2026-07.zim
devdocs/devdocs_en_rust_2026-07.zim
devdocs/devdocs_en_vue_2026-05.zim
devdocs/devdocs_en_react_2026-05.zim
devdocs/devdocs_en_ansible_2026-04.zim
ifixit/ifixit_en_all_2025-12.zim
stack_exchange/serverfault.com_en_all_2026-02.zim
stack_exchange/unix.stackexchange.com_en_all_2026-02.zim
stack_exchange/superuser.com_en_all_2026-02.zim
stack_exchange/askubuntu.com_en_all_2026-06.zim
stack_exchange/raspberrypi.stackexchange.com_en_all_2026-02.zim
wiktionary/wiktionary_en_all_nopic_2026-05.zim
other/minecraftwiki_en_all_maxi_2026-08.zim
other/terraria.wiki.gg_en_all_2026-07a.zim
other/bulbagarden_en_all_maxi_2026-05.zim
other/stardewvalleywiki_en_all_2026-07.zim
other/dwarffortresswiki.org_en_all_maxi_2026-06.zim
wikipedia/wikipedia_en_all_maxi_2026-02.zim
"

log "=== queue start (pid $$) ==="
fail=0
for rel in $QUEUE; do
    f=${rel#*/}
    if [ -f "$ZIM/$f" ]; then
        log "skip $f (already in library)"
        continue
    fi
    # Space guard: keep >=200G margin on /volume1 before starting any file.
    avail_g=$(df -BG /volume1 | awk 'NR==2 {gsub("G","",$4); print $4}')
    if [ "${avail_g:-0}" -lt 200 ]; then
        log "ABORT before $f: only ${avail_g}G free on /volume1 (<200G margin)"
        fail=1
        break
    fi
    log "start $rel (${avail_g}G free)"
    if (cd "$INC" && nice -n 19 wget -c -q "$BASE/$rel"); then
        mv "$INC/$f" "$ZIM/$f"
        log "done $f ($(du -h "$ZIM/$f" | cut -f1))"
    else
        log "FAIL $rel (wget exit $?) — leaving partial in .incoming for resume"
        fail=1
    fi
    sleep 10
done
log "=== queue finished (fail=$fail) — run kiwix-library-refresh.sh (root) to wire new ZIMs ==="
