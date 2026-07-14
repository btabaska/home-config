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
category/url/description/notes fields override the built-in maps, and two
optional prose fields render extra sections (absence is fine):
  about:       prose block  -> "## About"  (after the metadata table)
  troubleshoot: list of {symptom, fix} (or strings) -> "## Troubleshooting"
                (after Environment, before Operations)

Dependency-free: uses PyYAML when importable, otherwise falls back to a
minimal regex parser good enough for these simple compose files.

Usage:  python3 foss-setup/scripts/docs/gen-wiki-services.py
Output is deterministic (sorted) so re-running on a clean tree yields no diff.
```

## See also

- [`build-wiki.sh`](build-wiki-sh.md)
- [`gen-checks-pages.py`](gen-checks-pages-py.md)
- [`gen-roadmap-pages.py`](gen-roadmap-pages-py.md)
- [`gen-script-pages.py`](gen-script-pages-py.md)
- [`gen-todo.py`](gen-todo-py.md)
- [`publish-deploy.sh`](publish-deploy-sh.md)
- [Docs & tracker generators scripts](index.md) · [All scripts](../index.md)
