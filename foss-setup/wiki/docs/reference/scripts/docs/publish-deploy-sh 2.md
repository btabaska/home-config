# `publish-deploy.sh`

> publish foss-setup/ as the deployment repo (fix-07)

**Path:** `foss-setup/scripts/docs/publish-deploy.sh` · **Category:** [Docs & tracker generators](index.md) · **Type:** Bash

## Synopsis

```
./foss-setup/scripts/docs/publish-deploy.sh [--force]
```

## What it does

```text
 publish-deploy.sh — publish foss-setup/ as the deployment repo (fix-07)

 Repo topology:
   origin  = github.com/btabaska/home-config      — the FULL planning repo
   forgejo = forgejo:home/homelab (on the mini)   — DEPLOY repo = foss-setup/ subtree;
             hosts run ansible-pull against it, so its root is configs/, scripts/, docs/

 This script splits the foss-setup/ prefix into a synthetic branch and pushes it
 to forgejo main. git subtree split is deterministic for a given history, so
 subsequent publishes fast-forward. Run from anywhere inside the repo.

 First publish after the 2026-07-07 topology reconciliation used --force (the
 old forgejo lineage was unrelated; its unique content was imported first —
 see commit "Import macmini sbom manifest exports").

 Usage: ./foss-setup/scripts/docs/publish-deploy.sh [--force]
```

## Environment / variables referenced

`FORCE`, `ROOT`, `SPLIT_SHA`

## See also

- [`build-wiki.sh`](build-wiki-sh.md)
- [`gen-checks-pages.py`](gen-checks-pages-py.md)
- [`gen-roadmap-pages.py`](gen-roadmap-pages-py.md)
- [`gen-script-pages.py`](gen-script-pages-py.md)
- [`gen-todo.py`](gen-todo-py.md)
- [`gen-wiki-services.py`](gen-wiki-services-py.md)
- [Docs & tracker generators scripts](index.md) · [All scripts](../index.md)
