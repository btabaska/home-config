# Operations — Tracker & AI sessions

The tracker is now **plain data + generated views** (the self-contained
`docs/index.html` HTML app was **retired 2026-07-14** — one source of truth).

- **`foss-setup/docs/tasks.json`** — canonical task **definitions** (id, title,
  track, run, mode, steps, deps, verify). Extracted from the old `taskData`.
- **`foss-setup/docs/progress.json`** — **status** maps (`done` / `deferred` /
  `retired`) + `_meta` counts.
- **`foss-setup/docs/archive/tracker-meta.json`** — ARCHIVAL (fix-43, 2026-07-19): run/track/tier
  groupings + ai-handoff map extracted from the retired `index.html`. No script reads it and it
  is not maintained (it predates the `ai` track); kept only as history.

Two generated views from that data: **`todo.md`** (repo root — remaining work)
and the **[wiki Roadmap](../roadmap/index.md)** (full browsable tracker). To
change a task: edit `tasks.json`/`progress.json`, then re-run
`scripts/docs/gen-todo.py` + `gen-roadmap-pages.py` + `build-wiki.sh`.

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

1. **Sync & verify** — pull the repo, read the wiki (this page + the roadmap)
   and the persistent memory notes, run the probe sweep across reachable
   hosts, diff against the tracker. Regressions reopen tasks first.
2. **Plan the wave** — pick the next batch from the diff + tracker:
   autonomous (`ai`/`vault`) items first, sized to one session.
3. **Execute** — one logical change at a time, repo-first (the host follows
   the repo, never the reverse).
4. **Prove it** — every task closes with its `verify` command and output.
   **No probe, no checkmark.**
5. **Record** — commit (GitHub + Forgejo via `publish-deploy.sh`), update
   `progress.json`, update the wiki pages touched — docs are part of "done".
6. **Hand back** — record state in the persistent memory notes and the
   relevant wiki pages: what changed (with proof), what's blocked, and a
   numbered human queue with exact click-paths and the test that confirms
   each item.

### Rules of engagement

- **Act freely**: repo edits, read-only probes, reversible verified fixes
  (restart a crash-looping container, redeploy a script, commit drift).
- **Ask first**: anything destructive, one-way doors (firewall migration),
  waking/rebooting hosts outside a maintenance task, anything touching
  credentials.
- **Secrets** travel only via the vault ([Secrets policy](secrets.md)).
- **Every out-of-band manual change gets one line in persistent memory** (and
  the relevant wiki page) — no exceptions. This rule alone would have caught
  the DHCP misconfiguration.

## The handoff protocol

Session-to-session memory now lives in **persistent memory notes + the wiki**
(the standalone `docs/handoff-rollout-state.md` / `docs/quality-hardening-state.md`
workstream docs were retired 2026-07-14 when the wiki became the single source of
truth). Record newest state, partial/deferred items ("do NOT mark done without
verifying"), key URLs, and the suggested next_up in memory and on the wiki page
each touches. Vault keys only — never secret values (see the rotation-log incident).
