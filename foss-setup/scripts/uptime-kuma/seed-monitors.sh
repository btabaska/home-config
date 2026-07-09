#!/usr/bin/env bash
# Seed Uptime Kuma (v2.x, embedded MariaDB) with the full fleet monitor set
# + a default ntfy notification channel wired to every monitor.
#
# Run on the Mac mini (where the uptime-kuma container lives):
#   NTFY_TOKEN=tk_... bash seed-monitors.sh
#
# - Idempotent: monitors/notification matched by name; links deduped.
# - Direct host:port probes (no Caddy/DNS dependency) + 3 full-chain https
#   vhost checks + DNS + ping monitors.
# - v2 loads monitors at startup only -> restarts the container at the end.
#
# Status-code choices were probed live 2026-07-09 (see handoff):
#   *arr/login-redirect apps 3xx, mcpo 404 on /, apollo https 307 self-signed.
set -euo pipefail

CONTAINER="${KUMA_CONTAINER:-uptime-kuma}"
SOCKET="/app/data/run/mariadb.sock"
DB="kuma"
USER_ID=1
INTERVAL=60
RETRY=3
RETRY_INTERVAL=60
NTFY_TOKEN="${NTFY_TOKEN:?set NTFY_TOKEN (vault: ntfy.kuma_token)}"
# Optional: Palworld REST-API monitor (vault: palworld.admin_password). If unset,
# the Palworld monitor is skipped. gamedig-in-Kuma can't send the REST Basic auth,
# so this is a plain HTTP monitor against /v1/api/info with basic auth instead.
PALWORLD_ADMIN_PW="${PALWORLD_ADMIN_PW:-}"
NTFY_URL="${NTFY_URL:-http://ntfy:80}"     # kuma + ntfy share the edge network
NTFY_TOPIC="${NTFY_TOPIC:-homelab-alerts}" # phone is subscribed to this topic
NOTIF_NAME="ntfy → ${NTFY_TOPIC}"

MINI=192.168.10.2
NAS=192.168.10.4
RIG=192.168.10.12
HA=192.168.10.50
GW=192.168.10.1
SEEDBOX=100.119.134.94  # betty (Tailscale)

A_OK='["200-299"]'
A_3XX='["200-299","300-399"]'
A_404='["200-299","300-399","404"]'

sql() { docker exec "$CONTAINER" mariadb --socket="$SOCKET" "$DB" -N -e "$1"; }

exists() { [[ "$(sql "SELECT COUNT(*) FROM monitor WHERE name='${1//\'/\\\'}';")" -gt 0 ]]; }

add_http() { # name url accept [ignore_tls]
  local name="$1" url="$2" accept="$3" itls="${4:-0}"
  exists "$name" && { echo "skip  $name"; return 0; }
  sql "INSERT INTO monitor (name, active, user_id, \`interval\`, url, type, maxretries, retry_interval, accepted_statuscodes_json, method, ignore_tls)
       VALUES ('${name//\'/\\\'}', 1, ${USER_ID}, ${INTERVAL}, '${url}', 'http', ${RETRY}, ${RETRY_INTERVAL}, '${accept}', 'GET', ${itls});"
  echo "added $name → $url"
}

add_http_basic() { # name url accept user pass
  local name="$1" url="$2" accept="$3" user="$4" pass="$5"
  exists "$name" && { echo "skip  $name"; return 0; }
  sql "INSERT INTO monitor (name, active, user_id, \`interval\`, url, type, maxretries, retry_interval, accepted_statuscodes_json, method, auth_method, basic_auth_user, basic_auth_pass)
       VALUES ('${name//\'/\\\'}', 1, ${USER_ID}, ${INTERVAL}, '${url}', 'http', ${RETRY}, ${RETRY_INTERVAL}, '${accept}', 'GET', 'basic', '${user//\'/\\\'}', '${pass//\'/\\\'}');"
  echo "added $name → $url (basic auth)"
}

