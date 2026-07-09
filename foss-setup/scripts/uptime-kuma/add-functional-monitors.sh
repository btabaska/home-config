#!/usr/bin/env bash
# Add FUNCTIONAL monitors to Uptime Kuma (v2.x, embedded MariaDB) — checks that
# verify a service *works*, not just that its port answers.
#
# Born from the 2026-07-09 "no models available" incident: every liveness
# monitor (Rig LiteLLM /health/liveliness, Rig Ollama /, Rig Open WebUI /)
# stayed green while a UFW change broke the container->host ollama hop.
#
# Run on the Mac mini (where the uptime-kuma container lives):
#   KUMA_LITELLM_KEY=sk-... bash add-functional-monitors.sh
# KUMA_LITELLM_KEY = vault litellm.kuma_monitor_key (scoped virtual key,
# models chat+utility only — NOT the master key).
#
# Idempotent: monitors matched by name; linked to the existing default ntfy
# notification; restarts the container (v2 loads monitors at startup only).
set -euo pipefail

CONTAINER="${KUMA_CONTAINER:-uptime-kuma}"
SOCKET="/app/data/run/mariadb.sock"
DB="kuma"
USER_ID=1
KUMA_LITELLM_KEY="${KUMA_LITELLM_KEY:?set KUMA_LITELLM_KEY (vault: litellm.kuma_monitor_key)}"

RIG=192.168.10.12
PLAYIT_IP=69.9.181.17   # playit premium dedicated IP (friends' path)

sql() { docker exec "$CONTAINER" mariadb --socket="$SOCKET" "$DB" -N -e "$1"; }
exists() { [[ "$(sql "SELECT COUNT(*) FROM monitor WHERE name='${1//\'/\\\'}';")" -gt 0 ]]; }

main() {
  docker ps --format '{{.Names}}' | grep -qx "$CONTAINER" || { echo "no $CONTAINER container" >&2; exit 1; }

  # LiteLLM model list with real auth: catches empty/broken model config, DB
  # loss, and auth breakage — the "no models" class — in ~1 min. Keyword
  # matches the 'chat' alias in the JSON model list. No inference, no GPU.
  local name="Rig LiteLLM models (auth)"
  if exists "$name"; then echo "skip  $name"; else
    local headers="{\"Authorization\": \"Bearer ${KUMA_LITELLM_KEY}\"}"
    sql "INSERT INTO monitor (name, active, user_id, \`interval\`, url, type, keyword, maxretries, retry_interval, accepted_statuscodes_json, method, headers)
         VALUES ('${name//\'/\\\'}', 1, ${USER_ID}, 60, 'http://${RIG}:4000/v1/models', 'keyword', '\"chat\"', 3, 60, '[\"200-299\"]', 'GET', '${headers//\'/\\\'}');"
    echo "added $name"
  fi

  # Public game path: local port checks stay green when the playit tunnel dies
  # (same silent-gap class). TCP to the dedicated IP = the path friends use.
  # 300s interval — this transits the playit edge, no need to hammer it.
  name="Playit Java public (69.9.181.17)"
  if exists "$name"; then echo "skip  $name"; else
    sql "INSERT INTO monitor (name, active, user_id, \`interval\`, hostname, port, type, maxretries, retry_interval, accepted_statuscodes_json, method)
         VALUES ('${name//\'/\\\'}', 1, ${USER_ID}, 300, '${PLAYIT_IP}', 25565, 'port', 3, 300, '[\"200-299\"]', 'GET');"
    echo "added $name"
  fi

  # Link everything to the default ntfy notification (same as seed-monitors.sh)
  local nid
  nid=$(sql "SELECT id FROM notification WHERE is_default=1 LIMIT 1;")
  [[ -n "$nid" ]] || { echo "no default notification found — run seed-monitors.sh first" >&2; exit 1; }
  sql "INSERT INTO monitor_notification (monitor_id, notification_id)
       SELECT m.id, ${nid} FROM monitor m
       WHERE NOT EXISTS (SELECT 1 FROM monitor_notification mn WHERE mn.monitor_id = m.id AND mn.notification_id = ${nid});"

  echo "Restarting Uptime Kuma (v2 loads monitors at startup only)..."
  docker restart "$CONTAINER" >/dev/null
  sleep 45
  sql "SELECT m.name, COALESCE(h.status,'-'), COALESCE(LEFT(h.msg,60),'') FROM monitor m
       LEFT JOIN heartbeat h ON h.id = (SELECT MAX(h2.id) FROM heartbeat h2 WHERE h2.monitor_id = m.id)
       WHERE m.name IN ('Rig LiteLLM models (auth)', 'Playit Java public (69.9.181.17)');"
}

main "$@"
