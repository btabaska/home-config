# LAN exposure & listener-drift baseline

What to do when a `lan-listeners-drift-*` or `booklogr-registration-posture`
verification check fires (ntfy topic `verification`). This is the **LAN-side**
companion to [Edge / WAN exposure](edge-exposure.md): edge-exposure watches the
one WAN port; this watches every **all-interface (`0.0.0.0` / `*` / `[::]`) TCP
listener** on the trusted VLAN.

Outcome of **fix-51** (fleet-sweep 2026-08-02 findings SM56, SM58, SM24).

## The intended-exposure model (why most 0.0.0.0 binds are fine)

This is a flat-LAN homelab on a single trusted VLAN. **Caddy on the mini
(`:80`/`:443`) is the auth edge** — public hostnames route through it and it
applies basic_auth / forward-auth. But nearly every containerised service is
*also* published on `0.0.0.0` by docker-proxy, so a device already on the LAN
can hit the service port directly and **bypass Caddy's auth** (the
"Marinara-class hole"; fleet-sweep SM58 demonstrated `ollama`, `comfyui`,
`llama-swap` on the rig answering unauthenticated to an arbitrary LAN host).

That is an **accepted defense-in-depth tradeoff**, not a bug to firewall away:
the mitigation is VLAN segmentation (open task **ha-19**, IoT VLAN 20), after
which untrusted/IoT devices no longer share this L2. Until then the posture is
"the LAN is trusted." So the deliverable here is **a documented baseline of what
*should* listen + a tripwire on anything NEW**, not aggressively binding live
services to loopback (which would break the LAN-direct access paths people and
containers rely on).

The baseline lives in the repo, one file per host, consumed by the check:

- `foss-setup/verification/assets/expected-listeners/mini.ports`
- `foss-setup/verification/assets/expected-listeners/rig.ports`
- `foss-setup/verification/assets/expected-listeners/nas.ports`

Each is a commented port allowlist (port → owning service + why it's exposed).
Only wildcard binds count; `127.0.0.1`, tailscale-IP, host-IP and ephemeral
listeners are deliberately out of scope so the baseline stays stable.

## `lan-listeners-drift-<host>` failed (warn) — a NEW all-interface listener appeared

The check output is `LISTENER_DRIFT=<host>:<port,port> (NEW all-interface
listener not in baseline …)`. This is the exact tripwire that was missing when a
bare `nc -lvnp 9999` sat open on `0.0.0.0` on the mini for **17 days** (SM56 — a
stray detached `tmux` session `rigshell` from the 2026-07-16 audit; killed with
`tmux kill-session -t rigshell`, nothing respawns it).

1. Identify what opened the port:
   `ssh <host> 'sudo ss -tlnp | grep ":<port> "'` (rig/nas sudo needs the vault
   password — `sudo.rig_password` / `sudo.nas_password`).
2. Trace provenance before killing: `ps -o pid,ppid,etime,user,args -p <pid>`
   and `ls -l /proc/<pid>/cwd`. Check whether a systemd unit, cron, or a
   detached `tmux`/`screen` session would respawn it — kill the *respawner*, not
   just the process, or it comes back.
3. Decide:
   - **Rogue / debug leftover** (like the `nc`): kill it durably and confirm the
     port is gone and stays gone.
   - **A real new service you deployed**: add the port to the host's
     `expected-listeners/<host>.ports` with a comment, redeploy verification, and
     (if it should be Caddy-fronted) add the vhost + confirm it's not needed on
     the LAN directly.
4. `LISTENER_DRIFT=UNREACHABLE:<host>` means the runner couldn't reach the host
   to enumerate — a vantage failure (host down / ssh), not an exposure; fix the
   host, not the baseline.

## `booklogr-registration-posture` failed (warn) — container/.env disagree

BookLogr registration is **intentionally left OPEN**
(`AUTH_ALLOW_REGISTRATION=True`) pending a future household lockdown (SM24) — the
check does **not** assert `False`, it only **records** the current value so a
future flip is visible in `results.json` history. It fails **only** on
anti-drift: the running `booklogr-api` container env and the committed
`/opt/stacks/booklogr/.env` disagree (`match=no`), or the setting vanished
(`UNSET`).

- `match=no`: someone edited `/opt/stacks/booklogr/.env` but never redeployed
  (or vice-versa). Reconcile them and `docker compose up -d` in
  `/opt/stacks/booklogr` so the running value matches the committed one, then
  mirror `.env`-adjacent config back to
  `foss-setup/configs/docker-stack/stacks/booklogr/`.
- When the operator *does* lock registration down: set
  `AUTH_ALLOW_REGISTRATION=False` in `/opt/stacks/booklogr/.env`, redeploy, and
  the check keeps passing (it records `False`, `match=yes`). Mind the BookLogr
  two-vhost redeploy gotcha: `BL_API_ENDPOINT` is baked into the web bundle at
  container start, so a config change needs a full `docker compose up -d`.

## Deploy / update the baseline

```
# edit the .ports file(s) and/or bin/listener-drift.sh in the repo, then:
ssh mini 'sudo tee /opt/verification/assets/expected-listeners/<host>.ports' \
  < foss-setup/verification/assets/expected-listeners/<host>.ports
# (or run the full scripts/verification/deploy.sh once the repo is committed)
```

Re-baseline after an intentional service change so the check is clean again;
verify with
`ssh mini '/opt/verification/bin/listener-drift.sh <host>'` → `LISTENER_DRIFT=NONE`.
