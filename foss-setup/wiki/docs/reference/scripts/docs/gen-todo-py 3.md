# `gen-todo.py`

> generate the single todo.md (all remaining project tasks).

**Path:** `foss-setup/scripts/docs/gen-todo.py` · **Category:** [Docs & tracker generators](index.md) · **Type:** Python

## Synopsis

```
python3 foss-setup/scripts/docs/gen-todo.py
```

## What it does

```text
gen-todo.py — generate the single todo.md (all remaining project tasks).

Reads the canonical task data (docs/tasks.json = definitions) + docs/progress.json
(status) and writes /todo.md at the repo root: every REMAINING task (open +
deferred), grouped by track, plus a summary. This is the one working todo list;
the wiki roadmap is the browsable mirror; both generate from the same data. Run
after any task change. Deterministic.

Usage: python3 foss-setup/scripts/docs/gen-todo.py
```

## See also

- [`build-wiki.sh`](build-wiki-sh.md)
- [`gen-checks-pages.py`](gen-checks-pages-py.md)
- [`gen-roadmap-pages.py`](gen-roadmap-pages-py.md)
- [`gen-script-pages.py`](gen-script-pages-py.md)
- [`gen-wiki-services.py`](gen-wiki-services-py.md)
- [`publish-deploy.sh`](publish-deploy-sh.md)
- [Docs & tracker generators scripts](index.md) · [All scripts](../index.md)
