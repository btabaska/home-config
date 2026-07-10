# Runbook — Verification

The framework that keeps "done" meaning *still working*. Born from the
2026-07-07 audit finding: several tracker tasks were checked and had silently
regressed — **nothing verified that done stays done.**

!!! success "Status: LIVE (verify-01…05 shipped)"
    Deployed on the mini at `/opt/verification/` (source of truth:
    `foss-setup/verification/` in the repo — keep them in sync). 74 checks
    across 10 `checks.d/*.yaml` domains as of 2026-07-09. Run it:
    `ssh mini '/opt/verification/bin/run-checks.sh'`.

## The design

Four layers:

1. **Probe library — `checks.d/`** (verify-01). One declarative YAML per
   service/host. Each check has:

    ```yaml
    # a real check, verbatim from checks.d/dns.yaml
    id: dns-mini-internal
    name: "AdGuard (mini) resolves internal name home.tabaska.us"
    host: mini                 # where the probe targets (or use the file-stem domain)
    cmd: dig +short +time=3 +tries=1 @192.168.10.2 home.tabaska.us
    expect: '^192\.168\.10\.[0-9]+$'   # regex over stdout; omit = exit-code only
    severity: crit             # crit | warn
    task_id: dns-01            # tracker task this check guards (auto-reopen)
    runbook: wiki/runbooks/dns.md
    enabled: true
    ```

    Everything the fleet audit found by hand becomes a repeatable check;
    every check links the wiki runbook that fixes it.

2. **Runner — `run-checks`** (verify-02). Globs `checks.d/`, executes each
   `cmd` over SSH from the mini (BatchMode, timeout), evaluates `expect`,
   writes timestamped JSON results (check id, host, status, output,
   duration). Runs on a systemd timer. Alerts via **ntfy only on regression**
   (pass→fail transition) so alerts stay meaningful — no daily "all green"
   noise.

    **Two tiers (since 2026-07-09)**: the full sweep runs daily at 07:15 PT
    (`verification.timer`), and the cheap `--host url` subset runs **hourly**
    (`verification-quick.timer`, `--notify` flag) so a functional regression
    is flagged within the hour, not the next morning. Each tier keeps its own
    state file, both are dead-manned in Healthchecks (`verification-mini`,
    `verification-quick-mini`).

    **Blanket coverage + tripwire (since 2026-07-09, user mandate: 100%
    surface)**: `checks.d/docker-fleet.yaml` diffs every host's running
    containers against `verification/coverage/<host>.containers` and flags
    unhealthy/restart-looping containers and failed systemd units — so
    port-less workers (beets, kometa, soularr, sidecar DBs…) page like
    anything else, and a NEW container that nobody added monitoring for
    fails the sweep until the manifest (and, if user-facing, a Kuma
    monitor) is updated. **Deploying or retiring a service = update the
    manifest in the repo and redeploy it to mini.**

    **Probe what the user experiences, not just what answers.** The
    2026-07-09 lesson: ai.tabaska.us had "no models" for hours while 63/63
    checks and 50 Kuma monitors stayed green, because every probe tested
    ports from outside and the broken hop was container→host on the rig
    (UFW). Layered fix: `rig-ai-e2e` (real completion, daily+hourly),
    `ai-stack-watchdog.timer` **on the rig** (the hop itself, every 10 min →
    Healthchecks dead-man), and a Kuma keyword monitor on the authenticated
    LiteLLM model list (~1 min). When adding a check, ask: *which vantage
    point sees this break?* — some paths are only visible from inside the
    host or container that uses them.

3. **LLM triage on the rig** (verify-03/04). When checks fail, a local model
   on the rig (small, scoped skills) triages: groups related failures, drafts
   the diagnosis against the runbook, proposes next steps. The rig runs 24/7
   (as of 2026-07-08), so triage is always on call and rig checks run like
   any other host's — the rig being down is itself an incident, not an
   expected state. Paging a human for a known-shape failure is what this
   layer exists to avoid.

4. **Auto-reopen** (verify-05). Regressions feed back into the tracker:
   failed checks map to task ids and produce **reopen suggestions** against
   `docs/progress.json` — a checked task whose probe fails gets reopened
   rather than silently lying. This closes the tracker trust gap.

## Operating it

- **Read results**: `mini:/var/lib/verification/results.json` (daily sweep);
  filtered runs write `results-<host>.json` alongside (e.g. `results-url.json`
  hourly, `results-docker-fleet.json`). Regressions arrive on ntfy.
- **Re-run a subset**: `run-checks.sh --host <host-or-domain>` — matches a
  check's `host` field or its file-stem domain, includes that domain's
  `enabled: false` checks, and never touches the daily state. There is no
  per-check flag; for one check, execute its `cmd` by hand — it's plain
  YAML, nothing hidden. `--json` prints results; `--notify`/`--no-notify`
  control ntfy. **Don't run it as root** (ssh-based checks falsely fail —
  the runner warns).
- **Every session start (AI agents)**: run the sweep, diff against
  `progress.json`, reopen regressions *before* planning new work. No probe,
  no checkmark.
- **Add a check with every new service** — step 7 of
  [Add a service](add-a-service.md) — and update
  `verification/coverage/<host>.containers` with every deploy/retire, or
  the docker-fleet tripwire fails the sweep by design.

## The other monitoring layers

Alongside the sweep: Uptime Kuma (53 monitors as of 2026-07-09 — liveness
plus keyword/functional, e.g. the authenticated LiteLLM model-list check),
Healthchecks (9 dead-man switches for scheduled jobs), Diun (image
awareness), Beszel (host metrics), and the standalone drill scripts
(`scripts/network/dns-resilience-verify.sh` and friends). Known standing
gap: **all alerting lives on the mini** — if the mini dies, everything is
silent (external watcher recommended; user decision pending).

## Human approval gate (policy — added 2026-07-08 at the operator's request)

Verification is **read-only by design**, at every layer:

1. Probes only observe (curl/dig/systemctl show/git status). They never restart, edit, or delete anything.
2. The local-LLM triage layer only *diagnoses*: its output is a JSON verdict with `suggested_fix_commands` — **suggestions are never executed by the runner, a timer, or any automation.**
3. Remediation happens exclusively through an interactive AI session (Claude), and anything that would change system state requires **explicit operator approval first**, presented as: *what is broken (evidence) -> what the fix will do -> what could go wrong*. Reply-to-approve in chat.

If any future change to this framework would let a model execute commands autonomously, that change itself requires operator approval and a note here.
