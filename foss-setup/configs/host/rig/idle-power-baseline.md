# rig idle-power baseline (game-09)

The rig (`CachyOS`, i7-12700K + RTX 3090 Ti, `192.168.10.12`) runs **24/7** — auto-suspend
is a settled *won't-do* (decision 2026-07-08: availability > the ~$23/mo idle cost). This file
records the idle-power tuning that is **already applied** and the one remaining gate. It is
**documentation-only** (rig host config is not ansible-managed — see `README.md`); the actual
levers live in the units/checks referenced below.

## Measured baseline (2026-07-28, rig live but not truly idle)

| Domain | Measured | Notes |
|---|---|---|
| CPU package (RAPL `intel-rapl:0`) | **~10 W** | i7-12700K, `powersave` gov + `balance_performance` EPP, deep C-states available (POLL→C1E→C6→C8→**C10**). Already near-optimal for idle; no safe further win. |
| GPU (`nvidia-smi`) | 300 W cap / ~17 W idle floor | `gpu-power-tune.service` (from **game-10**) — persistence on + 300 W power-limit (default 450 W). Cap trims *peak*; persistence keeps the driver resident so the card drops to its ~17 W P8 idle floor instead of a re-init spike. |
| plasmashell | **~0–1 %** CPU (3s sample) | Historical busy-loop is **gone** — a full-Plasma-Wayland autologin session sits idle. Guarded by `rig-plasmashell-idle`. |

The two 24/7 workloads that keep the box from ever being *truly* idle are intentional, not waste:
the Palworld server and on-demand LLM loads (llama-swap / Immich ML night-window). Idle tuning
must **not** cap them — `gpu-power-tune` only sets a power *ceiling* (auto-restores full clocks
under load) and the CPU governor is left to `intel_pstate` (ramps on demand). Neither starves the
AI stack or the night-gated Immich ML window.

## Verification checks (in `verification/checks.d/rig.yaml`)

- `rig-gpu-power-tune` — persistence on + `gpu-power-tune.service` active (guards the GPU lever).
- `rig-plasmashell-idle` — plasmashell < 30 % CPU over a real 3s `/proc/<pid>/stat` delta
  (guards the busy-loop half; a future headless pass with no plasmashell passes cleanly).

## Remaining gate — needs a human / physical meter

The `verify` for game-09 is a **wall reading < 100 W idle**. This is **not** obtainable remotely:
the rig has **no power meter** — Home Assistant exposes no rig smart-plug (140 entities, office
lights + an Assist pipeline only), and there is no Kill-A-Watt in the loop. A person must take a
Kill-A-Watt / metered-plug reading with the rig idle (LLM unloaded, no active game session, Immich
ML off during the day) to close the task. The software-side tuning above is complete; only the
physical confirmation is outstanding.

## Optional future lever (user-facing → deferred)

A **headless / no-desktop-when-idle** pass (drop `graphical.target` autologin, boot to
`multi-user.target`) would remove the ~24/7 Plasma-Wayland session for a modest idle saving, but it
breaks the rig's local GUI (Code-OSS) use — a user decision + a 4–7 AM window. Not applied.
