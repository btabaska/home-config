# home-assistant — HA Green

The smart-home hub: pulls cloud-tethered devices into local control so lights
and climate work even when vendor clouds don't.

| | |
|---|---|
| **Hardware** | Home Assistant Green (dedicated appliance, eMMC) |
| **OS** | HAOS (Supervisor + add-on store) |
| **IP** | `192.168.10.50` · UI at `http://192.168.10.50:8123` · **not on the tailnet yet** (pending: ha-01) |
| **VLAN** | Trusted (reaches IoT devices via the Trusted → IoT allow rule) |
| **Power** | 24/7, ~2–3 W |
| **Access** | Web UI (creds in the vault). Shell: the SSH & Web Terminal add-on, or `root@192.168.10.50:22222` debug port — there is no normal user shell |

## Status

Discovered live on the LAN 2026-07-07; **onboarding not done** (pending:
ha-01 and the whole ha-* track — integrations, backups, tailnet join).

## Planned integrations (the ha-* track)

- **Hue** — native LAN integration via the Hue bridge (fully local)
- **Nest** — Google SDM API (cloud-routed; needs a Google Cloud project + $5 Device Access fee)
- **Midea AC/dehumidifier** — `midea_ac_lan` (local after a one-time cloud
  handshake; **back up the per-device token `.json` files**), or ESPHome
  dongle for fully cloud-free
- **UniFi Protect** cameras (local, needs a Protect API key + RTSP enabled)
- **Zigbee** backbone later: coordinator stick + Zigbee2MQTT + Mosquitto
- **Voice/LLM**: Assist pipeline pointed at LiteLLM on the mini (rig model
  when awake, fallback otherwise)

## Maintenance channel

**Managed appliance — HA manages itself.** Not Ansible-managed (no
general-purpose shell to converge). Updates via the HA UI on your schedule.

## Backups

Settings → System → Backups → scheduled full backups to the **NAS**
(pending: ha track). **The backup encryption key lives in Bitwarden — a
backup without its key is not a backup.** Also put `/config` YAML under git
via the Git add-on (pending), and separately back up the Midea token files.

## Failure blast radius

HA down: automations and dashboards stop; the devices themselves (Hue app,
Nest app, manual switches) keep working.
