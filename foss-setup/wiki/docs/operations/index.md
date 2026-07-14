# Operations

How the fleet is run day-to-day: convergence with Ansible, the secrets policy, the
tracker/AI-session flow, the config-as-code repo layout, the host inventory, and the
per-host restore runbook.

| Page | |
|---|---|
| [Ansible & convergence](ansible.md) | `ansible-pull` (per-host timer) + the glue-07 push lever |
| [Secrets policy](secrets.md) | Where secrets live and how they're handled |
| [Tracker & AI sessions](tracker.md) | Tasks-as-data (`tasks.json` + `progress.json`) → generated views |
| [Maintenance calendar](maintenance-calendar.md) | What runs when — timers, backups, drills |
| [Repo structure, branching & secrets](repo-structure.md) | Config-as-code monorepo layout + dual remotes |
| [Host inventory](inventory.md) | Point-in-time manifest export (mini) |
| [Restore runbook (template)](restore-runbook-template.md) | Fill-in-the-blank per-host rebuild procedure |

_6 pages._
