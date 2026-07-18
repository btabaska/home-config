# Continuous Verification (verify-01..05)

Daily automated checks of the homelab, with local-LLM triage of failures and
reopen suggestions for the task tracker. Runs on **mini** (always-on), deployed
to `/opt/verification`, state in `/var/lib/verification`.

## How it works

```
verification.timer (daily 07:15)
  └─ verification.service (oneshot, User=btabaska)
       └─ bin/verify-cycle.sh
            ├─ bin/run-checks.sh  → bin/checks_runner.py   (verify-01/02/05)
            │    • loads checks.d/*.yaml (PyYAML 5.4.1, stock on mini)
            │    • runs enabled checks: local/url/mini = on mini,
            │      nas = ssh nas (dedicated mini→nas key). rig checks are
            │      HTTP probes (host: url) by design — they test the endpoints
            │      clients hit; mini→rig SSH works, the container→host hop is
            │      watched rig-locally (ai-stack-watchdog). Only mini→seedbox
            │      SSH is ACL-blocked (that check stays disabled).
            │    • writes results.json, last-summary.md, reopen-suggestions.json
            │    • ONE ntfy summary to topic `verification` ONLY when failures
            │      exist or a previous failure recovered (diff vs prior results.json)
            │    • exit 1 if any crit check failed
            └─ bin/llm-triage.sh → bin/llm_triage.py        (verify-03/04)
                 • only when failures exist
                 • rig is 24/7 — LLM endpoint down means the rig is down (an
                   incident); recovery: WoL (50:eb:f6:b5:82:c6), wait ≤90s,
                   else records "rig unavailable" and exits 0
                 • ONE FRESH single-turn completion per failed check, using the
                   matching skills/*.md prompt; appends verdicts to
                   triage-<date>.md; malformed JSON → 1 retry → escalate:true
```

Manual runs:

```bash
sudo systemctl start verification.service      # full cycle
/opt/verification/bin/run-checks.sh            # checks only
/opt/verification/bin/run-checks.sh --json     # machine-readable
/opt/verification/bin/run-checks.sh --host rig # rig-only run (rig checks are
                                               # enabled in the daily cycle — rig is 24/7)
/opt/verification/bin/llm-triage.sh            # triage last results.json
```

`--host X` matches a check's `host` field **or its domain (file stem)**, and
also includes that host/domain's `enabled: false` checks (e.g. the seedbox
check). Filtered runs are ad-hoc/operator-driven: they write
`results-<host>.json` and never touch the daily state
(`results.json`, `reopen-suggestions.json`, `last-summary.md`) or send ntfy.

## Adding a check

Append to the matching `checks.d/<domain>.yaml` (or add a new file — the domain
maps to a triage skill in `bin/llm_triage.py:DOMAIN_SKILL`):

```yaml
  - id: mini-newthing            # unique, stable
    name: "newthing answers on :1234"
    host: mini                   # local | mini | nas | rig | url
    cmd: curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:1234/
    expect: '^200$'              # regex on stdout — OR use expect_exit: 0
    severity: warn               # crit (fails the run) | warn | info
    task_id: docker-14           # tracker task this check guards
    runbook: wiki/runbooks/docker.md   # may not exist yet
    enabled: true
```

Rules of thumb: **run the probe by hand first** and encode the code/output you
actually saw (many healthy apps answer 302/303/307/401, not 200). Then deploy:
rsync this dir to `mini:/opt/verification` (see Deploy below).

## LLM endpoint + model

- Default: **ollama on the rig**, `http://cachyos.tailb31641.ts.net:11434/v1`
  (OpenAI-compatible, no auth). litellm on `:4000` also answers but requires an
  API key (`401` without) — set `LLM_BASE_URL` + `LLM_API_KEY` in
  `/etc/verification/env` to use it instead.
- Model: `qwen3-coder:30b` (already pulled, ~18 GB).

### Model sizing on the 3090 Ti (24 GB VRAM)

| model | VRAM | notes |
|---|---|---|
| qwen2.5-coder:32b-q4 | ~19 GB | tight — little headroom for KV cache/long outputs |
| qwen3-coder:30b / 14b-class | ~14–18 GB | comfortable, best quality/speed balance for triage |
| llama3.1:8b / llama3.2:3b | ~2–5 GB | fast; fine for these small structured prompts |

### Fresh-context-per-check design

