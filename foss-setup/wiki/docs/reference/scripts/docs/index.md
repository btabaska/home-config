# Docs & tracker generators scripts

`foss-setup/scripts/docs/` — 15 script(s).

| Script | Role |
|---|---|
| [`add-dns-resilience-tasks.py`](add-dns-resilience-tasks-py.md) | Add dns-02..dns-05 resilience tasks + update dns-01 (idempotent). |
| [`apply-workstream-sequencing.py`](apply-workstream-sequencing-py.md) | Apply workstream sequencing to docs/index.html (task ids unchanged — preserves progress). |
| [`build-wiki.sh`](build-wiki-sh.md) | build and deploy wiki.tabaska.us (wiki-04) |
| [`gen-script-pages.py`](gen-script-pages-py.md) | generate wiki man-pages from scripts/ (wiki build-out). |
| [`gen-wiki-services.py`](gen-wiki-services-py.md) | generate wiki service pages from compose files (wiki-02). |
| [`generate-task-overrides.py`](generate-task-overrides-py.md) | Generate task-overrides.json for all tasks after net-13. |
| [`inject-handoff-workstream.py`](inject-handoff-workstream-py.md) | Add Agent handoff prep tier + tasks to docs/index.html (idempotent). |
| [`migrate-to-tracks.py`](migrate-to-tracks-py.md) | Migrate foss-setup/docs/index.html from linear phases to tiered parallel tracks. |
| [`patch-ai-handoff-badges.py`](patch-ai-handoff-badges-py.md) | Inject AI handoff map + badge/filter UI into foss-setup/docs/index.html. |
| [`patch-html-tasks.py`](patch-html-tasks-py.md) | One-shot patcher for foss-setup/docs/index.html task data. |
| [`publish-deploy.sh`](publish-deploy-sh.md) | publish foss-setup/ as the deployment repo (fix-07) |
| [`resequence-guide.py`](resequence-guide-py.md) | Resequence tasks in docs/index.html — see apply-workstream-sequencing.py for full workstre |
| [`sync-rollout-with-plan.py`](sync-rollout-with-plan-py.md) | Align Rollout Guide taskData in docs/index.html with current plan decisions. |
| [`tighten-tasks.py`](tighten-tasks-py.md) | Apply task-overrides.json to foss-setup/docs/index.html (tasks after net-13). |
| [`update-required-baseline.py`](update-required-baseline-py.md) | Tighten required baseline: per-task `required` flag, gap tasks, dependency fixes. |

[← All scripts](../index.md)
