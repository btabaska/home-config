# Runbook — Verification

The framework that keeps "done" meaning *still working*. Born from the
2026-07-07 audit finding: several tracker tasks were checked and had silently
regressed — **nothing verified that done stays done.**

!!! note "Status: being built (pending: verify-01…05)"
    A concurrent work stream is implementing this under
    `foss-setup/verification/` (config may land as
    `configs/verification/checks.d/`). This page documents the design from
    Plan v3 so operators and agents know the shape; update paths/commands
    when the framework lands.

## The design

Four layers:

1. **Probe library — `checks.d/`** (verify-01). One declarative YAML per
   service/host. Each check has:

    ```yaml
    id: dns-nas-secondary
    host: nas            # where the probe targets
    cmd: dig @192.168.10.4 example.com +time=2 +tries=1
    expect: NOERROR      # what "pass" means
    severity: critical
    runbook: https://wiki.tabaska.us/runbooks/dns-outage/
    ```

    Everything the fleet audit found by hand becomes a repeatable check;
    every check links the wiki runbook that fixes it.

2. **Runner — `run-checks`** (verify-02). Globs `checks.d/`, executes each
   `cmd` over SSH from the mini (BatchMode, timeout), evaluates `expect`,
   writes timestamped JSON results (check id, host, status, output,
   duration). Runs on a systemd timer. Alerts via **ntfy only on regression**
   (pass→fail transition) so alerts stay meaningful — no daily "all green"
   noise.

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

## Operating it (once live)

- **Read results**: latest results JSON on the mini (path set by verify-02);
  regressions arrive on ntfy.
- **Re-run one check**: `run-checks --only <check-id>` (or execute the
  check's `cmd` by hand — it's plain YAML, nothing hidden).
- **Every session start (AI agents)**: run the sweep, diff against
  `progress.json`, reopen regressions *before* planning new work. No probe,
  no checkmark.
- **Add a check with every new service** — step 7 of
  [Add a service](add-a-service.md).

## Until then

The interim verification layer is: Uptime Kuma (HTTP monitors + ntfy),
Healthchecks (dead-man's switch for scheduled jobs), Diun (image awareness),
Beszel (host metrics), and the standalone drill scripts
(`scripts/network/dns-resilience-verify.sh` and friends).

## Human approval gate (policy — added 2026-07-08 at the operator's request)

Verification is **read-only by design**, at every layer:

1. Probes only observe (curl/dig/systemctl show/git status). They never restart, edit, or delete anything.
2. The local-LLM triage layer only *diagnoses*: its output is a JSON verdict with `suggested_fix_commands` — **suggestions are never executed by the runner, a timer, or any automation.**
3. Remediation happens exclusively through an interactive AI session (Claude), and anything that would change system state requires **explicit operator approval first**, presented as: *what is broken (evidence) -> what the fix will do -> what could go wrong*. Reply-to-approve in chat.

If any future change to this framework would let a model execute commands autonomously, that change itself requires operator approval and a note here.
