# `build-wiki.sh`

> build and deploy wiki.tabaska.us (wiki-04)

**Path:** `foss-setup/scripts/docs/build-wiki.sh` · **Category:** [Docs & tracker generators](index.md) · **Type:** Bash

## Synopsis

```
./foss-setup/scripts/docs/build-wiki.sh   (from the operator MacBook)
```

## What it does

```text
 build-wiki.sh — build and deploy wiki.tabaska.us (wiki-04)

 What it does (idempotent, safe to re-run):
   1. rsync foss-setup/wiki/ to the mini (/tmp/wiki-src)
   2. dockerized, PINNED mkdocs build ON the mini:
        docker run --rm -v /tmp/wiki-src:/docs squidfunk/mkdocs-material:9.5 build --strict
      (tag verified present on the mini; --strict fails on broken internal links)
   3. sudo rsync the built site/ into /opt/stacks/wiki/site, which Caddy
      serves at https://wiki.tabaska.us via file_server

 Regenerate generated pages first if the repo changed:
   python3 foss-setup/scripts/docs/gen-wiki-services.py   # service pages (compose)
   python3 foss-setup/scripts/docs/gen-script-pages.py    # script man-pages
   python3 foss-setup/scripts/docs/gen-roadmap-pages.py   # todo list from progress.json

 Usage: ./foss-setup/scripts/docs/build-wiki.sh   (from the operator MacBook)
   env: MINI=<ssh alias> (default: mini)
```

## Environment / variables referenced

`IMAGE`, `MINI`, `REMOTE_SRC`, `SITE_DIR`, `WIKI_DIR`

## See also

- [`gen-checks-pages.py`](gen-checks-pages-py.md)
- [`gen-roadmap-pages.py`](gen-roadmap-pages-py.md)
- [`gen-script-pages.py`](gen-script-pages-py.md)
- [`gen-todo.py`](gen-todo-py.md)
- [`gen-wiki-services.py`](gen-wiki-services-py.md)
- [`publish-deploy.sh`](publish-deploy-sh.md)
- [Docs & tracker generators scripts](index.md) · [All scripts](../index.md)
