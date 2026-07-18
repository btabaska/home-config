# Runbook — Rebuild a host

The headline promise: **any owned box is disposable — bare OS to running in
under an hour** from git + the vault + backups. This is drilled (glue-06) in
a throwaway VM; the drill is the proof, this page is the procedure.

## The generic shape (mini, rig, or a drill VM)

```bash
# 1. Bare OS (Ubuntu for mini, CachyOS for rig) + basics
sudo apt install -y git curl   # or pacman -S

# 2. Clone the deploy repo (Forgejo; GitHub home-config also works)
git clone git@forgejo:home/homelab.git   # full repo; deploy tree = foss-setup/
# forgejo alias → macmini.tailb31641.ts.net, SSH port 2222 (~/.ssh/config)
cd homelab

# 3. Converge the host layer — ansible-pull does OS packages, Docker engine,
#    daemon.json log rotation, the edge network, tailscale, timers, chezmoi
sudo cp foss-setup/configs/ansible/ansible-pull.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now ansible-pull.timer
sudo systemctl start ansible-pull.service   # first converge now, not at 04:20

# 4. Stacks (mini only): clone the live compose state
git clone git@forgejo:home/docker-stacks.git /opt/stacks

# 5. Secrets: recreate each stack's .env from .env.example + the vault
#    (foss-setup/.handoff-secrets.yaml on the operator MacBook — values are
#    typed/templated in, never committed)

# 6. Bring stacks up in dependency order: edge first
docker network create edge          # hard prerequisite, easy to skip
cd /opt/stacks/caddy    && docker compose up -d
cd /opt/stacks/adguard  && docker compose up -d   # then unbound, then the rest
for d in /opt/stacks/*/; do (cd "$d" && docker compose up -d); done

# 7. Restore data volumes (DB-backed services) — see Backup & restore
#    restic restore per volume (live on mini/rig — /etc/restic/env);
#    Immich DB from pg_dump

# 8. Rejoin the tailnet
sudo tailscale up --ssh
```

## Per-host deltas

| Host | Differences |
|---|---|
| **mini** | Steps above verbatim. Also: etckeeper init, verify Caddy has certs (volume `caddy_data` restore avoids LE rate limits) |
| **rig** | Has its own `/opt/stacks` (gaming: amp, palworld, playit, beszel-agent — compose sources in `configs/gaming/` + `configs/host/rig/`; AMP instance + Palworld saves restore from restic). The **AI stack (litellm/open-webui/mcpo) lives in the separate `local-ai-tooling` repo** — clone it to `~/Documents/GitHub/` and `compose up` from its `docker/` dir; native Ollama via pacman. Plus chezmoi + pacman manifests via ansible-pull; `gpu-power-tune.service`; host timers (`ai-stack-watchdog`, `pcie-aer-monitor`, `playit-udp-guard`) from `configs/host/rig/`. ⚠️ AMP licence is hostname-pinned — restore the compose `hostname:` before `up` or instance licences invalidate |
| **nas** | **Not this runbook** — DSM Configuration Backup restore + Container Manager projects from `configs/nas/` + data from Hyper Backup |
| **HA** | Restore its own backup archive (key in Bitwarden) |
| **gateway** | Restore the `.unf` export in the UniFi GUI |

## Verify (the drill's pass condition)

- Every stack `docker compose ps` healthy; Homepage green; Uptime Kuma green.
- `ansible-pull` converges clean on the next timer fire (ok>0 failed=0).
- Elapsed time recorded in the tracker; gaps found → runbook updated in the
  same commit (glue-06: "record gaps; update runbook").

Template with the long-form checklist:
`configs/inventory/restore-runbook-template.md`.
