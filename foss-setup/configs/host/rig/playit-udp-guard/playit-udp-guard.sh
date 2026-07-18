#!/usr/bin/env bash
# playit-udp-guard — end-to-end Bedrock-UDP tunnel probe + self-heal (fix-34 M30).
#
# The playit agent's UDP claims historically break ~daily ("got unexpected
# response from register request ... UdpChannelDetails") and stay broken until
# the agent restarts; TCP keeps working so port-liveness checks miss it. This
# guard probes the CONSUMER path — a RakNet unconnected ping to the public
# Bedrock tunnel — and restarts the agent only when the evidence points at it:
#
#   local 19132 dead            -> Geyser/AMP problem, do NOT touch playit, alert
#   local ok + public ok        -> healthy, ping healthchecks dead-man
#   local ok + public dead      -> tunnel path broken -> restart playit once
#                                  (skipped if the container is <10 min old,
#                                  so a broken upstream can't make us flap)
#
# Deployed to /usr/local/bin/playit-udp-guard.sh (root 0755) on rig; timer runs
# it every 10 min. PING_URL (healthchecks 'playit-udp-rig') comes from
# /etc/playit-udp-guard.env (root 0600, vault healthchecks.playit_udp_rig_ping_url).
set -uo pipefail

PUBLIC_HOST="${PUBLIC_HOST:-bedrock.tabaska.us}"
PUBLIC_PORT="${PUBLIC_PORT:-1111}"
LOCAL_HOST="${LOCAL_HOST:-127.0.0.1}"
LOCAL_PORT="${LOCAL_PORT:-19132}"
CONTAINER="${CONTAINER:-playit}"
MIN_UPTIME_S="${MIN_UPTIME_S:-600}"
PING_URL="${PING_URL:-}"

raknet_ping() { # host port -> exit 0 on unconnected-pong
  python3 - "$1" "$2" <<'PY'
import socket, struct, sys
host, port = sys.argv[1], int(sys.argv[2])
MAGIC = bytes.fromhex("00ffff00fefefefefdfdfdfd12345678")
pkt = b"\x01" + struct.pack(">Q", 0) + MAGIC + struct.pack(">Q", 0x3412)
for attempt in range(2):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(5)
    try:
        s.sendto(pkt, (host, port))
        data, _ = s.recvfrom(4096)
        if data[:1] == b"\x1c":
            sys.exit(0)
    except OSError:
        pass
    finally:
        s.close()
sys.exit(1)
PY
}

hc_ping() { # append-path ("" or /fail) message
  [ -n "$PING_URL" ] || return 0
  curl -fsS -m 10 --retry 2 --data-raw "$2" "${PING_URL}$1" >/dev/null || true
}

if ! raknet_ping "$LOCAL_HOST" "$LOCAL_PORT"; then
  echo "local Geyser ${LOCAL_HOST}:${LOCAL_PORT} not answering RakNet ping — AMP/Geyser problem, not touching playit"
  hc_ping /fail "local geyser 19132 dead"
  exit 1
fi

if raknet_ping "$PUBLIC_HOST" "$PUBLIC_PORT"; then
  echo "tunnel healthy: ${PUBLIC_HOST}:${PUBLIC_PORT} answered through playit"
  hc_ping "" "ok"
  exit 0
fi

# local ok, public dead -> playit UDP path is the suspect
started=$(docker inspect "$CONTAINER" --format '{{.State.StartedAt}}' 2>/dev/null) || {
  echo "public probe failed and container ${CONTAINER} not inspectable"
  hc_ping /fail "public dead, container missing"
  exit 1
}
uptime_s=$(( $(date +%s) - $(date -d "$started" +%s) ))
if [ "$uptime_s" -lt "$MIN_UPTIME_S" ]; then
  echo "public probe failed but ${CONTAINER} only ${uptime_s}s old — flap guard, not restarting"
  hc_ping /fail "public dead, restart throttled (uptime ${uptime_s}s)"
  exit 1
fi

echo "public probe failed with healthy local origin — restarting ${CONTAINER} (uptime ${uptime_s}s)"
docker restart "$CONTAINER" >/dev/null
sleep 45
if raknet_ping "$PUBLIC_HOST" "$PUBLIC_PORT"; then
  echo "recovered after restart"
  hc_ping "" "recovered after playit restart"
  exit 0
fi
echo "still dead after restart — escalating"
hc_ping /fail "public dead even after playit restart"
exit 1