add_ping() { # name host
  local name="$1" host="$2"
  exists "$name" && { echo "skip  $name"; return 0; }
  sql "INSERT INTO monitor (name, active, user_id, \`interval\`, hostname, type, maxretries, retry_interval, accepted_statuscodes_json, method)
       VALUES ('${name//\'/\\\'}', 1, ${USER_ID}, ${INTERVAL}, '${host}', 'ping', ${RETRY}, ${RETRY_INTERVAL}, '${A_OK}', 'GET');"
  echo "added $name → ping ${host}"
}

add_dns() { # name query server port
  local name="$1" query="$2" server="$3" port="$4"
  exists "$name" && { echo "skip  $name"; return 0; }
  sql "INSERT INTO monitor (name, active, user_id, \`interval\`, hostname, port, dns_resolve_server, dns_resolve_type, type, maxretries, retry_interval, accepted_statuscodes_json, method)
       VALUES ('${name//\'/\\\'}', 1, ${USER_ID}, ${INTERVAL}, '${query}', ${port}, '${server}', 'A', 'dns', ${RETRY}, ${RETRY_INTERVAL}, '${A_OK}', 'GET');"
  echo "added $name → dns ${query} @${server}:${port}"
}

add_port() { # name host port — TCP connect check (docker DNS names OK on the edge net)
  local name="$1" host="$2" port="$3"
  exists "$name" && { echo "skip  $name"; return 0; }
  sql "INSERT INTO monitor (name, active, user_id, \`interval\`, hostname, port, type, maxretries, retry_interval, accepted_statuscodes_json, method)
       VALUES ('${name//\'/\\\'}', 1, ${USER_ID}, ${INTERVAL}, '${host}', ${port}, 'port', ${RETRY}, ${RETRY_INTERVAL}, '${A_OK}', 'GET');"
  echo "added $name → tcp ${host}:${port}"
}

