# Verification framework — self-checks

What to do when a `verification-self` check fires (ntfy topic `verification`).

These checks exist because the 2026-07-16 audit (task **fix-30**) found the
**monitoring layer itself** silently broken in ways liveness could never catch:
the LLM auto-triage was 404ing behind a `/v1/models`-200 shim, the rig
backup-freshness signal fabricated a `STALE` alert after any reboot, and
committed checks called scripts that the documented `rsync --delete` deploy
would have **deleted**. Every check here probes the **consumer end**.

Source checks: `verification/checks.d/verification-self.yaml`. Findings closed:
H24, M19 (triage), M20, M39 (restic marker), M38, M53 (deploy drift).

> **Deploy rule:** always deploy the suite with
> `foss-setup/scripts/verification/deploy.sh` — **never** a raw
> `rsync -a --delete verification/ → /opt/verification/`. See *Deploy* at the
> bottom.

---

## `llm-triage-completion-e2e` failed (warn) — LLM auto-triage can't complete

The verify-04 triage layer (`llm-triage.sh` → `llm_triage.py`) diagnoses failed
checks with the local model. This probe does a **real** chat completion, not a
`/models` liveness ping — the ollama `:11434` shim answers `/models` 200 but
404s a big-model completion, which is exactly how the failure hid for days.

Output is `TRIAGE_LLM_FAIL:<reason>`:

- `http_404` / `http_5xx` — the resolved endpoint/model is wrong or down. The
  authoritative endpoint is **llama-swap `:9292` / `qwen3.6-35b-a3b`** (the
  script default). Check for a **stale override** in `/etc/verification/env`:
  ```bash
  ssh mini 'sudo grep -E "^LLM_(BASE_URL|MODEL)" /etc/verification/env'
  ```
  There should be **no** `LLM_*` lines (script default wins). If a line pins
  `:11434` / `qwen3-coder:30b`, delete it — that ollama shim only holds three
  small models (`nomic-embed-text`, `tag:fast`, `llama3.2:3b`). Confirm the live
  model list: `curl -s :9292/v1/models`.
- `empty_content` — the model returned 200 but no content. `qwen3.6` is a
  reasoning model; a small `max_tokens` is spent on `<think>` and leaves the
  answer empty. The probe uses the real triage budget (600). If this fires, the
  model is likely mis-served (thinking not closing) — check `llama-swap` on the
  rig.
- `curl_error` — the rig is unreachable. The rig is 24/7; treat as an incident
  (`llm-triage.sh` attempts WoL recovery). See *Recover the rig (WoL)*.

Re-probe by hand: `ssh mini /opt/verification/bin/llm-triage-probe.sh`.

## `restic-marker-writer-{rig,mini}` failed (warn) — backup can't leave a reboot-durable freshness signal

`restic-latest-age` (behind `restic-snapshot-fresh-{rig,mini}`) reads systemd's
per-boot `ExecMainExitTimestamp`, falling back to a persisted marker
`/var/lib/restic-mon/last-success`. The marker **must be written by
`restic-backup.service` itself** (an `ExecStartPost`) so it survives a reboot
between the nightly backup and the next sweep — otherwise a post-backup reboot
wipes the systemd record and the checker-only marker goes stale → a **false
`STALE`** while the backup actually succeeded (the M20/M39 bug).

This check asserts the `ExecStartPost` is present. If it fires, the unit was
redeployed without it. Restore from the repo:

```bash
# mirror foss-setup/scripts/backup/restic-backup.service to the host, then:
sudo install -m644 restic-backup.service /etc/systemd/system/ && sudo systemctl daemon-reload
systemctl cat restic-backup.service | grep restic-mon   # must show the touch line
```

## `verification-bin-refs-present` failed (warn) — a check references a script that isn't deployed

The suite is **not self-contained** under `verification/`: four scripts it runs
from `/opt/verification/bin` live canonically elsewhere in the repo and are
staged in at deploy time. This check greps the live `checks.d` for every
`/opt/verification/bin/<x>` reference and stats it. Output names the gap:
`MISSING_BIN_REF:/opt/verification/bin/<name>`.

Fix: **run the deploy script** — it assembles the complete tree (and would have
refused to deploy in the first place if a ref were missing):

```bash
foss-setup/scripts/verification/deploy.sh
```

If a **new** check adds a script under some other `scripts/<area>/` dir, add it
to the `EXTERNAL_BIN` list in `deploy.sh` so future deploys stage it too.

## `verification-env-source-clean` failed (crit) — a value in `/etc/verification/env` breaks sourcing (sec-12 class)

