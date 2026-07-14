# 5. Electricity cost of running hardware 24/7

**Your rate:** RG&E all-in residential runs about **$0.20/kWh** in 2026 (supply + delivery; per-kWh delivery ~8.5¢, supply floats seasonally). Rule of thumb:

> **1 watt running 24/7 ≈ $1.75/year.** Every 100 W left on ≈ $175/year.

| Device | Typical draw | ~Annual cost @ $0.20/kWh |
|---|---|---|
| DS920+ + 4 large drives | ~35-45 W (less if drives hibernate) | **~$60-80** |
| Mac mini (Late 2014, i5-4278U, 8 GB) (Ubuntu) | ~10-15 W under load (idle ~6-10 W) | **~$18-26** |
| HA Green (purchased) | ~2-3 W | ~$4-5 |
| Dream Wall router | ~30-40 W | **~$55-70** |
| Fiber ONT/modem | ~5-10 W | ~$10-15 |
| **Always-on subtotal** | **~82-113 W** | **~$150-200/year** |
| CachyOS rig — *idling* | ~90-120 W (3090 Ti idles ~20-30 W alone, but on Linux can get stuck at ~100 W+) | ~$160-210 *(now always-on)* |
| CachyOS rig — *under LLM / streaming / heavy-server load* | 400-600 W+ | ~$700-1,000+ *if sustained 24/7* |

**Takeaways:**

1. **The rig is the entire story — and its cost is now a deliberate trade.** Always-on gear is cheap (~$150/year). **Decision 2026-07-08: the rig runs 24/7 for availability** — ~130 W idle ≈ $23/mo (~$275/year), accepted so Sunshine streaming, local LLM, and heavy game servers are ready instantly. The open **idle-power-tuning task (`game-09`)** and the GPU idle fix below keep that number honest.
2. **Wake-on-LAN = recovery tooling only:** keep WoL enabled in BIOS so the rig can be brought back after a power outage or accidental shutdown. It is no longer part of any workflow — there is no auto-suspend.
3. **NAS drive hibernation:** enable HDD hibernation in DSM so drives spin down when idle.
4. **GPU idle fix on Linux:** the 3090 Ti can get stuck in a high-power state at idle (~100-115 W doing nothing) instead of ~20-30 W. Check `nvidia-smi` at idle; persistence mode (`-pm 1`), a power limit (`nvidia-smi -pl`), and a modest undervolt (locked clocks + offset via a systemd service so it survives reboot) keep idle and load down.
5. **Measure it.** You already have **Emporia Energy** on the breaker/circuits — use its per-circuit data to replace these estimates with real draw (and feed it into HA's Energy dashboard).

---
[← index](index.md)