main() {
  docker ps --format '{{.Names}}' | grep -qx "$CONTAINER" || { echo "no $CONTAINER container" >&2; exit 1; }

  # ---- mini services (direct) ----
  add_http "Mini MeTube"       "http://${MINI}:8081"  "$A_OK"
  add_http "Mini Pinchflat"    "http://${MINI}:8945"  "$A_OK"
  add_http "Mini Seerr"        "http://${MINI}:5055"  "$A_3XX"
  add_http "Mini MusicSeerr"   "http://${MINI}:8688"  "$A_OK"
  add_http "Mini Libreseerr"   "http://${MINI}:8789"  "$A_3XX"
  add_http "Mini Tautulli"     "http://${MINI}:8181"  "$A_3XX"
  add_http "Mini Navidrome"    "http://${MINI}:4533"  "$A_3XX"
  add_http "Mini Paperless"    "http://${MINI}:8000"  "$A_3XX"
  add_http "Mini Wallabag"     "http://${MINI}:8085"  "$A_3XX"
  add_http "Mini Miniflux"     "http://${MINI}:8082"  "$A_OK"
  add_http "Mini Mealie"       "http://${MINI}:9000"  "$A_OK"
  add_http "Mini Homepage"     "http://${MINI}:3010"  "$A_OK"
  add_http "Mini Healthchecks" "http://${MINI}:8001"  "$A_3XX"
  add_http "Mini Dockge"       "http://${MINI}:5001"  "$A_OK"
  add_http "Mini Forgejo"      "http://${MINI}:3030"  "$A_OK"
  add_http "Mini ntfy"         "http://${MINI}:8080"  "$A_OK"
  add_http "Mini Beszel"       "http://${MINI}:8090"  "$A_OK"

  # ---- rig services ----
  add_http "Rig Open WebUI"    "http://${RIG}:3000"   "$A_OK"
  add_http "Rig LiteLLM"       "http://${RIG}:4000/health/liveliness" "$A_OK"
  add_http "Rig Ollama"        "http://${RIG}:11434"  "$A_OK"
  add_http "Rig MCPO"          "http://${RIG}:8000"   "$A_404"
  add_http "Rig Apollo"        "https://${RIG}:47990" "$A_3XX" 1

  # ---- other hosts ----
  add_http "HA Home Assistant" "http://${HA}:8123"    "$A_OK"
  add_http "Seedbox Deluge"    "http://${SEEDBOX}:8112" "$A_OK"
  add_http "Seedbox slskd"     "http://${SEEDBOX}:5030" "$A_3XX"

  # ---- full-chain (DNS + Caddy + TLS + service); also gives cert-expiry alerts ----
  add_http "Edge Homepage (vhost)"    "https://home.tabaska.us"  "$A_OK"
  add_http "Edge Vaultwarden (vhost)" "https://vault.tabaska.us" "$A_OK"
  add_http "Edge Books/CWA (vhost)"   "https://books.tabaska.us" "$A_3XX"

  # ---- DNS resolution ----
  # mini AdGuard/unbound: UDP hairpin container→host-IP times out, so those two
  # are TCP checks by container name on the shared edge network (probed 2026-07-09).
  add_port "DNS AdGuard mini" "adguardhome" 53
  add_dns  "DNS AdGuard NAS"  "home.tabaska.us" "${NAS}" 53
  add_port "DNS Unbound mini" "unbound" 5335

  # ---- game servers ----
  add_port "Rig Minecraft Java" "${RIG}" 25565   # Bedrock/Geyser is UDP 19132 (not probeable here)
  # Palworld: game traffic is UDP 8211 (unprobeable connectionless); liveness via
  # its REST API on 8212 (admin basic auth). Only added if PALWORLD_ADMIN_PW is set.
  if [[ -n "$PALWORLD_ADMIN_PW" ]]; then
    add_http_basic "Rig Palworld" "http://${RIG}:8212/v1/api/info" "$A_OK" "admin" "$PALWORLD_ADMIN_PW"
  else
    echo "skip  Rig Palworld (PALWORLD_ADMIN_PW unset)"
  fi

  # ---- host reachability ----
  add_ping "Ping NAS"     "${NAS}"
  add_ping "Ping Rig"     "${RIG}"
  add_ping "Ping HA"      "${HA}"
  add_ping "Ping Gateway" "${GW}"
  add_ping "Ping Seedbox" "${SEEDBOX}"

  # ---- ntfy notification channel (default, linked to every monitor) ----
  local nid
  nid=$(sql "SELECT id FROM notification WHERE name='${NOTIF_NAME//\'/\\\'}' LIMIT 1;")
  if [[ -z "$nid" ]]; then
    local cfg
    cfg=$(printf '{"name":"%s","type":"ntfy","isDefault":true,"applyExisting":true,"ntfyAuthenticationMethod":"accessToken","ntfyaccesstoken":"%s","ntfytopic":"%s","ntfyPriority":4,"ntfyserverurl":"%s","ntfyusername":"","ntfypassword":""}' \
      "$NOTIF_NAME" "$NTFY_TOKEN" "$NTFY_TOPIC" "$NTFY_URL")
    sql "INSERT INTO notification (name, active, user_id, is_default, config) VALUES ('${NOTIF_NAME//\'/\\\'}', 1, ${USER_ID}, 1, '${cfg//\'/\\\'}');"
    nid=$(sql "SELECT id FROM notification WHERE name='${NOTIF_NAME//\'/\\\'}' LIMIT 1;")
    echo "added notification '$NOTIF_NAME' (id $nid)"
  else
    echo "skip  notification '$NOTIF_NAME' (id $nid)"
  fi
  sql "INSERT INTO monitor_notification (monitor_id, notification_id)
       SELECT m.id, ${nid} FROM monitor m
       WHERE NOT EXISTS (SELECT 1 FROM monitor_notification mn WHERE mn.monitor_id = m.id AND mn.notification_id = ${nid});"
  echo "linked notification to all monitors ($(sql "SELECT COUNT(*) FROM monitor_notification WHERE notification_id=${nid};") links)"

  echo; echo "Restarting Uptime Kuma (v2 loads monitors at startup only)..."
  docker restart "$CONTAINER" >/dev/null
  sleep 45
  echo "Latest heartbeat per monitor (status: 1=up 0=down 2=pending):"
  sql "SELECT m.id, m.name, COALESCE(h.status,'-') , COALESCE(LEFT(h.msg,60),'') FROM monitor m
       LEFT JOIN heartbeat h ON h.id = (SELECT MAX(h2.id) FROM heartbeat h2 WHERE h2.monitor_id = m.id)
       ORDER BY m.id;"
}

main "$@"
