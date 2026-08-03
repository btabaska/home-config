# Runbook — The alerting plane (and its off-mini safety net)

Almost the entire alerting/observability plane lives on **mini**: ntfy (the
pager), Healthchecks + Uptime Kuma (both dead-man systems), all three
verification tiers, plus Caddy (the sole TLS edge), AdGuard (primary DNS) and
the Forgejo deploy remote. That co-location is convenient but it has one nasty
property — **a total mini outage takes down every self-hosted pager at once, so
nothing on mini can tell you mini is dead** (fleet-sweep SH19). This runbook
covers the plane and the pieces (fix-63) that make it survivable.

## Off-mini dead-man — the one alert that survives mini's death

- **Where it lives:** the **rig** (24/7, off-mini). Unit
  `mini-deadman.timer` → `/usr/local/bin/mini-deadman.sh`. Canonical source:
  `configs/host/rig/mini-deadman/`.
- **How it pages:** every 5 min it TCP-probes mini's Caddy TLS edge
  (`192.168.10.2:443`). Three consecutive misses (~15 min; tolerates a Caddy
  restart) → it publishes a **max-priority page directly to the public
  `ntfy.sh`** server on a secret topic (vault `alerting.mini_deadman_ntfy_topic`),
  **bypassing mini entirely**. It re-pages hourly while down and sends a
  RECOVERED notice when the edge returns. DNS is made mini-independent (resolves
  `ntfy.sh` against a public resolver, since mini hosts primary DNS).
- **Why ntfy.sh (no-cloud tradeoff):** this fleet leans no-cloud (foss-03), but
  a dead-man is only meaningful *outside* the thing it watches, and iOS push for
  the self-hosted ntfy already relays through ntfy.sh anyway. So for this **one
  safety-critical last resort** we accept a single public relay carrying a bare
  alert (no secrets; the topic name is the read secret). Chosen over an external
  hosted heartbeat because a robust self-hosted off-mini watcher already exists
  (the rig) and needs no external account.
- **Residual gap:** if the **rig is also down** (whole-house power loss) there is
  no page — but that is self-evident, and the phone is on cellular. Optional
  belt-and-suspenders: a free healthchecks.io check pinged *by* mini (needs
  operator signup) — left as a documented follow-up.

### Operator follow-up (required to actually receive it)

Subscribe the phone's ntfy app to the **ntfy.sh** server (not the self-hosted
one) on the `alerting.mini_deadman_ntfy_topic` topic, with a loud/critical
sound. This topic only ever fires when mini is dead.

### Self-test (proves it fires without mini)

```bash
ssh rig 'sudo MINI_DEADMAN_FORCE_DOWN=1 FAIL_THRESHOLD=1 \
  MINI_DEADMAN_STATE_DIR=/tmp/md-test /usr/local/bin/mini-deadman.sh'
# read it straight back off the public relay (topic from vault):
curl -s "https://ntfy.sh/<topic>/json?poll=1&since=5m"
```

Verified 2026-08-03: the forced-down run published *MINI DOWN — self-hosted
alerting is dark* to ntfy.sh and it was read back off ntfy.sh — a path that
never touched mini.

## Rig-down auto-recovery in the fast tier (WoL)

The rig is 24/7, so rig-down is an incident. The **fast tier** (every 10 min)
detects it, and now also *recovers* it: `verification-fast.service` runs
`/opt/verification/bin/rig-wol-selfheal.sh` as an `ExecStartPost`. It fires a
Wake-on-LAN magic packet the moment the rig is unreachable and **re-pages
`homelab-alerts` hourly** while it stays down. Previously WoL recovery lived
only in the *daily* cycle (`llm-triage.sh`), so a rig that dropped just after a
daily run got no automated wake for up to ~24h (SM54). See also
[Recover the rig](wake-the-rig.md).

## ntfy retention

`NTFY_CACHE_DURATION=720h` (30 days) in `/opt/stacks/ntfy/` — up from the ntfy
12h default, which had already purged the 07-31 rig-outage pages before they
could be reviewed the next morning (SL45). Post-incident reconstruction now
works from the ntfy cache (`/json?since=…`).

## Uptime Kuma status page

Published page: **<https://uptime.tabaska.us/status/fleet>** — 4 groups (Core
Infrastructure, Media & Photos, AI & Apps, Game Servers), 25 monitors. The old
`test` page was an empty placeholder (SL23) and was removed. The Homepage
*Uptime Kuma* tile now carries an `uptimekuma` widget bound to `slug: fleet`.
Re-seed idempotently with `scripts/uptime-kuma/seed-status-page.sh` (Kuma stores
all config in its DB, so that script is the codified source of truth).

## Alert-delivery drill (does a page actually reach the phone?)

Every alerting check proves publishes succeed *server-side*; none proved the
**last mile**. The weekly drill (`alert-delivery-drill.timer` on mini →
`/opt/verification/bin/alert-delivery-drill.sh`, Mondays 09:00) publishes a
timestamped message to a dedicated **`alert-drill`** topic over the same
ntfy → iOS-relay → device path real alerts use.

- **Send** is automated and freshness-checked (`alert-delivery-drill-fresh`).
- **Receipt is an operator human-confirm:** subscribe the phone to `alert-drill`
  (the `phone` user already has read on all topics) and, when the Monday drill
  lands, delivery is confirmed for the week.
- **Closed-loop upgrade (optional):** an iOS Shortcut that pings a Healthchecks
  dead-man on receiving the drill would make receipt machine-verifiable — create
  a Healthchecks check `alert-delivery-received` (period 8d) and point the
  Shortcut at its ping URL.

## Verification checks (fix-63)

| check | proves |
|-------|--------|
| `alert-offmini-deadman-armed` | the rig watcher's timer is active and heartbeating (SH19) |
| `alert-wol-selfheal-fast-tier` | WoL self-heal is wired into the fast tier (SM54) |
| `alert-kuma-statuspage-nonempty` | the published `fleet` status page has groups + monitors (SL23) |
| `alert-delivery-drill-fresh` | the delivery drill was sent within 8 days (SM39) |
