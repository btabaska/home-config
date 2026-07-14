# Checks — rig

`foss-setup/verification/checks.d/rig.yaml` — 7 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

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
