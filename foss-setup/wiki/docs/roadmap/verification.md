# Roadmap — verification

15 task(s). Status mirrors `docs/progress.json` (the source of truth).

| Task | Title | Status | Effort |
|---|---|---|---|
| `fix-100` | Check-integrity hardening — liveness-masquerade + fail-open + task_id drift + stale expects (mandate #1) | ⬜ open | 1-3 hrs |
| `fix-101` | Monitoring-coverage gaps + census enrollment + deploy tripwire (mandate #2, reconfirms verify-06/fix-68) | ✅ done | 1-3 hrs |
| `fix-29` | Close the liveness-vs-reality monitoring gap (end-to-end checks for the failure classes just found) | ✅ done | 1-3 hrs |
| `fix-30` | Repair the verification framework itself (LLM triage, false positives, deploy drift) | ✅ done | 1-3 hrs |
| `fix-61` | Verification framework repair: daily run killed by its own 30-min timeout mid-incident (dead-man dark, no self-page), triage 91% nonfunctional, chronic false-positive + flapping checks | ✅ done | 1-3 hrs |
| `fix-62` | Check quality + coverage batch: 4 structurally-broken checks (plex-version, stash auth, immich-backup 60s find, esde), Stash no-op self-heal page storm, liveness-only quartet, filed monitoring gaps | ✅ done | 1-3 hrs |
| `fix-97` | New-service deploy completion — unsloth-studio (lai-28) + bioclip (lai-22) never finished coverage/catalog/wiki/baseline (fix-68 regression) | ✅ done | 1-3 hrs |
| `fix-98` | rig listener-baseline codification — bless Steam 27036 + MoonDeckBuddy 59999 (fix-51 extension) | ✅ done | 1-3 hrs |
| `fix-99` | checks.d dead runbook paths — fleet-wide catch-all | ✅ done | 1-3 hrs |
| `verify-01` | Probe library — checks.d/*.yaml per service and host | ✅ done | 2 hr |
| `verify-02` | Runner + schedule — run-checks over SSH from mini, ntfy on regression | ✅ done | 2 hr |
| `verify-03` | Local-LLM triage skills — scoped prompts, one failure per context | ✅ done | 2-3 hr |
| `verify-04` | Rig model setup — pin models sized for the 3090 Ti, LiteLLM routes | ✅ done | 1 hr |
| `verify-05` | Regression wiring — failed checks auto-reopen tasks in progress.json | ✅ done | 1 hr |
| `verify-06` | Import-pipeline + fleet-coverage OUTCOME checks — the consumer-end verification layer | ✅ done | built incrementally 2026-07-10..17 |

[← Roadmap overview](index.md)
