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

## Current priority: local-AI ("local Claude") buildout — COMPLETE (2026-08-06)

The researched local-Claude AI stack shipped as tracker ledger `lai-01`…`lai-20` (orchestrated drive,
one subagent per item). **19 done; `lai-15` DEFERRED** (StrategyWiki sits behind Cloudflare
bot-management that fingerprints/403s mwoffliner — self-completing scaffolding + blocked-mode check
shipped; real path = file the openZIM zim-request). Close-out doc:
**`foss-setup/docs/local-ai-buildout-runlog.md`** (shipped-items table, all commits, the 20 e2e checks,
verification triage). New services: **SearXNG** (searxng.tabaska.us), **kiwix** + ZIM library incl. full
Wikipedia (kiwix.tabaska.us), **local-deep-research** (ldr.tabaska.us), **offline maps** PMTiles+Photon
(maps.tabaska.us), plus OWUI search/RAG/reranker/native-MCP/audio(Kokoro TTS+faster-whisper STT)/
image(ComfyUI)/code-exec(open-terminal)/native-memory, **opencode 1.18.10** pinned on Mac+rig with the
plugin array + skills bundle + DIY memory plugin, and reranker/comfyui/playwright/openzim/osm
MCPs (trilium-mcp retired 2026-08-14 with the read-27 trial). 19 consumer-probing checks live in
`verification/checks.d/local-ai.yaml` (domain `--host local-ai`), all green. Final full-fleet audit-safe run: **363/377 pass, ZERO genuine AI-stack
regressions** (the only lai-introduced fails — 9 new AI ports missing from the fix-51 exposure baseline —
were codified in `verification/assets/expected-listeners/`; the 1 crit + 13 other non-passes are
pre-existing residuals in CLAUDE.md/the `reopened` ledger, or GPU-gated best-effort daily checks).

**Open human follow-ups (none actioned):** **[SECURITY, urgent]** rotate `sudo.rig_password` (a lai-13
cached-sudo stdin fall-through exposed the value in a subagent transcript; cred file since rewritten
clean — follow `security-change-guard`); subscribe a phone to ntfy topic **`opencode`** (daily ~07:15
"Agent Idle" ping is expected); ~~register an operator account at **ldr.tabaska.us**~~ (DONE 2026-08-07
— `btabaska` account created); file the public **openZIM zim-request for strategywiki.org** then add the
`.zim` to the NAS `zim-download-queue.sh` (unblocks `lai-15`); ~~**Trilium-vs-Obsidian** decision~~
(DECIDED 2026-08-14 — Obsidian; Trilium + lai-16 trilium-mcp fully reverted, notes data kept at mini
`/opt/retired/trilium-20260814` pending purge); decide whether **Kagi** is retired or kept as a fallback engine; ~~schedule the **OWUI 0.11.0**
upgrade~~ (DONE 2026-08-16 — `lai-21`, v0.11.0 digest-pinned, all owui+journaling checks green; also shipped
`lai-22` **plant/species ID**: bioclip-api on rig :8199 [BioCLIP 2, CPU by design] + OWUI `identify_plant`
tool + 2 consumer checks — runbook `runbooks/plant-id.md`. NEW follow-up: the **chat lane (gemma4-31b-qat)
fails to load** when desktop VRAM residents [ComfyUI idle + Apollo NVENC + Steam] eat its <1GiB headroom —
decide: trim gemma ctx-size or free residents). Prior fleet-sweep follow-ups still stand (mini kernel reboot 4-7AM, rig
Windows `RealTimeIsUniversal`, off-mini dead-man/`alert-drill` ntfy subscribe, optional Bazarr subtitle
key). Next work is the pre-existing open queue (`ha-19`, `fix-24`, `game-*`, `media-09/10/13`,
`fix-70`…`fix-81`, etc.) via **`/build-next`** or **`/resolve-finding`**.

Prior priority (fleet-sweep 2026-08-02 remediation, `fix-49`…`fix-69` + `sec-12`) remains **COMPLETE**
(commits `667e361`…`25567cf`); its residuals are folded into the follow-up list above.
