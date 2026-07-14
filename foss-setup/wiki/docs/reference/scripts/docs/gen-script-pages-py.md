# `gen-script-pages.py`

> generate wiki man-pages from scripts/ (wiki build-out).

**Path:** `foss-setup/scripts/docs/gen-script-pages.py` · **Category:** [Docs & tracker generators](index.md) · **Type:** Python

## Synopsis

```
python3 foss-setup/scripts/docs/gen-script-pages.py
```

## What it does

```text
gen-script-pages.py — generate wiki man-pages from scripts/ (wiki build-out).

Walks scripts/**/*.{sh,py} and emits one SMALL, linked Markdown man-page per
script into wiki/docs/reference/scripts/<category>/<name>.md, plus a per-category
index and a top scripts index, plus the nav block in mkdocs.yml (between the
BEGIN/END GENERATED SCRIPTS NAV markers).

Design goals (operator, 2026-07-14): pages small enough for a local LLM's context,
DENSELY linked so an agent can traverse to what it needs. Each page = NAME / role,
PATH, SYNOPSIS (usage line), WHAT IT DOES (header comment), ENV (referenced vars),
SEE ALSO (sibling scripts + category + repo path). Deterministic — re-running on a
clean tree yields no diff.

Usage: python3 foss-setup/scripts/docs/gen-script-pages.py
```

## See also

- [`build-wiki.sh`](build-wiki-sh.md)
- [`gen-checks-pages.py`](gen-checks-pages-py.md)
- [`gen-roadmap-pages.py`](gen-roadmap-pages-py.md)
- [`gen-todo.py`](gen-todo-py.md)
- [`gen-wiki-services.py`](gen-wiki-services-py.md)
- [`publish-deploy.sh`](publish-deploy-sh.md)
- [Docs & tracker generators scripts](index.md) · [All scripts](../index.md)