Each failed check gets its **own single-turn completion** — no shared
conversation. Rationale: (1) 8–32B models degrade fast with long mixed
contexts; one check + one scoped skill prompt keeps them accurate; (2) no
cross-contamination — a DNS failure can't bias the diagnosis of a backup
failure; (3) verdicts are independently retryable and cacheable; (4) prompt
size stays bounded regardless of how many checks fail. The skills in
`skills/*.md` are written self-contained (environment facts + one few-shot
example + strict JSON contract) for exactly this reason.

## Reopen-suggestions flow (verify-05)

Every run writes `/var/lib/verification/reopen-suggestions.json`:

```json
{"generated": "...", "task_ids": ["dns-02", "nas-08"],
 "failed_checks": [{"id": "...", "task_id": "...", "severity": "..."}]}
```

The **AI session-start protocol** consumes this file: at the start of a session
it reads the list and proposes reopening those tasks in
`foss-setup/docs/progress.json`. The runner itself **never commits to git by
design** — reopening a task is a judgment call (flaky check vs. real
regression) that stays with the human/AI session.

## Deploy

**Always deploy with the script — never a raw `rsync --delete`.**

```bash
foss-setup/scripts/verification/deploy.sh          # idempotent; re-run any time
```

The suite is **not self-contained** under `verification/`: four scripts it runs
from `/opt/verification/bin` live canonically elsewhere in the repo
(`scripts/gaming/mc-{status,bedrock}-ping.py`, `scripts/ai/wiki-rag-sync.py`,
`scripts/media/window-maint-unpackerr-rclone.sh`). A naïve
`rsync -a --delete foss-setup/verification/ → /opt/verification/` **deletes all
four** (they aren't under `verification/`), silently breaking two checks and a
service — this was quality-gate finding M38/M53. `deploy.sh`:

- assembles a **complete** staging tree (`verification/` + those four scripts),
  so `--delete` is safe, and strips macOS `._*` / `__pycache__` / `*.pyc` junk;
- **refuses to deploy** if any `/opt/verification/bin/<x>` a check or unit
  references is missing from the tree (the standing guard, mirrored by the
  `verification-bin-refs-present` check);
- normalizes modes so the root-owned tree stays readable by the `btabaska`
  runner (a `600` source file + `chown root:root` once broke the coverage
  checks), (re)installs the daily/quick/fast systemd units + timers, and retires
  the old etckeeper-only `verification.service.d/healthchecks.conf` drop-in (the
  daily dead-man ping now lives in the base unit via `${VERIFY_DAILY_PING_URL}`).

```bash
# once, on mini: create /etc/verification/env from systemd/env.example, filling
# values from the vault (NTFY_TOKEN, VERIFY_{FAST,QUICK,DAILY}_PING_URL, PLEX/
# LIDARR keys, …). LLM_BASE_URL/LLM_MODEL stay UNSET so the script default
# (llama-swap :9292 / qwen3.6-35b-a3b) wins — a stale override 404s all triage.
#   docker exec ntfy ntfy token add --label verification admin
```

## Known state (2026-07-07)

- `dns-nas-*` FAIL (secondary resolver down) — guards reopened **dns-02**. Desired.
- `backup-immich-dump-fresh` FAIL (last dump 2026-07-02) — guards reopened **nas-08**. Desired.
- `git-*` may FAIL on drift (etckeeper dirty, 1 file in /opt/stacks) — real drift to review.
- seedbox: SSH blocked by ACL → its check is `enabled: false`.
- rig: runs 24/7 (decision 2026-07-08) — rig checks are **enabled** in the daily
  cycle; the rig being down / 502 is now an **incident**, with WoL retained as
  the recovery tool (llm-triage.sh self-heal). HTTP-only probes for now
  (mini→rig SSH historically denied by tailnet ACL; being re-verified).

## Human approval gate (policy — added 2026-07-08 at the operator's request)

Verification is **read-only by design**, at every layer:

1. Probes only observe (curl/dig/systemctl show/git status). They never restart, edit, or delete anything.
2. The local-LLM triage layer only *diagnoses*: its output is a JSON verdict with `suggested_fix_commands` — **suggestions are never executed by the runner, a timer, or any automation.**
3. Remediation happens exclusively through an interactive AI session (Claude), and anything that would change system state requires **explicit operator approval first**, presented as: *what is broken (evidence) -> what the fix will do -> what could go wrong*. Reply-to-approve in chat.

If any future change to this framework would let a model execute commands autonomously, that change itself requires operator approval and a note here.
