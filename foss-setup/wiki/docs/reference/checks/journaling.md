# Checks — journaling

`foss-setup/verification/checks.d/journaling.yaml` — 11 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `journaling-memos-ready`

memos journal front-end is ready on :5230

- **host:** `mini` · **severity:** `crit` · **guards task:** `journal-01` · **enabled:** True
- **expects:** `Service ready`

```bash
curl -s -m 8 http://localhost:5230/healthz
```

## `journaling-n8n-app`

n8n serves its app API on :5678 (/rest/settings 200)

- **host:** `mini` · **severity:** `crit` · **guards task:** `journal-01` · **enabled:** True
- **expects:** `^200$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:5678/rest/settings
```

## `journaling-whisper-ready`

faster-whisper (speaches) answers /health on :8010

- **host:** `mini` · **severity:** `warn` · **guards task:** `journal-01` · **enabled:** True
- **expects:** `^200$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:8010/health
```

## `journaling-coach-model-reachable`

rig llama-swap :9292 is reachable and registers dolphin-venice-24b

- **host:** `mini` · **severity:** `warn` · **guards task:** `journal-01` · **enabled:** True
- **expects:** `dolphin-venice-24b`

```bash
curl -s -m 10 http://192.168.10.12:9292/v1/models
```

## `journaling-memos-webhook-wired`

memos holds the memo.created webhook -> http://n8n:5678/webhook/journal

- **host:** `mini` · **severity:** `warn` · **guards task:** `journal-02` · **enabled:** True
- **expects:** `^WEBHOOK_OK`

```bash
curl -s -m 8 -H "Authorization:Bearer $MEMOS_API_TOKEN" http://localhost:5230/api/v1/users/btabaska/webhooks | python3 -c 'import sys,json;w=json.load(sys.stdin).get("webhooks",[]);print("WEBHOOK_OK" if any(x.get("url")=="http://n8n:5678/webhook/journal" for x in w) else "WEBHOOK_MISSING "+json.dumps(w)[:160])'
```

## `journaling-analyze-armed`

n8n journal-analyze webhook is armed (POST /webhook/journal registered)

- **host:** `mini` · **severity:** `crit` · **guards task:** `journal-03` · **enabled:** True
- **expects:** `not registered for GET requests`

```bash
curl -s -m 8 http://localhost:5678/webhook/journal
```

## `journaling-whisper-transcribes`

faster-whisper transcribes a probe clip (model loaded, not just /health)

- **host:** `mini` · **severity:** `warn` · **guards task:** `journal-04` · **enabled:** True
- **expects:** `^WHISPER_TRANSCRIBES_OK$`

```bash
curl -s -m 90 -X POST http://localhost:8010/v1/audio/transcriptions -F file=@/opt/verification/assets/whisper-probe.wav -F model=Systran/faster-whisper-small -F response_format=json | python3 -c 'import sys,json;t=json.load(sys.stdin).get("text","").strip();print("WHISPER_TRANSCRIBES_OK" if t else "WHISPER_EMPTY")'
```

## `journaling-owui-save-fn-installed`

rig Open WebUI holds the Save-to-Journal action (installed + active)

- **host:** `mini` · **severity:** `warn` · **guards task:** `journal-05` · **enabled:** True
- **expects:** `^OWUI_SAVE_FN_OK$`

```bash
curl -s -m 8 -H "Authorization:Bearer $OWUI_API_KEY" "$OWUI_URL/api/v1/functions/id/save_to_journal" | python3 -c 'import sys,json;f=json.load(sys.stdin);print("OWUI_SAVE_FN_OK" if (f.get("is_active") and f.get("type")=="action") else "OWUI_SAVE_FN_DRIFT "+json.dumps({"active":f.get("is_active"),"type":f.get("type")}))'
```

## `journaling-owui-coach-preset`

rig Open WebUI holds the Journaling Coach preset (base dolphin-venice, active)

- **host:** `mini` · **severity:** `warn` · **guards task:** `journal-05` · **enabled:** True
- **expects:** `^OWUI_COACH_PRESET_OK$`

```bash
curl -s -m 8 -H "Authorization:Bearer $OWUI_API_KEY" "$OWUI_URL/api/v1/models/model?id=journaling-coach" | python3 -c 'import sys,json;m=json.load(sys.stdin);print("OWUI_COACH_PRESET_OK" if (m.get("base_model_id")=="dolphin-venice" and m.get("is_active")) else "OWUI_COACH_PRESET_DRIFT "+json.dumps({"base":m.get("base_model_id"),"active":m.get("is_active")}))'
```

## `journaling-loop-e2e`

journal loop end-to-end: one #journal memo -> exactly one reflection comment

- **host:** `mini` · **severity:** `warn` · **guards task:** `journal-06` · **enabled:** True
- **expects:** `^E2E_(OK|SKIP_COACH_UNAVAILABLE)$`

```bash
python3 /opt/verification/bin/journaling-e2e.py
```

## `journaling-igdb-enrich`

IGDB #gamelog enrichment reaches Twitch OAuth + IGDB from the n8n container

- **host:** `mini` · **severity:** `warn` · **guards task:** `journal-07` · **enabled:** True
- **expects:** `^IGDB_(ENRICH_OK|SKIP_DISABLED)$`

```bash
python3 /opt/verification/bin/journaling-igdb-enrich.py
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
