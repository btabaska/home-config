# `publish-deploy.sh`

> publish the repo to the forgejo deploy remote (fix-07)

**Path:** `foss-setup/scripts/docs/publish-deploy.sh` · **Category:** [Docs & tracker generators](index.md) · **Type:** Bash

## Synopsis

```
./foss-setup/scripts/docs/publish-deploy.sh
```

## What it does

```text
 publish-deploy.sh — publish the repo to the forgejo deploy remote (fix-07)

 Repo topology (since 2026-07-14):
   origin  = github.com/btabaska/home-config      — the FULL planning repo
   forgejo = forgejo:home/homelab (on the mini)   — the SAME full repo; hosts
             consume it with paths prefixed foss-setup/ (ansible-pull plays
             foss-setup/configs/ansible/site.yml, wiki-drift runs
             foss-setup/scripts/wiki/wiki-drift-check.sh, etc.)

 HISTORY: home/homelab originally held only the foss-setup/ subtree, published
 via `git subtree split`. On 2026-07-14 the full repo main was pushed there
 (ai-01 session) and consumers were repointed to foss-setup/-prefixed paths,
 so this script is now a plain push of main to both remotes.

 Usage: ./foss-setup/scripts/docs/publish-deploy.sh
```

## Environment / variables referenced

`ROOT`

## See also

- [`build-wiki.sh`](build-wiki-sh.md)
- [`gen-checks-pages.py`](gen-checks-pages-py.md)
- [`gen-roadmap-pages.py`](gen-roadmap-pages-py.md)
- [`gen-script-pages.py`](gen-script-pages-py.md)
- [`gen-todo.py`](gen-todo-py.md)
- [`gen-wiki-services.py`](gen-wiki-services-py.md)
- [Docs & tracker generators scripts](index.md) · [All scripts](../index.md)
