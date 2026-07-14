#!/usr/bin/env bash
#
# wiki-drift-check.sh (wiki-05) — enforce the "same-commit rule".
#
# The wiki is generated from repo sources (tasks/progress JSON, checks.d/*.yaml,
# the docker-stack service catalog+enrichment, and the scripts themselves). The
# rule that keeps the manual honest: ANY change to those sources must regenerate
# the affected wiki pages IN THE SAME COMMIT. This check proves it — it checks
# out HEAD into a throwaway git worktree, re-runs EVERY page generator there, and
# looks for any change to the worktree. Any change means a source was committed
# but its generated page was not => STALE wiki.
#
#   exit 0  — in sync (generated pages match a fresh regeneration)
#   exit 1  — DRIFT (prints the stale paths)
#   exit 2  — environment/tooling error (not a drift verdict)
#
# Coverage is automatic: it runs every scripts/docs/gen-*.py it finds and diffs
# the WHOLE worktree, so a newly-added generator (or a new output path) is covered
# with no edit here — there is no allow-list to drift out of date. The only special
# case is gen-todo.py, which writes todo.md at the PLANNING-repo root (parent of
# foss-setup); that path only exists in the full planning repo, so it is skipped in
# the forgejo deploy subtree.
#
# Read-only wrt the invoking working tree: all regeneration happens in a detached
# worktree under $TMPDIR, removed on exit. Works from either the full planning repo
# (sources under foss-setup/) or the forgejo deploy subtree (sources at the repo
# root). Deps: git >=2.5, python3, python-yaml (same as the generators).
#
# Usage:  bash scripts/wiki/wiki-drift-check.sh
# Wired into verification as the `wiki-drift` check (see checks.d/git-hygiene.yaml),
# which runs it against a fresh forgejo checkout so the verify timer tests HEAD.
set -uo pipefail
export PYTHONDONTWRITEBYTECODE=1   # no __pycache__ noise in the worktree diff

die()  { echo "wiki-drift: $*" >&2; exit 2; }

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || die "cannot resolve self dir"
GIT_ROOT="$(git -C "$SELF_DIR" rev-parse --show-toplevel 2>/dev/null)" || die "not inside a git repo"

# Locate the foss-setup root (the dir that holds scripts/docs/gen-*.py + wiki/),
# relative to the repo root. Full planning repo -> "foss-setup"; deploy subtree -> ".".
if   [ -d "$GIT_ROOT/foss-setup/scripts/docs" ]; then SUB="foss-setup"
elif [ -d "$GIT_ROOT/scripts/docs" ];            then SUB="."
else die "cannot locate scripts/docs under $GIT_ROOT"; fi

command -v python3 >/dev/null 2>&1 || die "python3 not found"

# Throwaway worktree at HEAD. prune first so a killed prior run can't wedge us.
git -C "$GIT_ROOT" worktree prune 2>/dev/null || true
WT="$(mktemp -d "${TMPDIR:-/tmp}/wiki-drift.XXXXXX")" || die "mktemp failed"
cleanup() { git -C "$GIT_ROOT" worktree remove --force "$WT" >/dev/null 2>&1 || rm -rf "$WT"; }
trap cleanup EXIT
git -C "$GIT_ROOT" worktree add --detach -q "$WT" HEAD 2>/dev/null || die "git worktree add failed"

GENDIR="$WT/$SUB/scripts/docs"
shopt -s nullglob
GENERATORS=("$GENDIR"/gen-*.py)
shopt -u nullglob
[ "${#GENERATORS[@]}" -gt 0 ] || die "no generators found under $SUB/scripts/docs (checkout too old?)"

for g in "${GENERATORS[@]}"; do
  name="$(basename "$g")"
  # gen-todo writes todo.md at the PLANNING-repo root (outside foss-setup); that file
  # only exists in the full repo, so run it only there (skip in the deploy subtree).
  if [ "$name" = "gen-todo.py" ] && [ "$SUB" != "foss-setup" ]; then continue; fi
  if ! err="$(python3 "$g" 2>&1 >/dev/null)"; then
    die "generator $name failed: $err"
  fi
done

# Any change to the freshly-regenerated worktree = drift. Whole-tree status (not an
# allow-list) so a new generator's output is covered automatically. __pycache__ is
# gitignored + PYTHONDONTWRITEBYTECODE is set, so only real page changes show up.
DRIFT="$(git -C "$WT" status --porcelain 2>/dev/null)"

if [ -n "$DRIFT" ]; then
  echo "WIKI DRIFT: committed generated pages are stale vs a fresh regeneration."
  echo "$DRIFT"
  echo "--"
  echo "Fix: rerun the page generators (or build-wiki.sh) and commit the result in"
  echo "the SAME commit as the source change. Then this check clears."
  exit 1
fi
echo "wiki in sync: all generated pages match a fresh regeneration of HEAD ($SUB)"
exit 0
