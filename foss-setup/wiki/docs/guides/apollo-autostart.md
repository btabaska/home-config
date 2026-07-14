# Apollo autostart notes

> Install, configure, and autostart the Apollo game-stream host on the CachyOS rig, and pair the first Moonlight client.
_Source: `foss-setup/scripts/gaming/apollo-autostart-notes.md` · migrated + validated 2026-07-14._

Apollo ([ClassicOldSong/Apollo](https://github.com/ClassicOldSong/Apollo)) is a
maintained fork of **Sunshine** (LizardByte) — the self-hosted game-stream
**host**. Moonlight is the **client** (unchanged; Artemis is a Moonlight fork
for Android). Apollo is a **drop-in** for Sunshine: same Moonlight clients, same
ports, same pairing flow, web UI on 47990. We run it instead of stock Sunshine
because the rig is **headless and 24/7** — Apollo adds per-client permissions,
clipboard sync, and virtual-display management on top of Sunshine.

This runbook covers installing Apollo on the CachyOS/Arch rig with NVENC (RTX
3090 Ti), turning it on at boot, and the first-time web-UI setup.

!!! note "Verified live on the rig (192.168.10.12), 2026-07-14"
    - `apollo 0.4.8-3` (AUR), `nvidia-utils 610.43.02-3`, driver **610.43.02**, GPU **RTX 3090 Ti**.
    - `apollo.service` (systemd `--user`) is **active** and lingering is enabled (`Linger=yes`), so it survives boot with no interactive login.
    - Web UI answers on `https://localhost:47990` (LAN pairing UI `https://192.168.10.12:47990`); mDNS/Avahi advertising works.

!!! warning "This rig uses an HDMI dummy plug, not Apollo's virtual display"
    Despite Apollo's headless/virtual-display feature, the live rig captures a
    **physical HDMI dummy plug** on `HDMI-A-1` (the only `connected` DRM output;
    DP-1/2/3 are disconnected). A `display-policy.service` (systemd `--user`,
    active) keeps the dummy plug as the sole display when headless and switches
    to a real monitor via `kscreen-doctor` when one is plugged in. So Apollo
    captures a real KMS/Wayland display, not a synthetic virtual one. Run the
    companion `apollo-enable.sh` **only after a display exists** (dummy plug or
    real monitor). See `foss-setup/scripts/gaming/display-policy.sh`.

**Authoritative docs**

- Apollo project + docs (install, features, headless/virtual-display): <https://github.com/ClassicOldSong/Apollo>
- AUR package: <https://aur.archlinux.org/packages/apollo>
- Upstream Sunshine docs (Apollo shares most config/behavior): <https://docs.lizardbyte.dev/projects/sunshine/latest/md_docs_2getting__started.html>
- Moonlight setup guide (client side, unchanged): <https://github.com/moonlight-stream/moonlight-docs/wiki/Setup-Guide>

---

## 1. Install on Arch / CachyOS

The AUR `apollo` package is the supported install path for the fork:

```bash
# with an AUR helper, e.g. paru/yay:
paru -S apollo

# NVENC hardware encoding comes via the proprietary NVIDIA driver — ensure it
# and its NVENC libraries are installed:
sudo pacman -S --needed nvidia-utils
```

!!! note "NVENC on the 3090 Ti"
    Apollo uses **NVENC** for H.264/HEVC/AV1 4K HDR encode (same encoder path as
    stock Sunshine) — separate from the rig's render workload, so streaming costs
    little GPU. NVENC needs only the proprietary NVIDIA driver + `nvidia-utils`;
    the full `cuda` package is **not** required just for streaming.

---

## 2. Autostart (run on boot, as your user)

Apollo ships a **systemd `--user`** service from the `apollo` package. Enable +
start it now and on every login/boot:

```bash
# enable + start now, and on every login/boot:
systemctl --user enable --now apollo

# check status:
systemctl --user status apollo
```

To have the user service start at boot **without an interactive login** (the
24/7 rig boots unattended, e.g. after power-outage recovery), enable lingering
for your user (already enabled on the live rig):

```bash
sudo loginctl enable-linger "$USER"
```

!!! tip
    If `systemctl --user` can't find the unit, list what the package installed
    with `systemctl --user list-unit-files | grep -i apollo` and enable that
    exact name.

### Display capture (this rig)

Because this box is headless, a `display-policy.service` keeps an HDMI dummy
plug (`HDMI-A-1`) present so Apollo always has a real display to capture, and
falls back to a real monitor when one is attached. Apollo's own virtual-display
feature exists (KMS capture via `capture = kms` in the config, which may need
`cap_sys_admin` on the binary), but the deployed pattern here is the dummy plug.
Set output resolution/FPS via the display policy and Apollo's virtual-display
options in the web UI.

---

## 3. First-time web UI

1. Open **<https://localhost:47990>** on the rig (self-signed cert → accept the warning). From another LAN host use `https://192.168.10.12:47990`.
2. Create the **username + password** on first load (this protects the web UI — do this immediately; it is not set by default). Web creds can be set through this first-run flow or in the Apollo config file directly.
3. Confirm the encoder shows **NVENC** under Configuration → Audio/Video.
4. (Optional) Configure the **virtual display** (resolution/FPS/HDR), set **per-client permissions**, and add apps under **Applications** (Steam Big Picture is pre-added; add specific game executables as needed).

---

## 4. Firewall / ports

Apollo listens on the **same default ports as Sunshine**: TCP **47984, 47989,
48010** and UDP **47998–48000**, plus web UI TCP **47990**. On the live rig the
UFW rules allow these from **both** the Trusted VLAN (`192.168.10.0/24`, for
in-home mDNS discovery + pairing) **and** the Tailscale CGNAT range
(`100.64.0.0/10`, for remote play). Do NOT port-forward these publicly — remote
play goes over **Tailscale**.

---

## 5. Pair a client (in-home first!)

1. Put host + client on the **same Trusted VLAN** (mDNS auto-discovery).
2. Open Moonlight (or Artemis on Android) → the rig appears automatically.
3. Tap it → Moonlight shows a **PIN**.
4. On the rig web UI → **PIN** tab → enter the PIN + a device label → **Send**.
5. The client unlocks; launch Desktop or a game. Set that client's per-client permissions in the Apollo UI if you want to restrict what it can do.

!!! warning "iOS/tvOS clients"
    Apple clients **must** pair on the same local network first (Apple rule).

Android handhelds: **Artemis** (Moonlight fork) pairs the same way; with the
dummy plug in place there is a display to capture and HDR is available on the
host.

---

## 6. Verify

- `systemctl --user status apollo` → `active (running)`.
- Web UI reachable at <https://localhost:47990> and login works.
- A Moonlight client on the same VLAN sees the host and pairs.
- Encoder = NVENC; a test stream of the Desktop is smooth at your target res/FPS.

---
[← Guides](index.md)
