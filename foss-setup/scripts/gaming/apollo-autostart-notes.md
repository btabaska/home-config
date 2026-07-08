# Apollo on the CachyOS rig — install, config & autostart runbook

Apollo (ClassicOldSong/Apollo) is a **maintained fork of Sunshine** (LizardByte)
— the self-hosted game-stream **host**. Moonlight is the **client** (unchanged;
Artemis is a Moonlight fork for Android). Apollo is a **drop-in** for Sunshine:
same Moonlight clients, same ports, same pairing flow, web UI on 47990. We run it
instead of stock Sunshine because the rig is **headless and 24/7** — Apollo adds
built-in **virtual-display / headless output management** (no dummy HDMI plug
needed), **per-client permissions**, and clipboard sync on top of Sunshine.

This runbook covers installing Apollo on the CachyOS/Arch rig with NVENC (3090
Ti), turning it on at boot, and the first-time web-UI setup.

**Authoritative docs**
- Apollo project + docs (install, features, headless/virtual-display): <https://github.com/ClassicOldSong/Apollo>
- AUR package: <https://aur.archlinux.org/packages/apollo>
- Upstream Sunshine docs (Apollo shares most config/behavior): <https://docs.lizardbyte.dev/projects/sunshine/latest/md_docs_2getting__started.html>
- Moonlight setup guide (client side, unchanged): <https://github.com/moonlight-stream/moonlight-docs/wiki/Setup-Guide>

---

## 1. Install on Arch / CachyOS

**AUR `apollo` package** (the supported install path for the fork):

```bash
# with an AUR helper, e.g. paru/yay:
paru -S apollo
# NVENC (NVIDIA) hardware encoding comes via the proprietary NVIDIA driver;
# ensure it (and its CUDA/NVENC libraries) is installed:
sudo pacman -S --needed nvidia-utils cuda
```

> 3090 Ti note: Apollo uses **NVENC** for H.264/HEVC/AV1 4K HDR encode (same
> encoder path as stock Sunshine) — this is separate from the rig's render
> workload, so streaming costs little GPU. Ensure the proprietary NVIDIA driver
> is installed.

---

## 2. Autostart (run on boot, as your user)

Apollo ships a **systemd --user** service from the `apollo` package. Enable +
start it now and on every login/boot:

```bash
# enable + start now, and on every login/boot:
systemctl --user enable --now apollo

# check status:
systemctl --user status apollo
```

To have the user service start at boot **without an interactive login** (the
24/7 rig boots unattended, e.g. after a power-outage recovery), enable lingering
for your user:

```bash
sudo loginctl enable-linger "$USER"
```

> If `systemctl --user` can't find the unit, list what the package installed:
> `systemctl --user list-unit-files | grep -i apollo` and enable that exact name.

### Wayland / headless display capture
The whole reason we picked Apollo: on this **headless** rig it can manage a
**virtual display** so it captures and streams even with no monitor attached —
no dummy HDMI plug required (Apollo's headitor/virtual-display feature). For
Wayland headless capture use **`capture = kms`** in the config (KMS capture may
need `cap_sys_admin`, which the install usually grants the binary). An Xorg
session also works if you prefer. Set the output resolution/FPS via Apollo's
virtual-display options in the web UI.

---

## 3. First-time web UI

1. Open **<https://localhost:47990>** on the rig (self-signed cert → accept the warning).
2. Create the **username + password** on first load (this protects the web UI —
   do this immediately; it is not set by default). Web creds can be set either
   through this first-run flow in the `apollo` web UI or in the Apollo config
   file directly.
3. Confirm the encoder shows **NVENC** under Configuration → Audio/Video.
4. (Optional) Configure the **virtual display** (resolution/FPS/HDR), set
   **per-client permissions**, and add apps under **Applications** (Steam Big
   Picture is pre-added; add specific game executables as needed).

---

## 4. Firewall / ports

Apollo listens on the **same default ports as Sunshine**: TCP **47984, 47989,
48010** and UDP **47998–48000**, plus web UI TCP **47990**. On the **Trusted
VLAN** allow these so in-home Moonlight clients can auto-discover (mDNS) and
pair. Do NOT port-forward these publicly — for remote play we go over
**Tailscale** instead (see remote-streaming task).

---

## 5. Pair a client (in-home first!)

1. Put host + client on the **same Trusted VLAN** (mDNS auto-discovery).
2. Open Moonlight (or Artemis on Android) → the rig appears automatically.
3. Tap it → Moonlight shows a **PIN**.
4. On the rig web UI → **PIN** tab → enter the PIN + a device label → **Send**.
5. The client unlocks; launch Desktop or a game. Set that client's per-client
   permissions in the Apollo UI if you want to restrict what it can do.

> iOS/tvOS clients **must** pair on the same local network first (Apple rule).

Android handhelds: **Artemis** (Moonlight fork) pairs the same way; Apollo's
HDR + virtual-display support means no dummy-plug is needed on the host.

---

## 6. Verify

- `systemctl --user status apollo` → `active (running)`.
- Web UI reachable at <https://localhost:47990> and login works.
- A Moonlight client on the same VLAN sees the host and pairs.
- Encoder = NVENC; a test stream of the Desktop is smooth at your target res/FPS.
