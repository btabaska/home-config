# Roadmap — verification

7 task(s). Status mirrors `docs/progress.json` (the source of truth).

| Task | Title | Status | Effort |
|---|---|---|---|
| `fix-29` | Close the liveness-vs-reality monitoring gap (end-to-end checks for the failure classes just found) | ✅ done | 1-3 hrs |
| `fix-30` | Repair the verification framework itself (LLM triage, false positives, deploy drift) | ✅ done | 1-3 hrs |
| `verify-01` | Probe library — checks.d/*.yaml per service and host | ✅ done | 2 hr |
| `verify-02` | Runner + schedule — run-checks over SSH from mini, ntfy on regression | ✅ done | 2 hr |
| `verify-03` | Local-LLM triage skills — scoped prompts, one failure per context | ✅ done | 2-3 hr |
| `verify-04` | Rig model setup — pin models sized for the 3090 Ti, LiteLLM routes | ✅ done | 1 hr |
| `verify-05` | Regression wiring — failed checks auto-reopen tasks in progress.json | ✅ done | 1 hr |

[← Roadmap overview](index.md)
