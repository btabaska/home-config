# Voice (Kokoro TTS + faster-whisper STT for Open WebUI)

Runbook for the `voice-roundtrip` verification check and the OWUI voice plumbing
(lai-10, local-ai buildout). Two CPU-only backends, one on each side of the LAN:

| leg | service | where | endpoint |
|-----|---------|-------|----------|
| TTS | **Kokoro-FastAPI** `kokoro` | rig, `local-ai-tooling` compose | `http://192.168.10.12:8880/v1/audio/speech` (OWUI uses container name `http://kokoro:8880/v1`) |
| STT | **faster-whisper/speaches** `faster-whisper` | mini, `/opt/stacks/journaling` | `http://192.168.10.2:8010/v1/audio/transcriptions` (host publish `8010:8000`, journal-04) |

- **Kokoro image:** `ghcr.io/remsky/kokoro-fastapi-cpu:v0.7.1@sha256:2ff7f4d5...`
  (tag@digest pinned). **CPU variant on purpose** — the single 3090 Ti is
  contended ([local AI build](../architecture/local-ai-build.md) tenancy:
  LLM > ComfyUI > Immich-ML, no room for a fourth resident); do NOT swap in the
  `-gpu` image or add a `devices:` block. Model weights + UniDic are baked into
  the image: no volume, no runtime download, restarts are stateless. A short
  sentence synthesizes in under a second on the rig CPU.
- **Voices/model:** OpenAI-compatible; `model: kokoro`, 68 voices at
  `GET /v1/audio/voices`, fleet default `af_heart`.
- **STT model:** `Systran/faster-whisper-small` — must be **cached** in the
  speaches container (`/opt/stacks/journaling/whisper-cache`, pulled by
  journal-04 via `POST /v1/models/Systran/faster-whisper-small`). `GET
  /v1/models` 500s by design quirk — probe `/health` for liveness, or do a real
  transcription (this check does). A ~4 s clip takes ~20 s on the mini CPU.
- **Auth posture:** both backends are **keyless by design** — LAN/tailnet only,
  no Caddy vhosts, never internet-exposed. OWUI stores the placeholder key
  `none` (it just forwards it as a Bearer header both servers ignore).

## How OWUI is wired (PersistentConfig — DB wins)

Audio settings live in `webui.db` (`Admin Settings → Audio`); the
`AUDIO_TTS_*`/`AUDIO_STT_*` env seeds in the `local-ai-tooling` compose only
apply to a **fresh** volume. The live install was set via the admin API:

```
POST $OWUI_URL/api/v1/audio/config/update   (admin Bearer key, vault ai_stack.openwebui_rag_sync_api_key)
  tts: ENGINE=openai OPENAI_API_BASE_URL=http://kokoro:8880/v1 OPENAI_API_KEY=none MODEL=kokoro VOICE=af_heart SPLIT_ON=punctuation
  stt: ENGINE=openai OPENAI_API_BASE_URL=http://192.168.10.2:8010/v1 OPENAI_API_KEY=none MODEL=Systran/faster-whisper-small
```

Read it back with `GET /api/v1/audio/config`. Chat consumer routes:
`POST /api/v1/audio/speech` (OWUI → Kokoro, response **cached by request
hash** — see below) and `POST /api/v1/audio/transcriptions` (multipart file,
OWUI → mini whisper).

## The consumer check

`voice-roundtrip` (`verification/checks.d/local-ai.yaml`, host mini, **tier:
daily** — a real ~20 s CPU transcription is too heavy for the 10-min fast
sweep; severity warn; no GPU involvement, safe under any VRAM contention):

1. **Config drift gate** — `GET /api/v1/audio/config` must still show the
   exact engines/URLs/models above (UI flip-back or an OWUI volume wipe fails
   here).
2. **TTS** — synthesizes "The fleet voice loop check says pomegranate." at
   Kokoro directly; requires ≥40 KB and a `RIFF` magic (an error body is tiny
   JSON).
3. **STT** — transcribes that WAV at the mini whisper and requires
   `fleet…voice…loop…pomegranate` in the text.

It probes the backends **directly, not through OWUI's `/api/v1/audio/speech`
proxy, on purpose**: OWUI caches TTS output by request hash, so a cached MP3
would keep the proxy green while Kokoro is down.

## Troubleshooting

- **`VOICE_BAD config=DRIFT`** — someone changed Admin Settings → Audio, or the
  `open_webui_data` volume was wiped (PersistentConfig gone). Re-run the
  `audio/config/update` POST above; the compose seeds only heal a fresh volume.
- **`VOICE_BAD tts_bytes=...`** (small/not RIFF) — Kokoro down or erroring:
  `ssh rig 'docker logs kokoro --tail 50'`; redeploy from
  `~/Documents/GitHub/local-ai-tooling/docker` (`docker compose up -d kokoro`).
  A JSON error body here usually names a bad voice/model.
- **`VOICE_BAD stt=empty`** — whisper leg: `curl http://192.168.10.2:8010/health`
  (liveness), then check the model cache — if `whisper-cache/` was cleared,
  re-pull with `curl -X POST http://127.0.0.1:8010/v1/models/Systran/faster-whisper-small`
  on the mini. Container restart: journaling stack on the mini
  (`docker compose -p journaling --project-directory /opt/stacks/journaling up -d faster-whisper`).
- **Wrong/garbled transcription in chats but check green** — the check uses
  `faster-whisper-small`; if someone switched OWUI's STT `MODEL` to an uncached
  one, speaches downloads it on first use (slow first call) or errors — align
  the OWUI model with a cached one.
- **Tempted to give Kokoro the GPU?** Don't — CPU latency is sub-second for
  chat replies, and the card's tenancy policy (LLM > ComfyUI > Immich-ML) has
  no room for a fourth resident. The `-gpu` image is a deliberate non-goal.
