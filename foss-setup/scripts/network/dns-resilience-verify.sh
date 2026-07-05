#!/usr/bin/env bash
# dns-resilience-verify.sh — confirm fail-open DNS chain (dns-04)
#
# Usage:
#   ./dns-resilience-verify.sh
#   MINI_IP=192.168.10.2 NAS_IP=192.168.10.4 GW_IP=192.168.10.1 ./dns-resilience-verify.sh
#
# Refs: configs/network/dns-resilience-plan.md
set -euo pipefail

MINI_IP="${MINI_IP:-192.168.10.2}"
NAS_IP="${NAS_IP:-192.168.10.4}"
GW_IP="${GW_IP:-192.168.10.1}"
TEST_NAME="${TEST_NAME:-google.com}"
INTERNAL_NAME="${INTERNAL_NAME:-home.tabaska.us}"

log()  { printf '\033[1;34m[dns]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m  OK \033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m FAIL\033[0m %s\n' "$*"; }

RC=0
check_resolver() {
  local label="$1" server="$2" expect_internal="${3:-false}"
  if dig "@${server}" +time=3 +tries=1 "$TEST_NAME" +short 2>/dev/null | grep -qE '^[0-9]+\.'; then
    ok "${label} resolves ${TEST_NAME}"
  else
    fail "${label} cannot resolve ${TEST_NAME} (@${server})"
    RC=1
    return
  fi
  if [[ "$expect_internal" == "true" ]]; then
    if dig "@${server}" +time=3 +tries=1 "$INTERNAL_NAME" +short 2>/dev/null | grep -qE '^[0-9]+\.'; then
      ok "${label} resolves ${INTERNAL_NAME} (rewrite)"
    else
      fail "${label} missing rewrite for ${INTERNAL_NAME} (@${server})"
      RC=1
    fi
  fi
}

log "Fail-open DNS chain: mini=${MINI_IP} nas=${NAS_IP} gateway=${GW_IP}"

check_resolver "Primary (mini AdGuard)" "$MINI_IP" true
check_resolver "Secondary (NAS AdGuard)" "$NAS_IP" true
check_resolver "Fallback (gateway)" "$GW_IP" false

if [[ "$RC" -eq 0 ]]; then
  ok "All resolvers healthy."
else
  fail "One or more resolvers failed — see dns-resilience-plan.md outage runbook."
fi
exit "$RC"
