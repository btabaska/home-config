# Operations — Tracker & AI sessions

The rollout is driven by **Plan v3**: `foss-setup/docs/index.html`, a
self-contained HTML tracker with **223 tasks (as of 2026-07-09) organized
as staged runs** — the count grows as runs add work.
This page is how to read it, and the protocol AI sessions follow.

## The tracker

- **Runs (0–7)** are staged waves, each with a goal and its gates — e.g.
  Run 1 "DNS & Verification" (fail-open chain + checks.d), Run 2 "Home
  surface" (service catalog, Homepage, this wiki), Run 7 "Capstone"
  (rebuild drills, verification green fleet-wide, then delete the vault and
  rotate keys).
- **Modes** tag who can execute each task:
  `ai` (autonomous), `vault` (AI once a vault key is filled),
  `mixed` (AI + human), `human` (GUI/physical work — UniFi clicks, DSM
  Task Scheduler, hardware).
- **Gates** are explicit blockers a run can't pass without (e.g. B2 account
  + app key; rig sudo password; Tailscale ACL fix). Gates are surfaced as
  callouts on the run cards.
- Each task carries `steps`, `commands`, `files`, `docs[]` links, and a
  **`verify`** block — the named probe that defines "done".

## Progress-as-code

- Canonical record: **`foss-setup/docs/progress.json`** (committed) —
  `_meta` + a `done` map of task ids. The HTML auto-loads and additively
  merges it when served over HTTP; on `file://` use the **Import progress**
  button.
- The browser's localStorage (`foss-analogue-progress-v1`) is a working copy,
  not the truth. Export/merge back to `progress.json` and commit.
- **Reopened ids are intentionally absent from `done`** — a regression means
  the checkmark comes off (dns-02, game-10, nas-08 were all reopened by the
  2026-07-07 audit, later re-closed). This is automated now (verify-05):
  failed checks that carry a `task_id` write
  `mini:/var/lib/verification/reopen-suggestions.json` and ntfy a summary —
  session-start protocol is to process that file first. A `retired` block
  (2026-07-09) holds deliberately-abandoned tasks (the SBOM feature) so
  they neither count as done nor look like regressions.

## How AI sessions work

The standing session shape (from the audit's operating flow):

1. **Sync & verify** — pull the repo, read
   `docs/handoff-rollout-state.md`, run the probe sweep across reachable
   hosts, diff against the tracker. Regressions reopen tasks first.
2. **Plan the wave** — pick the next batch from the diff + tracker:
   autonomous (`ai`/`vault`) items first, sized to one session.
3. **Execute** — one logical change at a time, repo-first (the host follows
   the repo, never the reverse).
4. **Prove it** — every task closes with its `verify` command and output.
   **No probe, no checkmark.**
5. **Record** — commit (GitHub + Forgejo via `publish-deploy.sh`), update
   `progress.json`, update the wiki pages touched — docs are part of "done".
6. **Hand back** — end with a handoff in `docs/handoff-rollout-state.md`:
   what changed (with proof), what's blocked, and a numbered human queue
   with exact click-paths and the test that confirms each item.

### Rules of engagement

- **Act freely**: repo edits, read-only probes, reversible verified fixes
  (restart a crash-looping container, redeploy a script, commit drift).
- **Ask first**: anything destructive, one-way doors (firewall migration),
  waking/rebooting hosts outside a maintenance task, anything touching
  credentials.
- **Secrets** travel only via the vault ([Secrets policy](secrets.md)).
- **Every out-of-band manual change gets one line in the state doc** — no
  exceptions. This rule alone would have caught the DHCP misconfiguration.

## The handoff protocol

`foss-setup/docs/handoff-rollout-state.md` is the session-to-session memory:
newest state at the top, per-session sections, partial/deferred tables
("do NOT mark done without verifying"), key URLs, and the suggested next_up.
Read it at session start; write it at session end. Vault keys only — never
secret values (see the rotation-log incident).
