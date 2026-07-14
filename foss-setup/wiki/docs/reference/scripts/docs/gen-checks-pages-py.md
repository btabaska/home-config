# `gen-checks-pages.py`

> wiki reference for every verification check (wiki build-out).

**Path:** `foss-setup/scripts/docs/gen-checks-pages.py` · **Category:** [Docs & tracker generators](index.md) · **Type:** Python

## Synopsis

```
python3 foss-setup/scripts/docs/gen-checks-pages.py
```

## What it does

```text
gen-checks-pages.py — wiki reference for every verification check (wiki build-out).

Reads verification/checks.d/*.yaml and emits one small linked page per domain
(file), documenting each check: id, what it proves, host, severity, the exact cmd,
expected match, and the task it guards. Plus an index with counts. Deterministic.

Usage: python3 foss-setup/scripts/docs/gen-checks-pages.py
```

## See also

- [`build-wiki.sh`](build-wiki-sh.md)
- [`gen-roadmap-pages.py`](gen-roadmap-pages-py.md)
- [`gen-script-pages.py`](gen-script-pages-py.md)
- [`gen-todo.py`](gen-todo-py.md)
- [`gen-wiki-services.py`](gen-wiki-services-py.md)
- [`publish-deploy.sh`](publish-deploy-sh.md)
- [Docs & tracker generators scripts](index.md) · [All scripts](../index.md)
