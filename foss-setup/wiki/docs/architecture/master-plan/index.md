# Master plan (Going Analogue)

> The canonical reference build for moving the household off the Apple/iOS ecosystem onto self-owned hardware and FOSS tooling — the "why" behind every host, service, and decision in this wiki.

_Source: `foss-setup-plan-2.md` · migrated + validated 2026-07-14._

This is a large design doc, split into per-section pages. Each page is faithful to the original plan, with **version-sensitive and status claims validated against live reality on 2026-07-14** (live HA REST, `ssh` to mini/nas/rig, container inventories) and corrected where the plan drifted. Where something is planned/aspirational vs. actually deployed, it is marked.

## What changed since the plan was written (validation summary)

The plan is mostly still accurate, but several decisions were made or reversed after it was drafted. The big ones, verified live:

| Plan said | Reality (validated 2026-07-14) |
|---|---|
| LiteLLM gateway + small always-on fallback model in front of HA voice | **Retired** (AI-stack SPOF accepted). HA Assist points **directly at rig Ollama** (`conversation.rig_ollama_assist`). LiteLLM was **never deployed** on the mini — a phantom. |
| Dependency-Track v5 on the NAS as the SBOM centerpiece (§8) | **Fully retired.** SBOM/Dependency-Track judged overkill for a home net (syft OOM'd the 8 GB mini). No DT containers on the NAS; nightly SBOM timers disabled. |
| Tdarr + Maintainerr in the media-companion layer | **Both removed from the plan** (2026-07-08). Re-encoding conflicts with TRaSH quality automation; no auto-deletion wanted. |
| DS920+ needs a RAM upgrade before the offload plan | **Done** — NAS reports **20 GB** live. Limp-mode guidance retired. |
| Coolify PaaS for vibecoded apps | **Dropped** — non-starter on the 8 GB mini. **Caddy fronts everything** (plain Compose stacks, "option A"). |
| HAOS in a KVM VM as the HA host alternative | **Superseded** — HA runs on **HA Green** hardware (live, v2026.6.4). |
| Game servers via LinuxGSM (mini) + Tailscale-expose | **Superseded** — heavy servers run on **AMP on the rig** (24/7), exposed via **playit premium**. |
| Fail-open DNS: NAT :53 redirect + block DoH | **Retired** — operator prefers AdGuard-down clients bypass to the gateway over a house-wide DNS blackhole. |
| Frigate on the NAS iGPU | **Deferred** — UniFi Protect's built-in detection judged sufficient. Not deployed. |
| Second off-site backup; rotated Tier-2 HDD | **Both retired** — one off-site (B2, Object Lock) is enough; Tier-2 media is re-acquirable. |

The rig runs **24/7** (settled 2026-07-08); Wake-on-LAN is recovery tooling only, not a workflow. See the sections for detail.

## Sections

| # | Section |
|---|---|
| 0 | [The host decision — everything runs 24/7](host-decision.md) |
| 1 | [The home network — segmenting the UniFi Dream Wall](network.md) |
| 2 | [FOSS replacements, by Apple/iOS task](replacements.md) |
| 3 | [Smart home — Home Assistant](smart-home.md) |
| 4 | [Game servers and game streaming](gaming.md) |
| 5 | [Electricity cost of running hardware 24/7](power.md) |
| 6 | [Backup, beyond the NAS](backup.md) |
| 7 | ["Set it and forget it" configuration](set-and-forget.md) |
| 8 | [Inventory, SBOMs & rebuildable state](inventory-sbom.md) |
| 9 | [Fleet automation with Ansible](ansible.md) |
| — | [Suggested rollout (phased)](rollout.md) |
| — | [Cheap local sensor shopping list](sensor-shopping-list.md) |
| — | [The stack at a glance](stack-at-a-glance.md) |
| — | [Appendix A — superseded designs (kept for history)](appendix-a-superseded.md) |

---

> **Deliberate cloud exceptions.** Local-first is the principle, not a purity test: **Obsidian Sync** (official E2E-encrypted notes sync), **Backblaze B2** (the off-site backup target), and **Tailscale** (hosted control plane for the mesh VPN) are intentional, pragmatic exceptions — kept because they are the set-and-forget choice, not oversights.

---
[← Architecture & design](../index.md)
