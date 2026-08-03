#!/usr/bin/env bash
# seed-status-page.sh — publish a REAL Uptime Kuma status page (fix-63 / SL23).
#
# Kuma's only published page was 'test' (0 groups, 0 monitors) — an empty
# placeholder, and per memory the Homepage Kuma widget cannot be added until a
# real page exists. This seeds a curated, grouped, PUBLISHED status page at
# https://uptime.tabaska.us/status/<slug> and (by default) removes the empty
# 'test' page. Idempotent: re-running rebuilds the groups deterministically.
#
# Kuma stores ALL config in its embedded MariaDB (no config files), so this seed
# script IS the repo-codified source of truth for the status page — same pattern
# as seed-monitors.sh. Run on the mini (where the uptime-kuma container lives):
#   bash seed-status-page.sh
set -euo pipefail

CONTAINER="${KUMA_CONTAINER:-uptime-kuma}"
SOCKET="/app/data/run/mariadb.sock"
DB="kuma"
SLUG="${STATUS_PAGE_SLUG:-fleet}"
TITLE="${STATUS_PAGE_TITLE:-Going Analogue - Fleet Status}"
DESC="Live status of the Going Analogue homelab. Grouped by function."
DROP_TEST="${DROP_TEST:-1}"   # remove the empty 'test' placeholder

sql() { docker exec "$CONTAINER" mariadb --socket="$SOCKET" "$DB" -N -e "$1"; }
esc() { printf '%s' "$1" | sed "s/'/\\\\'/g"; }

mid() { # monitor id by name (empty if missing)
  sql "SELECT id FROM monitor WHERE name='$(esc "$1")' LIMIT 1;"
}

main() {
  docker ps --format '{{.Names}}' | grep -qx "$CONTAINER" || { echo "no $CONTAINER container" >&2; exit 1; }

  # ---- upsert the status page --------------------------------------------
  local spid
  spid=$(sql "SELECT id FROM status_page WHERE slug='$(esc "$SLUG")' LIMIT 1;")
  if [[ -z "$spid" ]]; then
    sql "INSERT INTO status_page (slug, title, description, icon, theme, published, search_engine_index, show_powered_by, show_tags)
         VALUES ('$(esc "$SLUG")', '$(esc "$TITLE")', '$(esc "$DESC")', '/icon.svg', 'auto', 1, 0, 1, 0);"
    spid=$(sql "SELECT id FROM status_page WHERE slug='$(esc "$SLUG")' LIMIT 1;")
    echo "created status page '$SLUG' (id $spid)"
  else
    sql "UPDATE status_page SET title='$(esc "$TITLE")', description='$(esc "$DESC")', published=1 WHERE id=${spid};"
    echo "updated status page '$SLUG' (id $spid)"
  fi

  # ---- rebuild groups deterministically ----------------------------------
  sql "DELETE mg FROM monitor_group mg JOIN \`group\` g ON g.id=mg.group_id WHERE g.status_page_id=${spid};"
  sql "DELETE FROM \`group\` WHERE status_page_id=${spid};"

  local weight=10
  add_group() { # group_name  monitor_name...
    local gname="$1"; shift
    sql "INSERT INTO \`group\` (name, status_page_id, public, active, weight)
         VALUES ('$(esc "$gname")', ${spid}, 1, 1, ${weight});"
    local gid; gid=$(sql "SELECT id FROM \`group\` WHERE name='$(esc "$gname")' AND status_page_id=${spid} ORDER BY id DESC LIMIT 1;")
    weight=$((weight + 10))
    local mw=10 m id
    for m in "$@"; do
      id=$(mid "$m")
      if [[ -z "$id" ]]; then echo "  WARN: no monitor named '$m' — skipped" >&2; continue; fi
      sql "INSERT INTO monitor_group (monitor_id, group_id, weight, send_url) VALUES (${id}, ${gid}, ${mw}, 0);"
      mw=$((mw + 10))
    done
    echo "group '$gname' (id $gid): $# monitors"
  }

  add_group "Core Infrastructure" \
    "Ping Gateway" "Ping NAS" "Ping Rig" "DNS AdGuard mini" "DNS AdGuard NAS" \
    "Mini ntfy" "Mini Healthchecks" "Mini Forgejo" "Mini Homepage"

  add_group "Media & Photos" \
    "NAS Plex" "NAS Jellyfin" "NAS Immich" "NAS Sonarr" "NAS Radarr" \
    "Edge Books/CWA (vhost)" "Mini Navidrome"

  add_group "AI & Apps" \
    "Rig Open WebUI" "Rig LiteLLM" "Mini Memos" "Mini n8n" "Mini Mealie" "Mini Paperless"

  add_group "Game Servers" \
    "Rig Minecraft Java" "Rig Palworld" "Rig AMP panel"

  # ---- drop the empty placeholder ----------------------------------------
  if [[ "$DROP_TEST" == "1" ]]; then
    local tid; tid=$(sql "SELECT id FROM status_page WHERE slug='test' LIMIT 1;")
    if [[ -n "$tid" ]]; then
      # only delete if it really is empty (no groups) — never nuke a real page
      local tgroups; tgroups=$(sql "SELECT COUNT(*) FROM \`group\` WHERE status_page_id=${tid};")
      if [[ "$tgroups" == "0" ]]; then
        sql "DELETE FROM status_page WHERE id=${tid};"
        echo "removed empty placeholder page 'test' (id $tid)"
      else
        echo "kept 'test' (id $tid) — it has ${tgroups} groups, not empty"
      fi
    fi
  fi

  echo; echo "Restarting Uptime Kuma (status-page config is loaded at startup)..."
  docker restart "$CONTAINER" >/dev/null
  sleep 30
  echo "Published status pages + group/monitor counts:"
  sql "SELECT sp.slug, sp.published,
         (SELECT COUNT(*) FROM \`group\` g WHERE g.status_page_id=sp.id) AS groups,
         (SELECT COUNT(*) FROM monitor_group mg JOIN \`group\` g ON g.id=mg.group_id WHERE g.status_page_id=sp.id) AS monitors
       FROM status_page sp;"
}

main "$@"
