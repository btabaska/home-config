---
description: Full read-only fleet sweep — architecture review, log sweep, per-service deep scans, and end-to-end chain probes; verified findings land in a dated audit doc + clustered fix-NN queue for /resolve-finding
argument-hint: (empty = full sweep) | quick (harvest existing signal only, no fan-out) | focus <host or chain> (e.g. focus nas, focus books, focus ai)
---

You are running a full-fleet quality sweep of the Going Analogue homelab, requested as:
**$ARGUMENTS**. The product is a **fix queue**: a dated findings doc with runnable evidence, a
clustered worklist, and `fix-NN` tasks that `/resolve-finding` can drive — NOT fixes. This sweep is
modeled on the 2026-07-16 quality-gate audit (26 auditor lanes, skeptic verification, completeness
critic + gap fillers, ~2.8M tokens) whose core lesson stands: **30+ services were green-but-broken
— liveness is not health.** Probe the consumer end of everything.

## Hard rules (read before anything else)

- **STRICTLY READ-ONLY on every host.** No restarts, edits, deletes, config changes, or fixes — a
  live problem you find gets *filed*, not repaired (even a one-liner; the fix session hardens and
  codifies, a sweep-fix creates drift). The only sanctioned writes: repo files in Step 5, scratch
  state (`VERIFICATION_STATE_DIR`) for the runner, and the transient artifacts of existing
  self-cleaning e2e checks. The audit doc must be able to say "Nothing was modified on any host."
- **Never paste secret values** into chat, findings, evidence blocks, commits, or docs — vault key
  paths only. Read vault values with python3+yaml into shell vars and pipe them.
- **Every finding needs copy-paste-runnable evidence** (the literal commands + output). Resolvers
  start from those exact commands.
- Run from the operator Mac inside `~/GitHub/Home` (the vault exists only there).

## Step 0 — load context (cold session)