`/etc/verification/env` is **sourced** (`set -a; . env`) under `set -euo pipefail`
by `/opt/scripts/ntfy-notify.sh` (the `OnFailure=ntfy-notify@` wrapper) and by
`bin/llm-triage*.sh`. A value that is unquoted-with-a-space or wrapped across two
physical lines makes the shell execute part of it as a command (exit 127): the
wrapper dies before paging, so **every mini OnFailure page is silently dropped**,
and the raw value **leaks into journald**. That was sec-12 (finding SH3): line 40
was `HARDCOVER_API_TOKEN=Bearer <jwt>` and the space split it.

The check output is `ENV_SOURCE_DIRTY rc=<n>` (it never prints the file). Fix:

```bash
# find the offending line WITHOUT echoing secrets — flags any value that is
# unquoted-with-whitespace or a bare (no KEY=) continuation line:
ssh mini "sudo python3 - <<'PY'
import re
for i,l in enumerate(open('/etc/verification/env').read().split('\n'),1):
    if l=='' or l.lstrip().startswith('#'): continue
    m=re.match(r'^[A-Za-z_][A-Za-z0-9_]*=(.*)\$', l)
    if not m: print(i,'NOT_ASSIGN'); continue
    v=m.group(1)
    if v[:1] in ('\"',\"'\"):
        if not (len(v)>=2 and v.rstrip().endswith(v[0])): print(i,'UNBALANCED_QUOTE')
    elif ' ' in v or '\t' in v: print(i,'UNQUOTED_WHITESPACE')
PY"
```

Then **double-quote** the value onto one line (`KEY="Bearer eyJ..."`) via
`sudo` (the file is `640 root:btabaska` — back it up first). `checks_runner.py`
strips surrounding quotes when it parses, so quoting does not change the value
any consumer reads. Verify: `ssh mini 'sudo bash -c "set -a; . /etc/verification/env; set +a"'`
exits 0 and prints nothing. Never `cat` the env file to a shared/logged stream.

## `mini-onfailure-ntfy-delivers` failed (crit) — mini OnFailure paging does not reach ntfy

Proves the `OnFailure=ntfy-notify@` path end-to-end: it posts a nonce to the
`backups` topic with the wrapper's own `NTFY_URL`/`NTFY_TOKEN` (min priority, so
no phone push) and reads it back. `NTFY_PUBLISH_FAIL` = bad/missing token or the
ntfy vhost is down (see the *ntfy* service page); `NTFY_DELIVERY_FAIL` =
published but not retrievable (topic/ACL or cache issue). Because the wrapper
sources `/etc/verification/env`, a `verification-env-source-clean` failure will
also break real paging even if this publish/read self-test still passes — fix
that one first. Re-prove a real page after any fix:

```bash
ssh mini 'sudo systemctl reset-failed "ntfy-notify@*" 2>/dev/null; \
  sudo /opt/scripts/ntfy-notify.sh sec12-manual-test.service'   # must exit 0 and land on `backups`
```

---

## Scheduled-tier behaviour (quirks fixed in fix-30)

- **Quick tier honours `enabled`.** `verification-quick.service` runs with
  `--respect-enabled`, so a deliberately-disabled check is **never resurrected**
  by the scheduled `--host` runs (an ad-hoc operator `--host` run still includes
  disabled checks by design).
- **A crit failure doesn't fail the unit.** Both the quick and fast units carry
  `SuccessExitStatus=1`, so a crit check failing (runner exits 1) is treated as
  success — the tier still RAN, the dead-man ping still fires, and the unit is
  not left in `failed` state (which `systemd-failed-mini` would otherwise flag
  against the framework itself). A real crash/timeout exits 2+ and correctly
  fails the unit.
- **ntfy titles name the tier that ran** (`[fast tier]`, not `[None tier]`).

## Dead-man pings

Each scheduled tier pings a self-hosted Healthchecks monitor on success, and the
URL lives in `/etc/verification/env` (not hardcoded in the unit), so the repo
units install verbatim:

| unit | env var | Healthchecks monitor |
|---|---|---|
| `verification.service` (daily) | `VERIFY_DAILY_PING_URL` | `verification-mini` |
| `verification-quick.service` | `VERIFY_QUICK_PING_URL` | `verification-quick-mini` |
| `verification-fast.service` | `VERIFY_FAST_PING_URL` | `verification-fast-mini` |

All three values are in the vault (`healthchecks.verification_{,quick_,fast_}mini_ping_url`).

## Deploy

```bash
foss-setup/scripts/verification/deploy.sh          # idempotent; safe to re-run
```

It stages `verification/` **plus** the four external scripts, strips `._*` /
`__pycache__` junk, **refuses to deploy** if any referenced bin script is
missing, normalizes modes so the root-owned tree stays readable by the
`btabaska` runner, (re)installs the daily/quick/fast units + timers, and retires
the old etckeeper-only daily-ping drop-in. A raw `rsync --delete` would delete
the four external scripts — don't.
