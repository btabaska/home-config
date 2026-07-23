---
description: Build the next ready homelab task end to end — auto-picks the next agent-completable open item (or a named id), one task per session
argument-hint: "next" (auto-pick next ready) | a task id (e.g. media-05, read-15, ha-04)
---

You are executing one homelab task from the roadmap, requested as: **$ARGUMENTS**. Run it in
THIS session, end to end, against the definition of done below. Do NOT report it done until
every stage passes with evidence. If a stage cannot be completed or verified, say so
plainly — never claim done.

The task list is heterogeneous (12 tracks, many hosts). Each task in `tasks.json` is
self-describing — you drive off its own fields, not a single program doc. The bmig
books-cutover chain this skill was born for is complete; `/build-next` now covers **all**
remaining roadmap work.

## Step A — pick the work item

Read `foss-setup/docs/tasks.json` (a list) and `foss-setup/docs/progress.json`. "Open" =
`id` not present in `progress.json.done` / `retired` / `deferred` (each a dict keyed by id).

- If **$ARGUMENTS** is a task **id** (e.g. `media-05`, `read-15`, `ha-04`): use that task.
  Confirm its `depends_on` are all done and its `gate` (if any) is satisfied before building;
  if not, stop and say what's missing.
- If **$ARGUMENTS** is empty or `next` / `next open` / `next ready`: **auto-select** the next
  **agent-completable, unblocked** task:
  - Keep only open tasks whose every `depends_on` is done, whose `gate` (if present) is
    already satisfiable now, and whose timing constraint (some gates read like
    "not before 2026-MM-DD") has passed.
  - Prefer tasks fully completable by an agent in-session: `mode` of **`ai`** or **`ai-vault`**
    (the latter needs one vault-secret handoff from me — see Step C). **Skip `mode: mixed`**
    (has physical/human steps — thermostat installs, VLAN moves, OAuth device pairing) **and
    `mode: human`** in auto-select; they can't be finished end to end here.
  - Order the survivors by `run` (wave, ascending), then `required: true` first, then `id`.
    Pick the first. State which item you picked **and why**, and list what you skipped and the
    reason (blocked dep, unmet gate, mixed/human mode) so the choice is auditable.
  - If nothing is agent-completable right now, say so and name the top blocked items + what
    would unblock each — don't force a `mixed`/`human` task.
- If **$ARGUMENTS** is a `fix-NN` id: that's a quality-gate item — hand off to
  **`/resolve-finding fix-NN`** (it loads the audit evidence); don't run it here.

## Step B — load context (this is a cold session)

1. Read `CLAUDE.md` at the repo root — fleet access, secrets path, anti-drift file-ownership
   map, generation/deploy commands, standing mandates. Everything to act safely is there.
2. From the chosen task read **all** its self-describing fields: `summary`/`detail`, `steps`,
   `commands`, `files`, `verify`, `depends_on`, `gate`, `pitfalls`, `hardware`, `host`,
   `type`, `mode`, `docs`, `source`. These are your spec.
3. If the task names an in-repo design/finding doc in `source` or a local path in `docs`,
   read it in full — that's the task's source of truth (root causes, target architecture,
   rollback). External `docs` URLs are reference; fetch only if you need them.
4. Verify **preconditions live**: each `depends_on` task's `verify` condition still holds on
   the fleet right now, and the task's own starting assumptions are true. A prior session may
   have drifted or another may be mid-flight — `git pull` and re-check before building on it.
5. If discovery is read-heavy (many files/hosts), delegate to an `Explore` /
   `general-purpose` subagent that returns only conclusions, to keep this session lean.

## Step C — align with me only where the task leaves a genuine decision

Use the `AskUserQuestion` tool ONLY for:
- **Vault-secret / gate handoff** — `ai-vault` tasks and gates that need creds I hold (API
  token, account login, device cred). Ask me to provide it; store at the vault key the task
  implies and **merge, never blind-assign** the vault section.
