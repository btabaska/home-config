# Home / homelab — operating context

This repo (`~/GitHub/Home`, the "Going Analogue" FOSS homelab) drives a 5-host fleet.
The main content is under `foss-setup/`. This file is auto-loaded every session — read it
before touching anything. The rule that matters most: **a fix that changes a live host but
not the repo (or vice-versa) creates drift.** Every change lands in both.

## Fleet access (SSH aliases in `~/.ssh/config`)

| alias | host | notes |
|-------|------|-------|
| `mini` / `server` | Ubuntu Mac mini `192.168.10.2` | Docker host, 38 containers in `/opt/stacks`. **Passwordless sudo + docker.** |
| `nas` | Synology DS920+ `192.168.10.4` | *arr stack + Plex + Immich + CWA. **No docker socket, no passwordless sudo.** sudo needs the vault password piped: `printf '%s\n' "$PW" \| ssh nas 'sudo -S …'`. **SFTP/scp disabled** → move files with `ssh nas 'cat > /path'`. Never add raw cron lines (DSM rewrites `/etc/crontab`) — use `.task` files in `/usr/syno/etc/synoschedule.d/root/`. |
| `rig` | CachyOS `192.168.10.12` | AI stack + game servers. 24/7 (suspend masked). sudo password at vault `sudo.rig_password`. |
| `seedbox` | Bytesized "betty" | Deluge only download client; no root; home `/home/hd34/btabaska`. |
| `ha` | Home Assistant `192.168.10.50:8123` | **LAN-only, NOT on the tailnet, SSH port refused** — drive via REST/WS API only (token at vault `hosts.ha.api_token`). |

## Secrets

`foss-setup/.handoff-secrets.yaml` — **gitignored, chmod 600** (so `git ls-files` won't show it;
reference it by path). Read with `python3` + `yaml`, reference by key path, **never paste values
into chat, commits, or docs.** Template: `.handoff-secrets.yaml.example`.

## Anti-drift: which files own which service

- **mini stacks** live in `/opt/stacks/<app>/` (its own git repo → Forgejo `home/docker-stacks`).
  Changing one means: edit live **and** mirror changed files back to
  `foss-setup/configs/docker-stack/stacks/<app>/`, commit+push both.
- **NAS compose** lives in `/volume1/docker/<app>/`; repo mirror under `foss-setup/configs/nas/`.
- **rig** units/config under `foss-setup/configs/host/rig/`; ansible-pull runs on rig too.
- After committing repo changes, **always run `foss-setup/scripts/docs/publish-deploy.sh`**
  (pushes `main` to both `origin` GitHub + `forgejo` mini:2222). On mini, push to forgejo as
  `btabaska`, not root (root lacks the ssh alias).
- Concurrent agent sessions happen: `git pull` before committing, re-read before Edit, expect
  intentional `/opt/stacks` drift from another session.

## Tracker & wiki are generated — never hand-edit outputs

- Source of truth: `foss-setup/docs/tasks.json` + `docs/progress.json` (`done` is a dict keyed by
  task id). After editing them, regenerate: `python3 scripts/docs/gen-todo.py` (writes root
  `todo.md`) and `scripts/docs/gen-roadmap-pages.py`. Tracker checkmarks are **not trustworthy** —
  verify live state.
- Wiki: prose for service pages lives in `configs/docker-stack/service-enrichment.yaml` (merged by
  `gen-wiki-services.py`) — **never hand-edit generated `wiki/docs/services/*.md`**. Deploy with
  `scripts/docs/build-wiki.sh` (dockerized mkdocs on the mini, `--strict`).
- Verification: runner on mini `/opt/verification` (`bin/run-checks.sh`); checks in repo
  `foss-setup/verification/checks.d/*.yaml` (each needs `cmd`, `task_id`, `runbook`). Deploy =
  `scp` the yaml to `/opt/verification/checks.d/`. Alerts go to ntfy topic `verification`.

## Standing mandates

1. **Verify end-to-end, not liveness.** "Container up / 200 OK" is not "the feature works." The
   2026-07-16 audit found 30+ services green-but-broken. New checks must probe the *consumer* end.
2. **100% monitoring coverage tripwire** — update the coverage manifest (`verification/coverage/`)
   with **every** service deploy or retire.
3. **Live stack is the source of truth for docs** — document what's running, not what was planned.
4. **Disruptive work → 4–7AM EST window.** Confirm before destructive or user-facing actions.

## Current priority: fleet-sweep remediation — COMPLETE (2026-08-02/03)

The `/fleet-sweep` 2026-08-02 audit (**`foss-setup/docs/fleet-sweep-2026-08-02.md`**, 318 findings;
**`docs/fleet-sweep-2026-08-02-worklist.md`**, 21 clusters = `fix-49`…`fix-69`) has been **fully
remediated** in an orchestrated drive (one subagent per item; operator waived the 4-7AM window):
all 22 items — `fix-49`…`fix-69` + escalated `sec-12` (SH3) — are resolved and closed in
`progress.json` (commits `667e361`…`25567cf`). Final audit-safe run: **343/362 checks pass, 0 crit
failures** (baseline was 29 fails). The 20 regressed prior-closures are re-fixed and tracked via the
new `progress.json.reopened` ledger (fix-68). Remaining warn-level residuals are expected/deferred,
NOT regressions: `edge-plex-version-current` (NAS Plex one build behind → user update, ties to
`fix-24`), `immich-user-zero-assets` (Kaelyn must enable backup on her own device),
`sys-docker-subnet-squat` (two more docker squatters → open task `ha-19`), the deferred
`git-etckeeper-clean`, plus self-healing `/opt/foss-setup` mini/rig clone drift (clears on the next
ansible-pull) and one Kuma monitor to eyeball on `/status/fleet`. **Open human follow-ups:** schedule
the pending mini kernel reboot (4-7AM), set Windows `RealTimeIsUniversal` on rig, subscribe a phone
to the off-mini dead-man + `alert-drill` ntfy topics, and (optional) provide a subsource/OpenSubtitles
key to broaden Bazarr coverage. Next work is the pre-existing open queue (`ha-19`, `fix-24`,
`game-*`, `media-09/10/13`, etc.) via **`/build-next`** or **`/resolve-finding`**.
