# Master prompt — advance the handoff queue (paste into a fresh session)

You are automating the "Going Analogue" homelab quality/reliability workstream. Do **one** queue item this session, then stop.

## Steps
1. **Orient.** Read `foss-setup/docs/quality-hardening-state.md` (especially the **Operational cheatsheet**) and `foss-setup/docs/prompts/HANDOFF-QUEUE.md`. The `MEMORY.md` notes auto-load; verify any named file/flag still exists before acting.
2. **Pick the next item.** In queue order, find the first item that is unchecked `[ ]` (or `[~]` partial) **and** whose `deps` are all `[x]`.
   - If that item is marked **`needs-user`** or **`collaborative`** (or it's the deferred #18 / backlog #19): **STOP.** Do the autonomous prep the item allows (e.g. a decision list, an exact UniFi click-list), then report to the user exactly what you need from them. Do not attempt the human steps yourself.
   - If no item is eligible (all remaining are needs-user/blocked): STOP and report that the autonomous queue is drained + what's waiting on the user.
3. **Execute** the item's prompt file end-to-end with the mandated loop — no shortcuts:
   **diagnose** (re-probe live; do NOT trust stale state in the docs) → **fix repo-first** → **validate the real end-to-end outcome** (the user-visible result, not container liveness) → **write a negative-tested regression check** (it must FAIL when the outcome is actually broken, PASS when fixed) → **deploy** to the live host → **commit** to `origin` + `./foss-setup/scripts/docs/publish-deploy.sh` to forgejo.
4. **Record & stop.**
   - Check the item off `[x]` in `HANDOFF-QUEUE.md` (or `[~]` with a note if partial/blocked).
   - Update the task board in `quality-hardening-state.md` and append one line to the queue's completion log (what changed + commit hash).
   - Write any durable gotcha to memory (`MEMORY.md` + a note file).
   - Commit those doc updates.
   - Report: what you did, proof it works, the regression check + its negative test, and what the next queue item is.

## Rules
- **One item per session.** Do not skip ahead or batch. (Re-running this master prompt advances the next item — that's the automation loop.)
- Secrets come only from `foss-setup/.handoff-secrets.yaml`; **never** write a secret value into a committed file, doc, or wiki.
- Reversible, verified changes are fine to make directly. For anything destructive, one-way, or that reboots/repairs a host, confirm with the user first.
- If you can't finish an item, leave it `[~]`, write the blocker into the queue item, commit, and report — don't mark it done.
- Live state is source of truth; treat prior "done"/green as liveness, not correctness.
