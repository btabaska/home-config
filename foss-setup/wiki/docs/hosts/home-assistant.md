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

Discovered live on the LAN 2026-07-07; core 2026.6.4. **Lights are live and
Apple-Home-bridged** (2026-07-13): Hue + Elgato integrated and controllable
from HA; the **HomeKit Bridge** (`HASS Bridge:21064`, light domain, 73
accessories) is created and awaiting the user's iPhone pairing. Still pending:
tailnet join (ha-01), real backups (see below), and the rest of the device
track.

## Integrations

Live now:

- **Hue** — native LAN integration via the Hue bridge (`192.168.20.100`, IoT
  VLAN, fully local). ~71 light entities. **Verified controllable from HA.**
- **Elgato Key Light ×2** — fully local; homed to the Office area.
- **HomeKit Bridge** (`homekit`) — exposes HA's `light` domain to Apple Home
  (Siri + HomePods). Advertises `_hap._tcp` on the Trusted VLAN; the iPhone /
  HomePods discover it natively because they share Trusted with HA (no mDNS
  reflection needed). Pairing code lives in the HA "HomeKit Pairing"
  notification.
- **Matter / Thread**, **mobile_app** (Btiphone) — already set up.

Ready to add (creds in vault, core integrations, no HACS needed) — not lights,
so left for a follow-up: **UniFi Protect** cameras (local), **Roborock**
(cloud), **VeSync** (cloud), **Withings** (cloud OAuth).

Blocked / needs a decision:

- **Midea AC ×4 + dehumidifier** — `midea_ac_lan` is a **HACS** custom
  integration (HACS is **not installed**) and needs a Midea/SmartLife account
  (**no creds in the vault**) for the one-time cloud handshake. Back up the
  per-device token `.json` after setup. ESPHome dongle path = hardware, skipped.
- **Emporia Vue** — `emporia_vue` is also **HACS** (blocked on HACS install).
- **Nest** — SDM cloud path **dropped** (being replaced by an ecobee via
  `homekit_controller`, hardware not yet installed). SDM needs a ~$5 Device
  Access registration fee — optional, not needed for lights.
- **Zigbee** backbone — deliberately out of scope (requires a coordinator
  stick + Zigbee2MQTT + Mosquitto = new hardware).
- **Voice/LLM**: Assist pipeline pointed at the rig's LiteLLM
  (`llm.tabaska.us`, OpenAI-compatible; the rig is 24/7 — it being down is
  an incident). *Earlier drafts said "LiteLLM on the mini" — that mini
  front-door/fallback was never deployed.*

## Maintenance channel

**Managed appliance — HA manages itself.** Not Ansible-managed (no
general-purpose shell to converge). Updates via the HA UI on your schedule.

### Pending updates — deferred, operator-gated (as of 2026-08-03, fix-66 / SL14)

Applying any of these **reboots HA** → schedule for the 4–7 AM window.

| Component | Installed | Available | Pending since |
|---|---|---|---|
| HA Core | 2026.7.2 | 2026.7.4 | 2026-07-28 |
| HA OS (HAOS) | 18.1 | 18.2 | 2026-08-01 |
| matter-server add-on | 9.1.0 | 9.1.1 | 2026-07-29 |

Supervisor (2026.07.5) is current. The `ha-updates-pending` check (fix-36)
warns only past a **21-day** stale threshold, so it stays green until
~2026-08-18 for Core — apply before then to keep it green.

### Watch: 2026-08-02 overnight 3-min network blip (fix-66 / SL13)

On 2026-08-02 **00:40–00:43 EDT** the appliance briefly lost all network:
`ENETUNREACH` on HA's *own* mDNS socket (`192.168.10.50:5353`), plus matter /
Hue / Elgato connect failures — then fully self-recovered (Hue/Elgato state
changes resumed the same morning; no errors after 00:43:07). ENETUNREACH on
HA's own socket = the appliance's own link/DHCP dropped for a beat, **not** a
per-device or firewall fault, and **unrelated** to the mini docker-subnet fix
(different host). **Single occurrence, no recurrence** through 2026-08-03. No
fix warranted; a *sustained* recurrence is already caught by the fast-tier
`ha-http` (crit) + `ha-api-auth`/`ha-hue-lights` checks — a sub-sweep 3-min blip
can slip between 10-min sweeps, which is acceptable for a self-healing transient.

## Backups

⚠️ **As of 2026-07-13 there are NO real backups.** The only backup agent is
`hassio.local` (on-appliance eMMC); there is **no schedule, no NAS agent, and
no encryption password** configured — so an eMMC failure loses everything. A
single local rollback snapshot (`pre-homekit-bridge-claude`, id `bdcf6693`,
2026-07-13) exists only as a pre-change safety net.

Target (still pending): Settings → System → Backups → scheduled full backups
to the **NAS** with an encryption key. **The backup encryption key must live
in Proton Pass — a backup without its key is not a backup.** Also put `/config`
YAML under git via the Git add-on, and separately back up the Midea token
files once Midea is added.

## Failure blast radius

HA down: automations and dashboards stop; the devices themselves (Hue app,
Nest app, manual switches) keep working.
