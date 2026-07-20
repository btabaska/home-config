---
description: Resolve one quality-gate work item (fix-NN) end to end — align, resolve, codify, harden, test, monitor, document
argument-hint: "next" (auto-pick next open) | fix-NN (e.g. fix-20) | a raw finding id like H7
---

You are resolving a quality-gate remediation item from the 2026-07-16 audit, requested as:
**$ARGUMENTS**. Run it in THIS session, end to end, against the definition of done below. Do NOT
report it resolved until every stage passes with evidence. If a stage cannot be completed or
verified, say so plainly — never claim done.

## Step A — pick the work item

- If **$ARGUMENTS** is empty or a word like `next` / `next item` / `next open`: **auto-select.**
  Read `foss-setup/docs/tasks.json` and `docs/progress.json`. Consider every task whose `id` is
  `fix-NN` with `NN ≥ 20`; drop any `id` present in `progress.json.done` (a dict keyed by id). Pick
  the **lowest-numbered remaining** one — the ids are numbered in wave order (fix-20 incident →
  fix-21-24 security → fix-25-29 pipelines → fix-30-38 infra → fix-39-45 hygiene → fix-46-48
  books-stack scan), so lowest = next.
  State which item you picked and why before continuing.
- If it's a `fix-NN`: use that task.
- If it's a raw finding id (e.g. `H7`): use the `fix-NN` task whose `findings` array contains it.

## Step B — load context (this is a cold session)

1. Read `CLAUDE.md` at the repo root — fleet access, the secrets path, the anti-drift
   file-ownership map, the generation/deploy commands, and the standing mandates. Everything you
   need to act safely is there or linked from there.
2. From the chosen task read `summary`, `findings`, `verify`, and any `gate`.
3. Read every listed finding's full entry (severity, detail, **evidence**) in the doc named by
   the task's `source` field — quality-gate items (H/M/L/I findings) live in
   `foss-setup/docs/quality-gate-2026-07-16.md`; books-stack items fix-46–48 (B findings) live in
   `foss-setup/docs/books-stack-scan-2026-07-20.md`. The evidence block has the exact commands
   that reproduced each issue — start from those.
4. If root-cause discovery will be read-heavy (many files/hosts), delegate it to an `Explore` or
   `general-purpose` subagent and have it return only the conclusion, to keep this session lean.

## Step C — align with me BEFORE doing any work

Do a quick live reproduce first (enough to know the real state), then **use the `AskUserQuestion`
tool to ask me 1–3 human-centered questions** so the resolution matches what I actually want. This
is the first interactive thing you do — don't design the fix until I've answered.

Ask about outcomes and expectations, not implementation trivia. Good dimensions:
- **Desired end state** — fix it / remove-retire it / accept-and-document it? (e.g. is Immich's empty
  library a bug to fix or was photo backup never intended; should CWA store-passthrough be on or off).
- **Scope** — just this cluster, or also the adjacent thing you'd inevitably touch?
- **Timing / risk tolerance** — safe to do now, or hold disruptive parts for the 4–7AM window?
- **Preservation** — anything that must not be deleted/changed (data, a working-around config)?
- **Tradeoffs** — where a fix has a user-facing cost, which way do I lean?

Make each question a real decision with concrete options; put your recommended option first and label
it. Skip a question if the answer is genuinely obvious from the finding. Do NOT ask permission-style
"should I proceed?" questions here — those belong to the approval gate in stage 2. Fold my answers
into the plan.

## Definition of done

1. **Reproduce & root-cause.** Confirm each finding still holds; find the actual cause, not the
   symptom; paste the evidence. (Some may already be fixed — say so, still close them in stage 8.)
2. **Plan, then gate.** Show the fix (shaped by my Step-C answers), blast radius, and whether it's
   disruptive/destructive. If the task `gate` is set or the change is disruptive/user-facing, **stop
   for my approval** and schedule disruptive work for the 4–7AM window. Otherwise proceed.
3. **Resolve.** Apply the fix idempotently on the live host(s).
4. **Codify (anti-drift).** Land the same change in the repo file that owns this service (CLAUDE.md
   ownership map) — compose/`.env`/ansible/config. A host-only fix is not done; the next redeploy
   reverts it.
5. **Harden.** Remove the root cause's ability to recur (guard, constraint, validation,
   least-privilege, retry/alert). State what would now stop it.
6. **Test + monitor.** Add BOTH: (a) a regression check for this exact bug, and (b) a class-level
   check that catches siblings. Wire into `foss-setup/verification/checks.d/` (each needs
   `cmd`/`task_id`/`runbook`), update the coverage manifest, attach a real monitor (healthchecks
   dead-man / uptime-kuma) with an ntfy route. **The check must probe the consumer end to end** —
   liveness is what missed all of these. Deploy it and show it green.
7. **Document.** Write it up in the wiki via the generation path (service prose in
   `configs/docker-stack/service-enrichment.yaml`, or the right `wiki/docs/` page — never hand-edit
   generated `services/*.md`), then rebuild. Cross-link from the quality-gate doc.
8. **Close the loop.** Mark the task done in `foss-setup/docs/progress.json` (one-line reason),
   regenerate (`gen-todo.py` + `gen-roadmap-pages.py`), prepare **one** commit scoped to this task
   with before/after evidence in the message, then run `publish-deploy.sh`. Verify `git status` is
   clean of stray/iCloud-conflict files first.

## Guardrails

- One work item = one commit/PR. Don't fix unrelated things you notice — log them instead.
- `git pull` before committing; another session may be working in parallel.
- Never paste secret values into chat, commits, or docs.
- End your turn with: which findings are now resolved (with evidence), what the new check is and
  that it's green, and anything you deliberately deferred.
