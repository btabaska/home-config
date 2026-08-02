#!/usr/bin/env bash
# listener-drift.sh <mini|rig|nas>   — fix-51 (fleet-sweep SM56 / SM58)
#
# Enumerate every ALL-INTERFACE (0.0.0.0 / * / [::]) TCP *listening* port on a
# fleet host and diff it against the codified intended-exposure baseline in
#   ../assets/expected-listeners/<host>.ports
# Emits ONE line:
#   LISTENER_DRIFT=NONE (host=.. baseline=.. current=.. missing_from_current=..)
#         -> current listener set is a subset of the baseline               PASS
#   LISTENER_DRIFT=<host>:<p,p,..> (NEW all-interface listener not in baseline)
#         -> a port opened that the baseline never blessed                  FAIL
#
# WHY: on 2026-07-16 a bare `nc -lvnp 9999` in a stray detached tmux session sat
# open on 0.0.0.0 on mini for 17 days with nothing watching listening sockets vs
# an expected set (fleet-sweep SM56). This is that tripwire — any NEW all-iface
# listener not in the baseline pages the daily sweep the day it appears.
#
# ADDITIVE-ONLY: a baseline port that DISAPPEARS (a service legitimately stopped)
# is reported as missing_from_current=N for context but does NOT fail — that is
# other checks' job; this one must not flap on a legit stop.
#
# SCOPE: only 0.0.0.0 / * / [::] wildcard binds count — exactly the finding's
# scope (the flat-LAN exposure, where Caddy is the auth edge). Host-IP-bound and
# 127.0.0.1 / tailscale-IP / ephemeral listeners are excluded by design, so the
# baseline stays stable and this does not churn on dynamic per-IP ports.
#
# Runs on the mini verification runner (btabaska). mini is read locally; rig/nas
# are read over the runner's existing BatchMode ssh (no sudo — listing listening
# ports needs no root, only PID attribution does, which we don't use here).
set -uo pipefail

host="${1:-}"
case "$host" in
  mini|rig|nas) ;;
  *) echo "LISTENER_DRIFT=ERROR:usage listener-drift.sh <mini|rig|nas>"; exit 0 ;;
esac

self="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
basefile="$self/../assets/expected-listeners/$host.ports"
if [ ! -f "$basefile" ]; then
  echo "LISTENER_DRIFT=ERROR:no-baseline-file:$host.ports"; exit 0
fi

# all-interface TCP LISTEN ports, one bare port number per line.
ENUM_SS='ss -Htln 2>/dev/null | awk "{print \$4}" | grep -E "^(0\.0\.0\.0|\*|\[::\]):" | sed -E "s/.*:([0-9]+)$/\1/"'
ENUM_NETSTAT='netstat -tln 2>/dev/null | awk "/^tcp/{print \$4}" | grep -E "^(0\.0\.0\.0|\*|::):" | sed -E "s/.*:([0-9]+)$/\1/"'

case "$host" in
  mini) cur="$(bash -c "$ENUM_SS")" ;;
  rig)  cur="$(ssh -o BatchMode=yes -o ConnectTimeout=10 rig "$ENUM_SS" 2>/dev/null)" ;;
  nas)  cur="$(ssh -o BatchMode=yes -o ConnectTimeout=10 nas "$ENUM_NETSTAT" 2>/dev/null)" ;;
esac

cur="$(printf '%s\n' "$cur" | grep -E '^[0-9]+$' | sort -un)"
if [ -z "$cur" ]; then
  echo "LISTENER_DRIFT=UNREACHABLE:$host (no listeners returned — host down or ssh failed)"
  exit 0
fi

# baseline: strip "# comments" and whitespace, keep bare port numbers.
base="$(sed -E 's/#.*//' "$basefile" | tr -d '[:blank:]' | grep -E '^[0-9]+$' | sort -un)"

# set differences, order-independent (grep -x -F, not comm).
unexpected="$(printf '%s\n' "$cur"  | grep -vxF -f <(printf '%s\n' "$base") | sort -n | tr '\n' ',' | sed 's/,$//')"
missing="$(  printf '%s\n' "$base" | grep -vxF -f <(printf '%s\n' "$cur")  | grep -c .)"
nb="$(printf '%s\n' "$base" | grep -c .)"
nc="$(printf '%s\n' "$cur"  | grep -c .)"

if [ -z "$unexpected" ]; then
  echo "LISTENER_DRIFT=NONE (host=$host baseline=$nb current=$nc missing_from_current=$missing)"
else
  echo "LISTENER_DRIFT=$host:$unexpected (NEW all-interface listener not in baseline — investigate: sudo ss -tlnp | grep the port)"
fi
