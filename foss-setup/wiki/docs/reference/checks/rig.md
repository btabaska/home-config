# Checks — rig

`foss-setup/verification/checks.d/rig.yaml` — 21 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `rig-ollama`

ollama SHIM answers on rig:11434 (HA Assist + Obsidian compat)

- **host:** `url` · **severity:** `warn` · **guards task:** `ai-01` · **enabled:** True
- **expects:** `^200$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://cachyos.tailb31641.ts.net:11434/api/tags
```

## `rig-litellm`

litellm proxy answers on rig:4000 (401 without key = up)

- **host:** `url` · **severity:** `warn` · **guards task:** `game-10` · **enabled:** True
- **expects:** `^(200|401)$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://cachyos.tailb31641.ts.net:4000/v1/models
```

## `rig-open-webui`

open-webui answers on rig:3000

- **host:** `url` · **severity:** `warn` · **guards task:** `game-10` · **enabled:** True
- **expects:** `^200$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://cachyos.tailb31641.ts.net:3000/
```

## `rig-ollama-models`

ollama shim holds HA Assist's model (llama3.2:3b)

- **host:** `url` · **severity:** `warn` · **guards task:** `ai-01` · **enabled:** True
- **expects:** `llama3.2:3b`

```bash
curl -s -m 8 http://cachyos.tailb31641.ts.net:11434/api/tags
```

## `rig-llama-swap`

llama-swap model server healthy on rig:9292

- **host:** `url` · **severity:** `warn` · **guards task:** `ai-01` · **enabled:** True
- **expects:** `^OK$`

```bash
curl -s -m 8 http://cachyos.tailb31641.ts.net:9292/health
```

## `rig-llama-swap-models`

llama-swap serves the coder lineup (bake-off winner + embedder)

- **host:** `url` · **severity:** `warn` · **guards task:** `ai-01` · **enabled:** True
- **expects:** `(?s)qwen3.6-35b-a3b.*qwen3-embed|qwen3-embed.*qwen3.6-35b-a3b`

```bash
curl -s -m 8 http://cachyos.tailb31641.ts.net:9292/v1/models
```

## `rig-ai-gpu-yield`

llama-swap loads on demand + VRAM frees on unload (gaming yield)

- **host:** `rig` · **severity:** `warn` · **guards task:** `ai-01` · **enabled:** True
- **expects:** `YIELD_OK`

```bash
curl -sm 90 http://localhost:9292/v1/chat/completions -H 'Content-Type: application/json' -d '{"model":"fast-3b","messages":[{"role":"user","content":"Say OK"}],"max_tokens":5}' | grep -q '"content"' && { curl -sm 30 -X POST http://localhost:9292/api/models/unload -o /dev/null || true; } && sleep 3 && v=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits) && { [ "$v" -lt 3000 ] && echo "YIELD_OK vram=${v}MiB" || echo "YIELD_FAIL vram=${v}MiB"; }
```

## `rig-fleet-mcp`

fleet-mcp ops tool server active on rig:8765

- **host:** `rig` · **severity:** `warn` · **guards task:** `ai-01` · **enabled:** True
- **expects:** `svc=active http=406`

```bash
echo "svc=$(systemctl is-active fleet-mcp) http=$(curl -sm 5 -o /dev/null -w '%{http_code}' http://localhost:8765/mcp)"
```

## `rig-mcpo-fleet-tools`

mcpo bridges the fleet ops tools to OWUI (gpu_status route present)

- **host:** `url` · **severity:** `warn` · **guards task:** `ai-01` · **enabled:** True
- **expects:** `gpu_status`

```bash
curl -s -m 8 http://cachyos.tailb31641.ts.net:8000/fleet/openapi.json
```

## `rig-ops-agent-e2e`

ops agent answers a canned question via fleet tools (bounded loop)

- **host:** `rig` · **severity:** `warn` · **guards task:** `ai-01` · **enabled:** True
- **expects:** `(?i)(vram|mib|gpu)`

```bash
set -a && . ~/.config/fleet-mcp/env && set +a && timeout 180 /opt/llm/fleet-venv/bin/python ~/Documents/GitHub/local-ai-tooling/ops/ops_probe.py --quiet --max-turns 4 "Use the gpu_status tool and report how much VRAM is used right now."
```

## `rig-ollama-keepalive`

ollama KEEP_ALIVE=0 on rig (VRAM frees after each request — GPU contention)

- **host:** `rig` · **severity:** `warn` · **guards task:** `game-13` · **enabled:** True
- **expects:** `OLLAMA_KEEP_ALIVE=0(?![.0-9a-zA-Z])`

