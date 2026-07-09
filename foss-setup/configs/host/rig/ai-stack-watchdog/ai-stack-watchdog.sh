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
  docker exec open-webui python3 -c "
import urllib.request
urllib.request.urlopen('http://host.docker.internal:11434/api/version', timeout=8)
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
      --data-raw "container->host ollama probe failed (open-webui -> host.docker.internal:11434); check rig UFW 172.16.0.0/12 allow on 11434, ollama.service, docker" \
      "$PING_URL/fail"
  fi
fi
