# rig `immich-ml` — remote ML container + night-only GPU window (glue-14)

Immich runs on the **NAS**; its ML inference (CLIP smart search, `buffalo_l` faces,
PP-OCRv5 OCR) is offloaded to the rig's **RTX 3090 Ti** via the container here
(`immich_machine_learning`, `-cuda` image, published to `192.168.10.12:3003`). The
NAS server routes ML with `machineLearning.urls = [rig, nas-local-fallback]`.

## The problem this solves

The 3090 Ti has **24 GB**. Measured fits:

| Tenant | VRAM |
|---|---|
| A 24B chat/coding/RP model (cydonia, dolphin-venice, …) @ ctx 61440 | **~22.2 GB** |
| Immich ML (SigLIP2 + buffalo_l + PP-OCRv5, resident) | **~13 GB** |

They **cannot coexist** — even weights-only they overflow 24 GB. Whoever loads
second OOMs: a 24B load dies with llama-swap `upstream command exited prematurely`
→ LiteLLM 500 in OpenWebUI; or Immich ONNX throws `Failed to allocate…`. Nothing
in the stack arbitrated the two (llama-swap only swaps LLM↔LLM; `gpu-arbiter` only
guards ComfyUI). **Photos are the lowest-priority GPU tenant**, so they yield.

## The policy — night-only rig window

Two systemd timers on the rig gate the container to **01:00–07:00 EDT**:

| Unit | Fires | `immich-ml-window.sh` action |
|---|---|---|
| `immich-ml-window-off.timer` | 07:00 EDT | pause `smartSearch`/`faceDetection`/`ocr` queues, **stop** the container |
| `immich-ml-window-on.timer` | 01:00 EDT | **start** the container, wait for `/ping`, resume the queues |

By day the container is **stopped** → Immich falls back to the **NAS iGPU**
(OpenVINO). Interactive search stays ~225 ms warm (see the NAS `.env`
`MACHINE_LEARNING_PRELOAD__CLIP__TEXTUAL` keep-warm), batch indexing of new photos
waits for the night, and the rig GPU is 100 % free for chat/coding/ComfyUI. At
night the 3090 Ti crunches any backlog while nobody is using it.

`smartSearch`/`faceDetection`/`ocr` are paused by day so new-photo indexing does
**not** grind the NAS iGPU (shared with Plex Quick Sync). Thumbnail / metadata /
video queues run on the NAS server CPU and are left alone. Interactive text search
is a live API call, not a queue job, so it keeps working by day.

## Files (canonical source — mirror live ↔ repo)

| File | Live target on rig |
|---|---|
| `compose.yaml` | `/opt/stacks/immich-ml/compose.yaml` |
| `immich-ml-window.sh` | `/usr/local/bin/immich-ml-window.sh` (`install -m 755`) |
| `immich-ml-window@.service` | `/etc/systemd/system/immich-ml-window@.service` |
| `immich-ml-window-on.timer` | `/etc/systemd/system/immich-ml-window-on.timer` (enable) |
| `immich-ml-window-off.timer` | `/etc/systemd/system/immich-ml-window-off.timer` (enable) |
| `immich-ml-window.env.example` | `/etc/immich-ml-window.env` (fill from vault, chmod 600) |

Deploy the units:
```
sudo install -m 755 immich-ml-window.sh /usr/local/bin/
sudo cp immich-ml-window@.service immich-ml-window-*.timer /etc/systemd/system/
sudo install -m 600 /dev/stdin /etc/immich-ml-window.env   # fill IMMICH_API_KEY from vault
sudo systemctl daemon-reload
sudo systemctl enable --now immich-ml-window-on.timer immich-ml-window-off.timer
```

The `.env` holds a **least-privilege** key (`job.create` + `job.read` only —
vault `immich.rig_ml_window_api_key`), not the admin key.

## Monitoring

`verification/checks.d/rig-immich-ml.yaml` is window-aware:
- `immich-smart-search-consumer` (crit) — smart search returns results end-to-end,
  whichever backend is active. The real user-facing signal.
- `rig-immich-ml-window` (warn) — rig ML up+encoding at night, **down** by day; a
  `DAY_UNEXPECTED_UP` means the off-timer failed and VRAM contention is back.

`docker-fleet.yaml`'s `containers-manifest-rig` **excludes** `immich_machine_learning`
(intentionally absent by day) — it is covered by the two checks above, not the
blanket manifest, so it is removed from `verification/coverage/rig.containers`.