```bash
systemctl show ollama -p Environment
```

## `rig-gpu-power-tune`

rig GPU power-tune applied (persistence on + gpu-power-tune.service active)

- **host:** `rig` · **severity:** `warn` · **guards task:** `game-09` · **enabled:** True
- **expects:** `svc=active persist=Enabled`

```bash
echo "svc=$(systemctl is-active gpu-power-tune.service) persist=$(nvidia-smi --query-gpu=persistence_mode --format=csv,noheader | tr -d ' ')"
```

## `rig-music-no-flac`

rig ~/Music holds no FLAC (ALAC-only mirror, no dupes — media-06)

- **host:** `rig` · **severity:** `warn` · **guards task:** `media-06` · **enabled:** True
- **expects:** `^0$`

```bash
find /home/btabaska/Music -type f -iname '*.flac' 2>/dev/null | wc -l | tr -d ' '
```

## `palworld-rest-liveness`

palworld game server alive (REST :8212 reports serverfps)

- **host:** `url` · **severity:** `warn` · **guards task:** `game-10` · **enabled:** True
- **expects:** `"serverfps":`

```bash
curl -sm 8 -u "admin:$PALWORLD_ADMIN_PASSWORD" http://cachyos.tailb31641.ts.net:8212/v1/api/metrics
```

## `playit-java-public`

Minecraft Java public path (playit edge 69.9.181.17:1105, real status ping)

- **host:** `url` · **severity:** `warn` · **guards task:** `game-10` · **enabled:** True
- **expects:** `"version"`

```bash
for i in 1 2 3 4; do python3 /opt/verification/bin/mc-status-ping.py 69.9.181.17 1105 minecraft.tabaska.us && { echo "pass on try $i/4"; break; }; sleep 3; done
```

## `playit-bedrock-public`

Minecraft Bedrock public path (playit edge 69.9.181.17:1111, RakNet ping)

- **host:** `url` · **severity:** `warn` · **guards task:** `game-10` · **enabled:** True
- **expects:** `version`

```bash
for i in 1 2 3 4; do python3 /opt/verification/bin/mc-bedrock-ping.py 69.9.181.17 1111 && { echo "pass on try $i/4"; break; }; sleep 3; done
```

## `rig-mcpo`

mcpo tool host serving on rig:8000 (OWUI tools)

- **host:** `url` · **severity:** `warn` · **guards task:** `game-10` · **enabled:** True
- **expects:** `^200$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://cachyos.tailb31641.ts.net:8000/docs
```

## `rig-ai-e2e`

litellm end-to-end completion (gateway -> llama-swap -> model)

- **host:** `url` · **severity:** `warn` · **guards task:** `game-10` · **enabled:** True
- **expects:** `"finish_reason"`

```bash
curl -s -m 50 -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H "Content-Type: application/json" -d '{"model":"utility","messages":[{"role":"user","content":"Say OK"}],"max_tokens":5}' http://cachyos.tailb31641.ts.net:4000/v1/chat/completions
```

## `rig-suspend-masked`

rig systemd sleep targets masked (24/7 box must never suspend)

- **host:** `rig` · **severity:** `crit` · **guards task:** `game-08` · **enabled:** True
- **expects:** `^masked\s*$`

```bash
systemctl is-enabled sleep.target suspend.target hibernate.target hybrid-sleep.target | sort -u | tr '\n' ' '
```

## `rig-root-fs-writable`

rig root + /home are READ-WRITE (real write probe — catches silent RO remount)

- **host:** `rig` · **severity:** `crit` · **guards task:** `fix-20` · **enabled:** True
- **expects:** `write=OK root=rw home=rw`

```bash
p="/home/btabaska/.verify-rw-probe"; if ( : > "$p" ) 2>/dev/null; then rm -f "$p"; w=OK; else w=FAIL; fi; echo "write=$w root=$(findmnt -no OPTIONS / | cut -d, -f1) home=$(findmnt -no OPTIONS /home | cut -d, -f1)"
```

## `rig-litellm-vkey-e2e`

litellm answers a VIRTUAL-key completion (DB-auth path — catches litellm-db down that master-key probes miss)

- **host:** `url` · **severity:** `warn` · **guards task:** `fix-20` · **enabled:** True
- **expects:** `"finish_reason"`

```bash
curl -s -m 50 -H "Authorization: Bearer $LITELLM_VKEY" -H "Content-Type: application/json" -d '{"model":"utility","messages":[{"role":"user","content":"Say OK"}],"max_tokens":5}' http://cachyos.tailb31641.ts.net:4000/v1/chat/completions
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
