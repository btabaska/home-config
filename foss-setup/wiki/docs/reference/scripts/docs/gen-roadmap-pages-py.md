# `gen-roadmap-pages.py`

> mirror the task tracker into the wiki (todo list).

**Path:** `foss-setup/scripts/docs/gen-roadmap-pages.py` · **Category:** [Docs & tracker generators](index.md) · **Type:** Python

## Synopsis

```
python3 foss-setup/scripts/docs/gen-roadmap-pages.py
```

## What it does

```text
gen-roadmap-pages.py — mirror the task tracker into the wiki (todo list).

Reads the SOURCE OF TRUTH — docs/tasks.json (definitions) + docs/progress.json
(status) — and emits small, linked per-track roadmap pages into wiki/docs/roadmap/, plus an index
with live counts, plus the mkdocs nav block. So the wiki carries the todo list
(browsable by humans + local LLMs) without becoming a second source of truth: this
is GENERATED from progress.json, re-run after any tracker change.

Usage: python3 foss-setup/scripts/docs/gen-roadmap-pages.py
```

## See also

- [`build-wiki.sh`](build-wiki-sh.md)
- [`gen-checks-pages.py`](gen-checks-pages-py.md)
- [`gen-script-pages.py`](gen-script-pages-py.md)
- [`gen-todo.py`](gen-todo-py.md)
- [`gen-wiki-services.py`](gen-wiki-services-py.md)
- [`publish-deploy.sh`](publish-deploy-sh.md)
- [Docs & tracker generators scripts](index.md) · [All scripts](../index.md)
