# Going Analogue — homelab config & docs

Local-first homelab: moving off the Apple/iCloud ecosystem onto owned hardware (DS920+ NAS, Mac mini/Ubuntu, CachyOS rig, HA Green, UniFi Dream Wall, plus an off-site seedbox).

**Start here:**

1. **[foss-setup-plan-2.md](foss-setup-plan-2.md)** — the why: the full design narrative (hosts, services, backups, principles).
2. **[foss-setup/docs/index.html](foss-setup/docs/index.html)** — the what/when: the Plan v3 rollout tracker, organized as 8 staged runs. Open it in a browser; live progress is tracked there.
3. **[foss-setup/](foss-setup/)** — the how: config-as-code. `configs/` is declarative (compose stacks, network plans, host configs), `scripts/` is idempotent (safe to re-run).

**Other files:** [agent-fix-tasks.md](agent-fix-tasks.md) is an older fix checklist, partially superseded by Plan v3's audit-fixes track but kept for its per-edit specs.

**Secrets** live ONLY in `foss-setup/.handoff-secrets.yaml` (gitignored). Nothing else in the repo may contain a credential.

**Repo topology:**

- `origin` = GitHub **btabaska/home-config** — this full repo.
- Forgejo **home/homelab** (on the Mac mini) — the deployment repo that hosts ansible-pull from; it is the `foss-setup/` subtree, published via `scripts/docs/publish-deploy.sh` (to be added).
- `/opt/stacks` on the mini = Forgejo **home/docker-stacks** — the live compose state.
