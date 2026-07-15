#!/usr/bin/env bash
# ai-stack-watchdog: dead-man ping for the container->host ollama hop on the rig.
#
# Why this exists (2026-07-09): a UFW hardening pass scoped port 11434 to
# LAN+tailnet and silently dropped docker-subnet traffic, so open-webui/litellm
# could not reach host-native Ollama ("no models available") while every
# external port probe stayed green. This probe runs from INSIDE the open-webui
# container — the only vantage point that sees that hop — and reports to
# healthchecks (mini:8001, check "ai-stack-rig" -> ntfy phone alert).
# No inference: zero GPU cost, immune to model-queue latency.
#
# Deploy: /usr/local/bin/ai-stack-watchdog.sh on the rig, driven by
# ai-stack-watchdog.timer (every 10 min). PING_URL comes from
# /etc/ai-stack-watchdog.env (root:root 600; vault: healthchecks.ai_stack_rig_ping_url).
set -u
: "${PING_URL:?PING_URL not set (EnvironmentFile /etc/ai-stack-watchdog.env)}"

probe() {
  # hop 1: open-webui container -> host ollama SHIM (:11434 — HA Assist +
  # Obsidian compat since ai-01; big models moved to llama-swap in-compose).
  docker exec open-webui python3 -c "
import urllib.request
urllib.request.urlopen('http://host.docker.internal:11434/api/version', timeout=8)
" >/dev/null 2>&1 || return 1
  # hop 2 (ai-01): mcpo container -> host fleet-mcp (:8765). Same UFW failure
  # class (docker-subnet -> host INPUT); HTTP 406 on bare GET = reachable+alive,
  # only a transport error means the hop is down.
  docker exec mcpo python3 -c "
import urllib.request, urllib.error, sys
try:
    urllib.request.urlopen('http://host.docker.internal:8765/mcp', timeout=8)
except urllib.error.HTTPError:
    sys.exit(0)
except Exception:
    sys.exit(1)
" >/dev/null 2>&1
}

if probe; then
  curl -fsS -m 10 --retry 2 -o /dev/null "$PING_URL"
else
  sleep 15   # ride out a container restart / ollama service bounce
  if probe; then
    curl -fsS -m 10 --retry 2 -o /dev/null "$PING_URL"
  else
    curl -fsS -m 10 --retry 2 -o /dev/null \
      --data-raw "container->host probe failed (open-webui->:11434 ollama shim OR mcpo->:8765 fleet-mcp); check rig UFW 172.16.0.0/12 allows on 11434+8765, ollama.service, fleet-mcp.service, docker" \
      "$PING_URL/fail"
  fi
fi
