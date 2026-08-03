# journal-reflection-reconcile (mini host units) — fix-67 / SM37

Doc-only mirror of two mini host units that are **not** ansible-managed (the mini
`site.yml` roles are base/docker/tailscale/backup/state only — see the
"mini host units not ansible-managed" memory). Keep this in sync by hand.

## What it fixes

The n8n `journal-analyze` workflow only analyzes `memos.memo.created` events. A
`#journal` tag **added by editing** a memo after creation arrives as
`memos.memo.updated`, which the Guard node drops by design — so that entry is
silently never analyzed. Memo 36 (2026-07-23) was lost this way (fleet-sweep
finding SM37). Handling `memos.memo.updated` in the workflow would risk
duplicate reflections on every later edit, so the safety net is a periodic
**reconciler** instead: it finds every top-level `#journal` memo with no 🧭
Reflection comment and re-injects a `created`-shaped event into the journal
webhook. Idempotent (a reflected memo is skipped), so it also self-heals any
missed webhook, and best-effort (posts nothing when the coach model is evicted;
retried next run).

## Files

| unit | canonical source |
|------|------------------|
| `journal-reflection-reconcile.service` | this dir → `/etc/systemd/system/` |
| `journal-reflection-reconcile.timer`   | this dir → `/etc/systemd/system/` |
| reconciler script | `foss-setup/configs/docker-stack/stacks/journaling/scripts/reconcile-reflections.py` → `/opt/stacks/journaling/scripts/` |

## Install / re-apply (idempotent)

```sh
# script ships with the journaling stack; ensure it's present + executable
sudo install -m 0755 reconcile-reflections.py /opt/stacks/journaling/scripts/
# units
sudo cp journal-reflection-reconcile.service journal-reflection-reconcile.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now journal-reflection-reconcile.timer
# one-off run
sudo systemctl start journal-reflection-reconcile.service
journalctl -u journal-reflection-reconcile.service --no-pager | tail
```

## Monitoring

Consumer-end check `journaling-reflection-backlog` (checks.d/journaling.yaml,
helper `verification/bin/journaling-reflection-backlog.py`, tier daily): counts
`#journal` memos older than 24h with **zero** reflection comments — expects 0.
The 24h grace lets the nightly free-GPU window + hourly reconciler clear the
backlog, so it does not false-positive during day-time GPU contention.