- **Live-state divergence** — if what you find on the fleet contradicts the task's assumptions
  (image gone, port taken, counts that don't match), present the delta and 2–3 concrete
  options, recommended first.
- **User-facing tradeoffs / timing** — where the fix has a cost I should weigh, or disruptive
  work needs scheduling (the 4–7AM window per mandate 4).
- **Mixed-mode partial** — if I explicitly asked for a `mixed` task, confirm which physical/
  human steps I'll do so you can scope the software half and hand off the rest cleanly.

Do NOT ask permission-style "should I proceed?" questions, and do NOT re-ask what the task
spec already answers. If nothing qualifies, proceed without questions.

## Definition of done

1. **Verify preconditions & current state.** Show live evidence the dependency chain holds and
   the task's starting assumptions are true (paste the commands/output that prove it).
2. **Plan, then act.** State the change set and blast radius. If the change is
   disruptive/destructive or user-facing, confirm first and schedule disruptive work for the
   4–7AM window (mandate 4). Destructive steps follow archive-before-delete: create + verify
   the archive, then delete.
3. **Build.** Apply the task's `steps`/`commands` idempotently on the live host(s). Digest-pin
   any new image (fix-38/I68 supply-chain posture; note the pin's provenance).
4. **Codify (anti-drift).** Land every live change in its owning repo file (compose /
   `.env.example` / stack mirror / ansible / config / script) per the CLAUDE.md ownership map,
   **same session**. A host-only change is not done — the next redeploy reverts it.
5. **Test end to end at the consumer.** Run the task's `verify` acceptance and paste the
   evidence. Probe the *consumer* end, not liveness — "container up / 200 OK" is not
   acceptance (mandate 1).
6. **Monitor.** If the task warrants a check (new/changed service, a recurring failure), wire
   it into `foss-setup/verification/checks.d/` (`cmd`/`task_id`/`runbook` each), deploy to the
   mini runner (`ssh sudo tee` — scp fails silently), run and show green. Keep the coverage
   manifest current with every container added or removed (100%-coverage tripwire, mandate 2).
7. **Document.** Update the wiki via the generation path (enrichment prose in
   `configs/docker-stack/service-enrichment.yaml` or the right `wiki/docs/` page — never
   hand-edit generated `services/*.md`), rebuild with `build-wiki.sh --strict`.
8. **Close the loop.** Mark the task done in `foss-setup/docs/progress.json` (one-line
   reason), regenerate (`gen-todo.py` + `gen-roadmap-pages.py`), make **one** commit scoped to
   this task with before/after evidence in the message, then run `publish-deploy.sh`. Confirm
   `git status` is clean of stray/iCloud-conflict files first. Finally, tell me the single
   command to continue: `/build-next`.

## Homepage widget/service sub-recipe (home-05…08 + any task that adds a Homepage tile)

The Homepage build-out flow (`home-05`…`home-08`, plus every new-service task that ends in
"+ Homepage widget") shares one recipe on top of the definition of done. Follow it so each tile
is landed consistently and anti-drift holds:

1. **Verify the widget exists + its exact fields first.** Homepage widgets are versioned —
   check `https://gethomepage.dev/widgets/services/<type>/` (or `/info/<type>/`) before wiring.
   Do NOT invent a `widget.type`. Known no-widget services (keep as `siteMonitor`): whisparr,
   pinchflat, metube, wallabag, open-webui, comfyui, flaresolverr, dockge.
2. **Live is the mini's `/opt/stacks/homepage/config/`; the repo mirror is
   `configs/docker-stack/stacks/homepage/config/`.** Edit both the same session — a live-only
   tile reverts on the next redeploy. Secrets go in the stack `.env` as `HOMEPAGE_VAR_*` and in
   `.handoff-secrets.yaml` (MERGE the section — never blind-assign; safe_dump strips comments).
   `.env.example` gets the key name only, never the value.
3. **Widget URLs hit upstream directly** (container name for mini services, IP for NAS/seedbox,
   the Caddy hostname only for cross-host like Beszel); `href` uses `https://<name>.tabaska.us`.
   Mind version flags: Mealie `version: 2` (v3), Beszel `version: 2` (≥0.9.0), Immich `version: 2`.
4. **Test at the consumer, not liveness (mandate 1).** Acceptance = the tile renders *live data*
   (counts/streams/status), not "container up" and not "API Error"/blank. Paste what you saw.
5. **A new service (not just a widget) still owes the full runbook** — Caddy vhost, service
   catalog, `checks.d/` consumer probe, `verification/coverage/<host>.containers`, wiki
   enrichment — per `wiki/docs/runbooks/add-a-service.md`. A pure widget-wiring task
   (home-05…08) adds no container, so no coverage change; a Homepage-widget liveness probe in
   `checks.d/` is optional but preferred for the higher-value tiles.
6. **User-facing note:** adding tiles changes the household dashboard. It's non-destructive, but
   confirm timing per mandate 4 if the change is visible mid-day; `home-05` adds no new secret
   so it's the safe first pick.

## Guardrails

- One task = one commit. Log unrelated discoveries as new tracker tasks; don't fix them here.
- `git pull` before committing; concurrent agent sessions happen — expect intentional
  `/opt/stacks` drift and re-read before Edit.
- Never paste secret values into chat, commits, or docs — vault key paths only.
- NAS has no docker socket / no passwordless sudo: pipe vault `sudo.nas_password` into
  `sudo -S`; move files with `ssh nas 'cat > path'`, never scp. rig sudo at
  `sudo.rig_password`; HA is REST/WS-only (token at `hosts.ha.api_token`).
- `mixed`/`human` steps you can't perform (physical installs, on-device pairing, OAuth clicks):
  do every software part you can, then hand off the rest explicitly — never claim end-to-end
  done for work a human still has to do.
- End your turn with: what shipped (with evidence), acceptance + checks status, anything
  deliberately deferred or handed off, and the next command to run (`/build-next`).
