# Host internals reference

Per-host operational internals — the Docker stack layout, the systemd units, and the
self-healing watchdogs that keep the fleet running unattended. High-level host summaries
live under **Hosts**; this section is the config-as-code detail behind them.

| Page | |
|---|---|
| [mini — Docker stack & daemon.json](mini-docker-stack.md) | `/opt/stacks` layout + the `fix-19` daemon.json |
| [mini — network resilience](mini-network-resilience.md) | Static IP + `net-selfheal` watchdog (the DHCP-lease-outage fix) |
| [rig — PCIe AER monitor](rig-pcie-aer-monitor.md) | AER → ntfy watchdog for the marginal NVMe PCIe link |
| [rig — background timers](rig-timers.md) | Music mirror + AI-stack watchdog timers |
| [Fleet systemd units — index](systemd-units.md) | Every `.service` / `.timer` in the repo, by host |

_5 pages._
