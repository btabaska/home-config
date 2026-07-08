# Sunshine on the CachyOS rig — install, config & autostart runbook

Sunshine (by LizardByte) is the self-hosted game-stream **host**. Moonlight is the
**client**. This runbook covers installing Sunshine on the CachyOS/Arch rig with
NVENC (3090 Ti), turning it on at boot, and the first-time web-UI setup.

**Authoritative docs**
- Getting Started (install, all platforms): <https://docs.lizardbyte.dev/projects/sunshine/latest/md_docs_2getting__started.html>
- LizardByte pacman repo (prebuilt Arch packages): <https://github.com/LizardByte/pacman-repo>
- AUR package (alternative): <https://aur.archlinux.org/packages/sunshine>
- Moonlight setup guide (client side): <https://github.com/moonlight-stream/moonlight-docs/wiki/Setup-Guide>

---

## 1. Install on Arch / CachyOS

**Preferred — LizardByte prebuilt pacman repo** (best supported). Follow the repo
instructions to add the LizardByte pacman repository, then:

```bash
sudo pacman -S sunshine
# NVENC (NVIDIA) hardware encoding support:
sudo pacman -S cuda
```

**Alternative — AUR** (build from PKGBUILD; "use AUR at your own risk"):

```bash
# with an AUR helper, e.g. paru/yay:
paru -S sunshine
```

> 3090 Ti note: Sunshine uses **NVENC** for H.264/HEVC/AV1 4K HDR encode — this is
> separate from the rig's render workload, so streaming costs little GPU. Ensure
> the proprietary NVIDIA driver + `cuda` are installed.

---

## 2. Autostart (run on boot, as your user)

Sunshine ships a **systemd --user** service. As of recent (2026) releases the unit
was renamed from `sunshine.service` to a reverse-DNS name:

```bash
# enable + start now, and on every login/boot:
systemctl --user enable --now app-dev.lizardbyte.app.Sunshine

# check status:
systemctl --user status app-dev.lizardbyte.app.Sunshine
```

To have the user service start at boot **without an interactive login** (the 24/7
rig boots unattended, e.g. after a power-outage recovery), enable lingering for
your user:

```bash
sudo loginctl enable-linger "$USER"
```

> If `systemctl --user enable sunshine` says "Unit sunshine.service does not exist",
> you're on a new build — use the `app-dev.lizardbyte.app.Sunshine` name above.
> Ref: <https://github.com/LizardByte/Sunshine/issues/4882>

### Wayland / display capture caveat
For the rig to capture and stream even when no monitor is attached (or to get a
specific resolution), you typically need a **virtual display / dummy HDMI plug**, or
run an Xorg session. KMS/Wayland capture works but may require permissions
(`cap_sys_admin`) — the install script usually sets this up. See Getting Started.

---

## 3. First-time web UI

1. Open **<https://localhost:47990>** on the rig (self-signed cert → accept the warning).
2. Create the **username + password** on first load (this protects the web UI — do
   this immediately; it is not set by default).
3. Confirm the encoder shows **NVENC** under Configuration → Audio/Video.
4. (Optional) Set output resolution/FPS/HDR caps and add apps under **Applications**
   (Steam Big Picture is pre-added; add specific game executables as needed).

---

## 4. Firewall / ports

Sunshine listens on (default): TCP **47984, 47989, 48010** and UDP **47998–48000**,
plus web UI TCP **47990**. On the **Trusted VLAN** allow these so in-home Moonlight
clients can auto-discover (mDNS) and pair. Do NOT port-forward these publicly — for
remote play we go over **Tailscale** instead (see remote-streaming task).

---

## 5. Pair a client (in-home first!)

1. Put host + client on the **same Trusted VLAN** (mDNS auto-discovery).
2. Open Moonlight (or Artemis on Android) → the rig appears automatically.
3. Tap it → Moonlight shows a **PIN**.
4. On the rig web UI → **PIN** tab → enter the PIN + a device label → **Send**.
5. The client unlocks; launch Desktop or a game.

> iOS/tvOS clients **must** pair on the same local network first (Apple rule).

Android handhelds: use **Apollo** (Sunshine fork, better HDR, no dummy-plug needed)
+ **Artemis** (Moonlight fork). See: <https://github.com/ClassicOldSong/Apollo>

---

## 6. Verify

- `systemctl --user status app-dev.lizardbyte.app.Sunshine` → `active (running)`.
- Web UI reachable at <https://localhost:47990> and login works.
- A Moonlight client on the same VLAN sees the host and pairs.
- Encoder = NVENC; a test stream of the Desktop is smooth at your target res/FPS.
