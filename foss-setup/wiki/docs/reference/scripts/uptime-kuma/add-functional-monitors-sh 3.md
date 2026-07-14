# `add-functional-monitors.sh`

> Add FUNCTIONAL monitors to Uptime Kuma (v2.x, embedded MariaDB) — checks that

**Path:** `foss-setup/scripts/uptime-kuma/add-functional-monitors.sh` · **Category:** [Uptime Kuma](index.md) · **Type:** Bash

## What it does

```text
 Add FUNCTIONAL monitors to Uptime Kuma (v2.x, embedded MariaDB) — checks that
 verify a service *works*, not just that its port answers.

 Born from the 2026-07-09 "no models available" incident: every liveness
 monitor (Rig LiteLLM /health/liveliness, Rig Ollama /, Rig Open WebUI /)
 stayed green while a UFW change broke the container->host ollama hop.

 Run on the Mac mini (where the uptime-kuma container lives):
   KUMA_LITELLM_KEY=sk-... bash add-functional-monitors.sh
 KUMA_LITELLM_KEY = vault litellm.kuma_monitor_key (scoped virtual key,
 models chat+utility only — NOT the master key).

 Idempotent: monitors matched by name; linked to the existing default ntfy
 notification; restarts the container (v2 loads monitors at startup only).
```

## Environment / variables referenced

`CONTAINER`, `KUMA_CONTAINER`, `KUMA_LITELLM_KEY`, `RIG`, `SOCKET`, `USER_ID`

## See also

- [`bootstrap-nas-monitors.sh`](bootstrap-nas-monitors-sh.md)
- [`seed-monitors.sh`](seed-monitors-sh.md)
- [Uptime Kuma scripts](index.md) · [All scripts](../index.md)
