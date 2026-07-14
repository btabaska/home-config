# `wiki-drift-check.sh`

> wiki-drift-check.sh (wiki-05) — enforce the "same-commit rule".

**Path:** `foss-setup/scripts/wiki/wiki-drift-check.sh` · **Category:** [wiki](index.md) · **Type:** Bash

## Synopsis

```
bash scripts/wiki/wiki-drift-check.sh
```

## What it does

```text
 wiki-drift-check.sh (wiki-05) — enforce the "same-commit rule".

 The wiki is generated from repo sources (tasks/progress JSON, checks.d/*.yaml,
 the docker-stack service catalog+enrichment, and the scripts themselves). The
 rule that keeps the manual honest: ANY change to those sources must regenerate
 the affected wiki pages IN THE SAME COMMIT. This check proves it — it checks
 out HEAD into a throwaway git worktree, re-runs every page generator there, and
 diffs the result against what HEAD actually committed. Any difference means a
 source changed but its generated page did not => STALE wiki.

   exit 0  — in sync (generated pages match a fresh regeneration)
   exit 1  — DRIFT (prints the stale paths)
   exit 2  — environment/tooling error (not a drift verdict)

 Read-only wrt the invoking working tree: all regeneration happens in a detached
 worktree under $TMPDIR, removed on exit. Works from either the full planning
 repo (sources under foss-setup/) or the forgejo deploy subtree (sources at the
 repo root). Deps: git >=2.5, python3, python-yaml (same as the generators).

 Usage:  bash scripts/wiki/wiki-drift-check.sh
 Wired into verification as the `wiki-drift` check (see checks.d/git-hygiene.yaml),
 which runs it against a fresh forgejo checkout so the verify timer tests HEAD.
```

## Environment / variables referenced

`DRIFT`, `GENDIR`, `GENERATORS`, `GEN_PATHS`, `GIT_ROOT`, `SELF_DIR`, `SUB`, `TMPDIR`

## See also

- [wiki scripts](index.md) · [All scripts](../index.md)
