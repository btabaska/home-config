---
description: Build the next books-cutover task (bmig-NN) end to end — Bookshelf + hardcover metadata migration, one task per session
argument-hint: "next" (auto-pick next open) | bmig-NN (e.g. bmig-03)
---

You are executing one task of the **books metadata cutover program** (Goodreads-mode
Readarr → Bookshelf + rreading-glasses:hardcover), requested as: **$ARGUMENTS**. Run it in
THIS session, end to end, against the definition of done below. Do NOT report it done until
every stage passes with evidence. If a stage cannot be completed or verified, say so
plainly — never claim done.

## Step A — pick the work item

- If **$ARGUMENTS** is empty or a word like `next` / `next item` / `next open`:
  **auto-select.** Read `foss-setup/docs/tasks.json` and `docs/progress.json`. Consider every
  task whose `id` is `bmig-NN`; drop any `id` present in `progress.json.done` (a dict keyed by
  id). Pick the **lowest-numbered remaining** one — bmig-01…06 are a strict dependency chain
  (parallel deploy → wire → migrate → patch → cut over → monitor), so lowest = next.
  State which item you picked before continuing. If a lower-numbered bmig task is NOT done
  but you were asked for a higher one, stop and say so — the chain must not be skipped.
- If it's a `bmig-NN`: use that task (after confirming its `depends_on` are all done).
- If ALL bmig tasks are done: say the program is complete and stop.

## Step B — load context (this is a cold session)

1. Read `CLAUDE.md` at the repo root — fleet access, secrets path, anti-drift ownership map,
   generation/deploy commands, standing mandates.
2. Read **`foss-setup/docs/books-metadata-cutover-2026-07-20.md`** in full — it is the
   program's source of truth: root-cause findings C1–C5 with evidence, the architecture
   target, the per-task implementation detail for YOUR task, the rollback plan, and the
   standing constraints. The owner decisions recorded there (full pivot; pre-approved to run
   outside the maintenance window; author-gate in scope) are settled — do not re-litigate.
3. From the chosen task in `tasks.json` read `summary`, `steps`, `verify`, `depends_on`.
4. Verify the **preconditions live**: each `depends_on` task's verify condition still holds
   on the fleet right now (a prior session's work may have drifted or another session may be
   mid-flight — `git pull` and re-check before building on it).
5. If discovery is read-heavy, delegate to an `Explore`/`general-purpose` subagent that
   returns only conclusions.

## Step C — align with me only where the plan leaves a genuine decision

The program doc already fixed the big decisions. Use `AskUserQuestion` ONLY for:
- **Secrets handoff** — bmig-01 needs me to create the Hardcover account/token and paste it
  (store at vault `books.hardcover_api_token`; merge, never blind-assign).
- **Live-state divergence** — if what you find on the fleet contradicts the plan doc
  (an image gone, a port taken, counts that don't match C5), present the delta and 2–3
  concrete options, recommended first.
- **Newly-discovered tradeoffs** with user-facing cost the doc didn't anticipate.

Do NOT ask permission-style "should I proceed?" questions, and do NOT re-ask what the doc
already answers. If nothing qualifies, proceed without questions.

## Definition of done

1. **Verify preconditions & current state.** Show live evidence the dependency chain holds
   and the task's starting assumptions are true (paste the commands/output that prove it).
2. **Plan, then act.** State the change set and blast radius. The parallel-run rule is the
   gate: **nothing may break the live readarr→CWA pipeline before bmig-05**; if your change
   could, stop and redesign. Destructive steps (bmig-05) follow archive-before-delete:
   create + verify the archive, then delete.
3. **Build.** Apply the task idempotently on the live host(s). Digest-pin any new image.
4. **Codify (anti-drift).** Land every live change in its owning repo file (compose /
   `.env.example` / stack mirror / script) per the CLAUDE.md ownership map, same session.
5. **Test end to end at the consumer.** Run the task's acceptance from the program doc —
   the poison corpus / parity counts / correct-or-loud request behavior — and paste the
   evidence. Container-up is not acceptance.
6. **Monitor.** If the task's plan-doc section names checks (liveness in bmig-01/02, the
   full migration in bmig-06): wire them into `foss-setup/verification/checks.d/`
   (`cmd`/`task_id`/`runbook` each), deploy to the mini runner (ssh sudo tee — scp fails
   silently), run and show green. Keep the coverage manifest current with every container
   added or removed (100%-coverage tripwire).
7. **Document.** Update wiki via the generation path (enrichment prose / runbooks — never
   hand-edit generated `services/*.md`), rebuild with `build-wiki.sh`, and note progress in
   the program doc (a one-line "done 2026-MM-DD + what shipped" under the task's section).
8. **Close the loop.** Mark the task done in `foss-setup/docs/progress.json` (one-line
   reason), regenerate (`gen-todo.py` + `gen-roadmap-pages.py`), **one commit** scoped to
   this task with before/after evidence in the message, then `publish-deploy.sh`. Confirm
   `git status` is clean of stray files first. Finally, tell me the single command to
   continue: `/build-next` (or that the program is complete after bmig-06).

## Guardrails

- One task = one commit. Log unrelated discoveries as tracker tasks; don't fix them here.
- `git pull` before committing; concurrent agent sessions happen.
- Never paste secret values into chat, commits, or docs — vault key paths only.
- NAS has no docker socket / no passwordless sudo: pipe vault `sudo.nas_password` into
  `sudo -S`; move files with `ssh nas 'cat > path'`, never scp.
- Respect the fix-38/I68 supply-chain posture: digest-pin, note the pin's provenance.
- End your turn with: what shipped (with evidence), acceptance + checks status, anything
  deliberately deferred, and the next command to run.
