# mini-deadman — the off-mini dead-man (fix-63 / SH19)

The rig is **not** ansible-managed (see `configs/host/rig/README.md`); these
units are the canonical source and are deployed by hand.

## What it solves

The whole alerting/observability plane is co-located on **mini**: ntfy (pager),
Healthchecks + Uptime Kuma (both dead-man systems), all three verification
tiers, Caddy (sole TLS edge), AdGuard primary DNS, the Forgejo deploy remote.
A dead-man only works if it lives **outside** what it watches — so a total mini
outage (power/disk/kernel) kills every self-hosted pager and nothing can report
it. This watcher lives on the **rig** (24/7, off-mini) and pages over a channel
that never touches mini.

## Design choice (preference order)

Chosen: **option 1 — a self-hosted, off-mini watcher** (rig) that publishes
directly to the **public ntfy.sh** relay on a secret topic the phone
subscribes to. Picked over a purely-external heartbeat because a robust
off-mini self-hosted watcher *does* exist (rig is 24/7 and already reaches
ntfy.sh), and it needs no external account. iOS push fundamentally routes
through ntfy.sh regardless, so using ntfy.sh directly for this last-resort page
is consistent with the fleet's existing posture (`NTFY_UPSTREAM_BASE_URL`).

**no-cloud tradeoff (foss-03):** one public relay is used for this one
safety-critical function only. The payload is a bare alert (no secrets); the
topic name is the read secret.

**Residual gap (documented):** if the rig is *also* down (e.g. whole-house
power loss) there is no page — but that failure mode is self-evident (the whole
house is dark) and the phone is on cellular. An optional belt-and-suspenders is
a free external heartbeat (healthchecks.io) pinged *by* mini; it needs operator
signup, so it is left as a documented follow-up, not built here.

## How it works

- Timer every 5 min → probes mini's Caddy TLS edge (`192.168.10.2:443`).
- 3 consecutive misses (~15 min, tolerates a Caddy restart) → **page** to
  `ntfy.sh/<secret-topic>` at max priority.
- Re-pages hourly while still down; sends a **RECOVERED** notice when the edge
  answers again.
- DNS-resilient: resolves `ntfy.sh` against a public resolver (mini's AdGuard
  may be down) and hands curl a pinned `--resolve`.
- Writes `/var/lib/mini-deadman/heartbeat` every run — the verification check
  `alert-offmini-deadman-armed` reads it to prove the watcher is live.

## Deploy (on the rig)

```bash
sudo install -m755 mini-deadman.sh /usr/local/bin/mini-deadman.sh
sudo install -m600 mini-deadman.env.example /etc/mini-deadman.env
# edit /etc/mini-deadman.env: set MINI_DEADMAN_NTFY_TOPIC from vault
#   (alerting.mini_deadman_ntfy_topic)
sudo install -m644 mini-deadman.service mini-deadman.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mini-deadman.timer
```

## Self-test (proves it fires WITHOUT mini)

```bash
# forces the DOWN path and publishes to ntfy.sh; mini is never contacted
sudo MINI_DEADMAN_FORCE_DOWN=1 FAIL_THRESHOLD=1 \
     MINI_DEADMAN_STATE_DIR=/tmp/md-test /usr/local/bin/mini-deadman.sh
# read it back straight from the public relay (topic from vault):
curl -s "https://ntfy.sh/<topic>/json?poll=1&since=5m"
```

## Operator follow-up (human)

Subscribe the phone's ntfy app to the **ntfy.sh** server (not the self-hosted
one) on topic `alerting.mini_deadman_ntfy_topic`. Give it a loud/critical
notification sound — this topic only ever fires when mini is dead.
