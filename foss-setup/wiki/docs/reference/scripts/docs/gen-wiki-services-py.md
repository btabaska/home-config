# `gen-wiki-services.py`

> generate wiki service pages from compose files (wiki-02).

**Path:** `foss-setup/scripts/docs/gen-wiki-services.py` · **Category:** [Docs & tracker generators](index.md) · **Type:** Python

## Synopsis

```
python3 foss-setup/scripts/docs/gen-wiki-services.py
```

## What it does

```text
gen-wiki-services.py — generate wiki service pages from compose files (wiki-02).

Walks every compose stack in the repo:

  configs/docker-stack/stacks/*/compose.yaml      -> host: mini (adguard-nas -> nas)
  configs/docker-stack/*/docker-compose.yml       -> host: mini (wallabag)
  configs/nas/*/docker-compose.yml                -> host: nas

and emits one Markdown man-page per stack into wiki/docs/services/, plus a
generated services/index.md grouped by category, plus the nav block in
wiki/mkdocs.yml (between the BEGIN/END GENERATED SERVICES NAV markers).

Facts per stack: image + pin per service, host, ports, canonical URL
(https://<name>.tabaska.us convention, with known overrides), env var NAMES
from .env.example (never values), volumes, upstream doc links parsed from the
compose header comment.

Enrichment: if configs/docker-stack/service-catalog.yaml exists, its
category/url/description fields override the built-in maps (absence is fine).

Dependency-free: uses PyYAML when importable, otherwise falls back to a
minimal regex parser good enough for these simple compose files.

Usage:  python3 foss-setup/scripts/docs/gen-wiki-services.py
Output is deterministic (sorted) so re-running on a clean tree yields no diff.
```

## See also

- [`add-dns-resilience-tasks.py`](add-dns-resilience-tasks-py.md)
- [`apply-workstream-sequencing.py`](apply-workstream-sequencing-py.md)
- [`build-wiki.sh`](build-wiki-sh.md)
- [`gen-script-pages.py`](gen-script-pages-py.md)
- [`generate-task-overrides.py`](generate-task-overrides-py.md)
- [`inject-handoff-workstream.py`](inject-handoff-workstream-py.md)
- [`migrate-to-tracks.py`](migrate-to-tracks-py.md)
- [`patch-ai-handoff-badges.py`](patch-ai-handoff-badges-py.md)
- [`patch-html-tasks.py`](patch-html-tasks-py.md)
- [`publish-deploy.sh`](publish-deploy-sh.md)
- [`resequence-guide.py`](resequence-guide-py.md)
- [`sync-rollout-with-plan.py`](sync-rollout-with-plan-py.md)
- [Docs & tracker generators scripts](index.md) · [All scripts](../index.md)
