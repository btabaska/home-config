# Cheap local sensor shopping list

Grounded picks for the Zigbee backbone in Section 3 (smart-home) — all pair cleanly with **Zigbee2MQTT/ZHA**, need **no vendor hub**, and run fully local. Street prices as of mid-2026 (USD). Buy the **Sonoff SNZB-P** line for the best price/reliability; **Aqara** is the premium alternative; **Third Reality** is good for plugs and the siren leak sensor.

> **Status:** this rollout (wave 1, ~$505-865 hardware) is **deferred** (`ha-30`, buy in stages) and compiled into `docs/hardware-shopping-list.md`.

## Start here — the coordinator (buy one)

| Item | Why | ~Price | Link |
|---|---|---|---|
| **Sonoff Zigbee 3.0 USB Dongle Plus-E** | Most-recommended 2026 coordinator (CC2652P); ZHA + Z2M. Use a short USB-2 extension. | ~$20 | itead.cc |
| **Home Assistant Connect ZBT-2** | Official HA coordinator; zero-fuss first-party. | ~$25 | home-assistant.io |

## Sensors (mix and match)

| Sensor | Type | ~Price | Battery |
|---|---|---|---|
| **Sonoff SNZB-03P** | Motion (PIR, light sensor, ~5s re-trigger) | ~$11-13 | CR2477 |
| **Aqara Motion Sensor P1** | Motion, premium (adjustable sensitivity) | ~$20-25 | CR2450 |
| **Sonoff SNZB-04P** | Door/window contact (tamper) | ~$13-15 | CR2477 |
| **Aqara Door & Window Sensor** | Contact, premium | ~$10-15 | CR1632 |
| **Sonoff SNZB-02D** | Temp/humidity with LCD | ~$10-13 | CR2477 |
| **Third Reality 3RTHS24BZ** | Temp/humidity with e-ink screen | ~$15-18 | AAA |
| **Sonoff SNZB-05P** | Water-leak (detects 0.5 mm film) | ~$10-16 | CR2477 |
| **Third Reality Water Leak Sensor** | Water-leak with **120 dB siren** (alerts even if HA is down) | ~$15-20 | AAA |
| **Aqara Wireless Mini Switch** | Button (single/double/long-press scenes) | ~$18 | CR2032 |
| **Sonoff SNZB-06P** *(stretch)* | mmWave presence (occupancy, not just motion) | ~$25 | USB-C |
| **Third Reality Zigbee Smart Plug** | Smart plug **+ energy reporting + Zigbee router** | ~$13 | mains |

> **Mesh tip:** every mains-powered device (smart plug) is a Zigbee **router** — spread **5-7** around the house for a stable mesh. Pair devices *near* the coordinator first, then move them. **Avoid Aqara-branded hubs** if you mix brands. A solid starter kit: 1 coordinator + 2 smart plugs (routers) + 2 motion + 3 contact + 2 leak + 1 temp/humidity ≈ **$150-180**.

---
[← index](index.md)
