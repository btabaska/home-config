# HA health — updates, entity availability, Apple-side pairing

What to do when `ha-updates-pending`, `ha-availability-drift`, or
`ha-iphone-presence` fires (ntfy topic `verification`). All three were added by
**fix-36** (quality-gate M9/M11/M40/M41/M42, 2026-07-19) after the audit found
the HA Green quietly degraded for weeks: HAOS two major versions behind, 11
iPhone companion sensors dead since 07-07, 8 Hue lights unavailable — all
invisible because only liveness was checked.

The HA Green (192.168.10.50) is **LAN-only, no tailnet, no standing SSH** —
drive it via REST/WS API (token: vault `hosts.ha.api_token`). For file-level
work, start/stop the `core_ssh` add-on over the Supervisor WS proxy (see the
[reverse proxy runbook](reverse-proxy.md), step 2).

## Accepted baseline (decided 2026-07-18, fix-36)

| what | state | why |
|------|-------|-----|
| ~8 Hue lights `unavailable` (kitchen ×4, basement ×2, upstairs bath, attic) | **accepted usage** | Bulbs are cut at wall switches — the Hue bridge itself reports zigbee `connectivity_issue` for exactly these devices, and the set churns as switches get used. Not an HA/bridge fault. |
| 11 `sensor.btiphone_*` telemetry sensors `unavailable` + `notify.brandon_iphone` unknown | **deferred — phone-side fix pending** | Needs hands on the iPhone (below). Presence (`device_tracker` + battery) still works and is monitored. |
| HomeKit client uuid `51d8dbec…` at 192.168.10.42 rejected on pair-verify | **deferred — Apple-side re-pair pending** | Device (Apple MAC, likely the HomePod) holds stale pairing keys. Bridge is healthy with 2 working paired clients; the rejects are log noise until re-paired (below). |

## `ha-updates-pending` fired — something sat pending ≥21 days

Policy: apply HA updates roughly monthly; don't let them accumulate (the audit
caught HAOS at 16.3 with 18.1 current — two majors).

Apply via REST, no UI needed (order: add-ons → Core → OS last, it reboots):

```bash
TOKEN=<vault hosts.ha.api_token>
# add-on / core (backup:true snapshots first); OS takes no backup flag (A/B slots)
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"entity_id":"update.home_assistant_core_update","backup":true}' \
  http://192.168.10.50:8123/api/services/update/install
```

The call blocks/times out while HA restarts — poll `/api/config` for the new
`version` and `state: RUNNING`, then confirm all config entries `loaded`
(`config_entries/get` over WS). Daily 04:45 encrypted backups to the NAS
(`ha-backup-offsite-fresh`) are the rollback path; the key is vault
`hosts.ha.backup_password`.

## `ha-availability-drift` fired

The message names the condition:

- **`DRIFT:<entities>`** — something *outside* the accepted baseline went
  `unavailable`: an integration silently died. Check
  `config_entries/get` (WS) for a non-`loaded` entry and the system log
  (`system_log/list` — REST `/api/error_log` 404s on 2026.x cores). Reload the
  integration via `POST /api/config/config_entries/entry/<id>/reload`.
- **`BTIPHONE:<n>`** — the iPhone sensor cluster grew past the accepted 11:
  the companion app is degrading further. Do the phone-side fix below.
- **`DARK30:<entities>`** — a light has been unavailable ≥30 days straight.
  That's a dead bulb or a fixture someone forgot, not wall-switch churn.
  Replace the bulb or retire the entity.

## `ha-iphone-presence` fired — the companion pipeline is actually dead

`device_tracker.brandon_iphone` or battery stopped reporting real values —
this is the part we rely on (presence), not the accepted-dead telemetry.
On the iPhone: open the HA companion app so it reconnects; if still dead,
check app Settings → Companion App → *Reset front-end cache / reconnect*, and
that the server URL points at `http://192.168.10.50:8123`.

## Deferred hands-on fixes (do these when convenient, then delete the baseline)

**Re-enable the 11 iPhone sensors (M11/M42):** on the iPhone, HA app →
Settings (gear) → **Companion App → Sensors** → toggle on the disabled ones
(BSSID/SSID, Connection Type, Geocoded Location, SIM 1/2, Storage, Audio
Output, Last Update Trigger, kiosk brightness/volume). If they're already on,
iOS Settings → Home Assistant → allow Location *Always* + Motion & Fitness,
and enable Background App Refresh. Verify: the `sensor.btiphone_*` entities
leave `unavailable` within minutes of opening the app. Then tighten
`ha-availability-drift`'s btiphone allowance from 11 to 0 in
`verification/checks.d/ha.yaml`.

**Re-pair the stale HomeKit client (M41):** the device at 192.168.10.42
attempts pair-verify with keys the bridge no longer recognizes (bridge was
re-created; device kept old keys — rejected 4× on 2026-07-19 alone). On the
Apple side: Home app → find the stale **HASS Bridge** accessory → *Remove
Accessory* (or reset the HomePod's Home association), then re-add using the
pairing code from HA → Settings → Devices & Services → HomeKit Bridge. The 2
already-paired clients keep working throughout; don't reset the bridge
pairing itself unless both sides are stale.

## History

2026-07-19 (fix-36): Core 2026.6.4 → 2026.7.2, HAOS 16.3 → 18.1, Matter
Server 9.0.3 → 9.1.0 applied via `update.install` service calls; baseline
above accepted; checks added. Details:
`docs/quality-gate-2026-07-16.md` findings M9/M11/M40/M41/M42.
