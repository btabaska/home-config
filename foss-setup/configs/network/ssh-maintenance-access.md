# SSH & maintenance access

With ~25 services across 4-5 boxes plus an off-site seedbox, you SSH between
machines constantly. Make it frictionless and secure **once**, not ad-hoc
forever. You already run Tailscale on every node (net-07/08/11), so lean on it
for the access layer instead of hand-distributing keys.

Two layers:

1. **Tailscale SSH** — the primary, key-less path (net-13).
2. **Classic SSH key + `~/.ssh/config`** — the break-glass fallback (net-14).

Plus a fleet lever: **Ansible** for running one command across every box
(glue-07, see `../ansible/`).

---

## 1. Tailscale SSH (primary)

Run on every node:

```bash
./scripts/network/tailscale-ssh-enable.sh   # or: sudo tailscale set --ssh
```

Then apply the access policy in the Tailscale admin console (Access Controls)
from [`tailscale-acl-ssh.hujson`](tailscale-acl-ssh.hujson):

- Admin devices (laptop, phone) get `tag:admin`.
- Hosts get `tag:server`.
- The `ssh` rule allows **only `tag:admin` -> `tag:server`**, as a chosen Unix
  user, with a `checkPeriod` re-auth window.

Why this first:

- **No `authorized_keys` sprawl** — auth is the tailnet identity.
- **Nothing on the public internet** — no port 22 exposed anywhere.
- **Central revocation** — de-auth a lost laptop in the console and it's locked
  out of every host instantly; no key rotation across five boxes.
- **Optional session recording** to a recorder node for an audit trail.

After this, from any `tag:admin` device (using the `mini` alias from
`ssh-config.example`, which sets the right user + MagicDNS host):

```bash
ssh mini       # just works, over the tailnet, no key prompt
```

---

## 2. Classic SSH key + `~/.ssh/config` (break-glass)

Tailscale SSH depends on the control plane being reachable. Keep a normal path
for when it isn't.

```bash
ssh-keygen -t ed25519 -C "$USER@maintenance"
ssh-copy-id -i ~/.ssh/id_ed25519.pub <admin-user>@<host-tailnet-name>   # per host
install -m 600 configs/network/ssh-config.example ~/.ssh/config # then edit it
```

[`ssh-config.example`](ssh-config.example) gives you `ssh nas` / `ssh mini` /
`ssh rig` / `ssh ha` / `ssh seedbox` aliases, `AddKeysToAgent yes`, and
`ForwardAgent no` by default (enable agent forwarding per-command only when you
actually need to hop). Track it with **chezmoi** (glue-04) so a rebuilt box gets
your whole SSH setup back with `chezmoi init --apply`, and the key rides the
Tier-1 backup (nas-04/05).

---

## 3. Per-host quirks (the things that bite)

### Synology DSM (NAS)
SSH is **off by default**:

- Control Panel -> Terminal & SNMP -> **Enable SSH service**.
- Make it **key-based** and put it behind the **DSM 2FA** you enforce in sec-01.
- Don't SSH as the default `admin`/`root` — use a **dedicated admin user**.
- DSM **rewrites `sshd_config` on updates**, so treat deep SSH customization as
  non-persistent and record it in `hosts/ds920/restore.md`.

### Home Assistant (HAOS)
There is no normal user shell:

- Day-to-day: install the official **Advanced SSH & Web Terminal** add-on and
  drop your public key into its config (default port 22).
- Low-level: the **`root@<ha-ip>:22222`** debug port.
- This is the same box whose `/config` already lives in Git (sbom-03 / HA).

### On-demand rig (CachyOS)
It's asleep most of the time, so **wake, then SSH**:

```bash
RIG_MAC=aa:bb:cc:dd:ee:ff ./scripts/gaming/wake-rig.sh && ssh rig
```

This reuses the Wake-on-LAN setup from game-08. The rig's own backup (nas-05)
and SBOM (sbom-02) timers use the same "while awake" wake path, so manual SSH
and automation share one wake mechanism rather than fighting auto-suspend
(game-09).

### Seedbox
Already keys-only and hardened (sec-04). Just add it to the same
`~/.ssh/config` and your tailnet so it's reachable like any other node, with
nothing extra exposed.

---

## 4. Fleet maintenance

For "run one command across every box" (patch / reboot / audit), use the small
Ansible setup in [`../ansible/`](../ansible/) (glue-07). It's agentless and rides
the SSH/Tailscale path above. It is the **manual** lever; automatic per-host
security patching stays with **unattended-upgrades** (sec-05).
