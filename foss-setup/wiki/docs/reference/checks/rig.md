# Checks — rig

`foss-setup/verification/checks.d/rig.yaml` — 10 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `rig-ollama`

ollama API answers on rig:11434

- **host:** `url` · **severity:** `warn` · **guards task:** `game-10` · **enabled:** True
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

ollama has the triage model pulled (qwen3-coder:30b)

- **host:** `url` · **severity:** `warn` · **guards task:** `game-10` · **enabled:** True
- **expects:** `qwen3-coder:30b`

```bash
curl -s -m 8 http://cachyos.tailb31641.ts.net:11434/api/tags
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

## `rig-ai-e2e`

litellm end-to-end completion (containers reach host ollama)

- **host:** `url` · **severity:** `warn` · **guards task:** `game-10` · **enabled:** True
- **expects:** `"finish_reason"`

```bash
curl -s -m 50 -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H "Content-Type: application/json" -d '{"model":"utility","messages":[{"role":"user","content":"Say OK"}],"max_tokens":5}' http://cachyos.tailb31641.ts.net:4000/v1/chat/completions
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