1. Read repo-root `CLAUDE.md` (fleet access, secrets, anti-drift ownership map, mandates).
2. Read **`foss-setup/docs/fleet-sweep-reference.md`** in full — it is this command's other half:
   §1 working access recipes per host, §2 verification-framework harvest, §3 the end-to-end chain
   matrix, §4 log surfaces, §5 the failure-pattern taxonomy (this fleet's priors), §6 drift axes,
   §7 contradiction sources, §8 topology/SPOF, §9 known-normal states (do-not-file list), §10 the
   exact output formats. Facts there were verified 2026-08-02; re-verify counts live before citing.
3. `git pull`; read `foss-setup/docs/tasks.json` + `docs/progress.json` to build the OPEN-task and
   done-task sets (dedup inputs); skim the prior sweep/audit docs named in CLAUDE.md so known
   findings get `known_issue: true` instead of duplicate tasks.
4. Preflight access: one cheap read-only probe per host (mini, nas, rig, seedbox ssh; ha REST). If
   a host is unreachable, that is itself a critical finding — note it, sweep the rest, don't block.

## Step 1 — harvest existing signal (cheap, before any fan-out)

The fleet already self-reports; collect it first so lanes verify rather than rediscover:

1. Audit-safe full check run (~8 min, run backgrounded):
   `ssh mini 'mkdir -p /tmp/verify-audit && VERIFICATION_STATE_DIR=/tmp/verify-audit /opt/verification/bin/run-checks.sh --no-notify --json'`
   — never without `VERIFICATION_STATE_DIR` (it would clobber daily state and page ntfy).
2. While it runs: `/var/lib/verification/{last-summary.md,reopen-suggestions.json,acks.json}` +
   recent `triage-*.md`; Healthchecks API state (anything not `up`, or last_ping > period+grace);
   `systemctl --failed` + failed-timer scan on mini/rig; docker restart counts on all three docker
   hosts; coverage-manifest diffs (reference §6.4); git hygiene (`/opt/stacks` porcelain +
   unpushed, foss-setup clean).
3. Fold the check-run results in: every failing check is a seed finding (with its `task_id` as the
   dedup key); every *passing* consumer check is a chain you can mark verified instead of re-probing.

**If $ARGUMENTS is `quick`: skip Steps 2–3**, verify the Step-1 failures just enough to classify
them, and go to Step 4 with what you have. If `focus <x>`: run Steps 2–3 restricted to the matching
host/chain/service lanes plus the repo-drift lane.

## Step 2 — orchestrated fan-out (the sweep proper)

Use the **Workflow tool** to fan out read-only auditor lanes (this command is your authorization to
orchestrate; if Workflow is unavailable, batch parallel Agent subagents instead, ≤8 at a time).
Every lane prompt must carry: the hard rules above, the relevant reference-doc excerpts (access
recipes for its hosts, its chain rows, the failure-pattern taxonomy, known-normal list), and a
structured-output schema matching the findings JSON fields (reference §10b: severity, host,
component, title, detail, evidence, confidence, known_issue — auditor is the lane name). Lanes
return findings AND green confirmations (info-severity) — "verified working end to end" is signal.

Lane roster for a full sweep (~30 lanes; trim for focus mode):

- **Host lanes (5)** — `host:mini|nas|rig|seedbox|ha`: inventory vs coverage manifest, restart
  loops, failed units/timers/crons, disk, journal error+flood scan (reference §4–5), host hygiene.
- **Service lanes (9)** — `svc:…`: arr-stack+request-layer, nas-apps (Immich/Plex/Jellyfin/Komga/
  ABS/CWA/Stash), media-aux (kometa/bazarr/pinchflat/metube/beets/navidrome/tautulli), ai-stack
  (LiteLLM/llama-swap/OWUI/ComfyUI/arbiter/mcpo/ollama-shim), infra-mini (Caddy/AdGuard/Unbound/
  Forgejo/Homepage), monitoring-stack (runner/Kuma/Healthchecks/ntfy/Beszel/Diun/Scrutiny),
  docs-life (Paperless/Wallabag/Mealie/Miniflux/BookLogr/Memos/n8n), gaming (AMP/Palworld/playit/
  Terraria/RomM/ES-DE/BedrockConnect), reading (Bookshelf/rreading-glasses/libreseerr/Shelfmark/
  Mylar3/Suwayomi). Each: config sanity, error logs, **zero-throughput probe** (newest-item
  timestamp + primary-table count on every "green" service — taxonomy #13), auth-rot scan.
- **Flow lanes (one per chain family, reference §3)** — `flow:…`: movies-tv, music, books(+
  shelfmark), audiobooks+ipod, manga+comics, photos, youtube, journaling, ai-serving+image-gen,
  monitoring-alerting, bug-intake, git-control-plane, backups, syncthing-mesh, edge+dns, ha,
  game-servers, retro. Each walks its chain hop-by-hop and probes the CONSUMER end with the
  matrix's probe recipe; a chain marked **⚠ gap** gets a manual one-shot probe of the uncovered
  leg. Missing-e2e-coverage is itself a finding (monitoring-gap class, mandate 2).
- **Repo/drift lanes (4)** — `repo:live-drift` (all 13 axes, reference §6), `repo:verification-
  suite` (the runner audits itself: check quality, liveness-masquerading-as-consumer probes, triage
  health, double-run placement), `repo:tracker-wiki` (tracker coherence + done-but-failing lies +
  contradiction sources §7), `repo:junk-deadpaths`.
- **Architecture lane (1)** — `arch:topology`: SPOF review (§8), cross-host dependency health,
  exposure posture, docs-vs-live contradictions — findings here are allowed to be design-level
  (e.g. "alerting plane co-located with everything it monitors") at medium confidence.

Practical limits: NAS-touching lanes must not run concurrent git operations (pull deadlock) and
should stagger heavy sudo-docker use; rig lanes must apply the known-normal list before filing
VRAM/ML findings; the seedbox is a shared host — its load is not a finding.

## Step 3 — skeptic verification, completeness critic, dedup

1. **Skeptic pass**: every `confidence: medium` finding (and any high-severity claim resting on a
   single observation) gets an independent adversarial verifier prompted to REFUTE it with fresh
   probes. Refuted → dropped (count them for the totals line); confirmed → `verification:
   "confirmed"` + `verify_note` (which may correct severity or mechanism).
2. **Completeness critic**: one agent reads the full finding set against the lane roster + chain
   matrix and asks what's missing — an unprobed leg, a lane that returned suspiciously little, a
   cross-lane pattern (same root cause seen from two hosts). It dispatches up to ~6 targeted
   `gap:<mission>` lanes. Iterate once more if the gap lanes surface something big.
3. **Dedup + known-issue folding** (reference §10 rules): same fact from two lanes merges (keep
   both auditors' evidence); open-task coverage → `known_issue: true`, no new task; regression of a
   done task → work item framed as regression; acked checks excluded.

## Step 4 — cluster into root-cause work items

Cluster all actionable findings (everything except pure-info) by **shared root cause / failure
class**, not by host or severity — an incident bundles its downstream cascade; hygiene batches into
catch-alls (the 2026-07-16 clustering, 303→26, is the exemplar). Assign waves (0 incident, 1
security, 2 broken user-facing pipelines, 3 service/infra repair, 4 hygiene/drift) and number
`fix-NN` sequentially in wave order starting at max+1. Mark disruptive clusters with the 4–7AM
gate. Every non-info finding lands in exactly one cluster.

## Step 5 — write the queue (repo writes happen here, and only here)

Produce the four artifacts + close-out exactly per reference §10 — dated findings MD + JSON twin
(severity-sorted, position-derived ids, sweep-letter prefix), worklist, tasks.json entries — then:
register the new doc in `.claude/commands/resolve-finding.md` (Step A ranges + Step B mapping),
update CLAUDE.md's current-priority pointer, append the sweep to progress.json `_meta.note`
(indent=1!), regenerate `gen-todo.py` + `gen-roadmap-pages.py`, `git pull`, ONE commit, then
`./foss-setup/scripts/docs/publish-deploy.sh`. Record the method (lane roster + agent/token counts
+ refuted count) in the findings doc's header blockquote so the next sweep can reproduce it.

## Step 6 — report

End your turn with: totals by severity; the top 5 findings in plain language (what's broken for
whom); anything on fire *right now* (critical section) flagged for immediate `/resolve-finding`;
chains verified healthy end to end; coverage gaps filed; what was deliberately not probed; and the
single command to start remediation: `/resolve-finding fix-NN` (lowest new item).

## Guardrails

- One sweep = one commit. Do not fix anything on any host, however trivial.
- Don't file anything on the known-normal list (reference §9) or under an ack.
- The tracker's checkmarks are untrustworthy — verify live before citing task state either way.
- A truncated log read (`docker logs --since` aborting on NUL) or a journal time-gap is evidence,
  not an inconvenience — file it (taxonomy #1, #15).
- If the sweep itself gets interrupted, the Workflow run is resumable; partial results are worth
  filing over losing them — a smaller honest doc beats a perfect lost one.
- Expect a full sweep to be expensive (the 07-16 exemplar: ~2.8M tokens, 1300+ probes). `quick`
  and `focus` exist for anything less than the full budget.
