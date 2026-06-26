# Midea AC + Dehumidifier — Local Control in Home Assistant

Goal: control the Midea AC and dehumidifier **locally** (LAN only, no cloud at
runtime). Two paths. Path A keeps the OEM Wi-Fi dongle and uses the HACS
`midea_ac_lan` integration. Path B replaces the dongle with an ESPHome-flashable
module for a guaranteed cloud-free setup. There is also a Tuya fallback for some
2021+ units.

Authoritative docs:
- `midea_ac_lan` (HACS): https://github.com/wuwentao/midea_ac_lan
- HACS install: https://hacs.xyz/docs/use/download/download/
- ESPHome Midea component: https://esphome.io/components/climate/midea/
- SLWF-01Pro flashing: https://smartlight.me/diy-smart-home/slwf01_flashing_en
- SLWF-01Pro web flasher: https://smlight.tech/flasher/#slwf01proV2
- LocalTuya (Tuya fallback): https://github.com/xZetsubou/hass-localtuya

---

## ⚠️ READ THIS FIRST — back up the per-device `.json`

Midea has been **closing the cloud Token APIs** used to add devices
(Meiju / Smarthome / NetHome Plus, shutting down in stages). Once these are gone you
**cannot generate a new token/key**, and your existing token becomes the **only**
credential that controls the device. If you lose it, you permanently lose local
control until a working cloud API exists again.

**Therefore, the moment each V3 device is added successfully:**

- [ ] Back up its config file: `/config/.storage/midea_ac_lan/<device_id>.json`
- [ ] Store the copy **off the HA box** (NAS + password manager / encrypted vault).
- [ ] Do NOT delete or unbind the device from the integration "to start over".
- [ ] If you ever migrate/reinstall: restore the `.json` files into
      `.storage/midea_ac_lan/` BEFORE starting HA, or use **Configure manually** and
      type in the `device_id`, `type`, `ip`, `port`, `protocol`, `token`, `key`.

> Note: only **V3** devices have a `.json` with token/key. Old **V2** devices have no
> token and no `.json` file. If `/config/.storage/midea_ac_lan/` is missing, device
> info may also be in `/config/.storage/core.config_entries`.

Each `.json` contains: `device_id`, `type`, `protocol`, `ip_address`, `port` (6444),
`model`, `subtype`, `token`, `key`.

---

## Path A — HACS `midea_ac_lan` (keep OEM dongle)

This is the lowest-effort path and supports AC + dehumidifier (and many other Midea
appliance types). V3 devices need **one** cloud handshake to fetch token/key; after
that, control is local.

1. [ ] Install **HACS** if not already: https://hacs.xyz/docs/use/download/download/
2. [ ] In HACS, add/open **midea_ac_lan**, download it, then **Restart Home Assistant**.
       Quick link: https://my.home-assistant.io/redirect/hacs_repository/?owner=wuwentao&repository=midea_ac_lan
3. [ ] Give each Midea device a **static DHCP lease** on the IoT VLAN (so the IP in the
       `.json` stays valid). Recommended for stable local control.
4. [ ] Settings → Devices & Services → **+ Add Integration** → **midea_ac_lan**.
5. [ ] The integration auto-discovers devices on the LAN. For each device:
       - V2: added directly, no token needed.
       - V3: you'll be asked for your **Midea account + password** ONE time so it can
         pull the **token/key** from the cloud. After all V3 devices are configured,
         you can remove the Midea account credentials without affecting control.
6. [ ] **Immediately back up each `/config/.storage/midea_ac_lan/<device_id>.json`**
       (see the warning section above). This is the most important step.
7. [ ] (Optional) Per-device options accept JSON customizations, e.g.
       `{ "refresh_interval": 15, "fan_speed": 100 }`.

### Getting the `.json` for backup
- Easiest: use the **Samba**/**SSH & Web Terminal** add-on (or File editor) to copy
  `/config/.storage/midea_ac_lan/*.json` to the NAS share.
- See the project's debug doc: https://github.com/wuwentao/midea_ac_lan/blob/master/doc/debug.md

---

## Path B — ESPHome SLWF-01Pro dongle (fully cloud-free, ~$10)

Replaces the OEM Wi-Fi USB dongle with the **SLWF-01Pro** (ESP8266) flashed with
ESPHome's `midea` climate component. No Midea cloud, no tokens, ever. The dongle
plugs into the AC's internal USB port and talks UART at **9600 baud, 5V logic**.

1. [ ] Buy an **SLWF-01Pro v2.1** (CloudFree / smartlight.me / Tindie).
2. [ ] Flash it (v2.1 has USB-C web flashing — no UART adapter needed):
       - Go to https://smlight.tech/flasher/#slwf01proV2
       - Hold the **FLH** button, connect via USB-C, release after connecting.
       - Select firmware, click **Flash**. (Older v1.x needs a USB-TTL CH340/CP210x
         adapter per https://smartlight.me/diy-smart-home/slwf01_flashing_en)
3. [ ] Or flash your own ESPHome firmware (recommended for HA-native config) using the
       `midea` component — see example `esphome-midea-slwf01.yaml` in this folder.
4. [ ] Power the dongle from the AC's USB port; join its `AC-wifi` AP
       (password `slwf01pro`), browse to `http://192.168.4.1`, select your IoT Wi-Fi.
5. [ ] ESPHome auto-discovers in HA: Settings → Devices & Services → **ESPHome** → Add.
6. [ ] Repeat per AC. (The dehumidifier may not have a compatible USB dongle slot —
       keep it on Path A if so.)

---

## Path C — Tuya fallback (some 2021+ units)

A subset of newer Midea-branded units ship with **Tuya** internals rather than the
classic Midea protocol. If `midea_ac_lan` cannot discover/authenticate the device, it
is likely Tuya. Use **LocalTuya** (HACS) for local control, which requires extracting
the device `local_key` (one-time, via Tuya IoT developer account).
- LocalTuya: https://github.com/xZetsubou/hass-localtuya

---

## Recommendation

- **AC units:** prefer **Path B (SLWF-01Pro)** for the AC if you want a guaranteed
  cloud-free future, since Midea's token APIs are being retired. Otherwise Path A is
  fine *as long as you back up the `.json`*.
- **Dehumidifier:** **Path A** (`midea_ac_lan`) — back up its `.json` immediately.
- Put all Midea devices on the **IoT VLAN** with static leases; HA on the Trusted VLAN
  reaches them (Trusted → IoT is allowed).
