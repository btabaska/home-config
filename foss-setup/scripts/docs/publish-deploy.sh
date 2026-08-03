#!/usr/bin/env bash
#
# publish-deploy.sh — publish the repo to the forgejo deploy remote (fix-07)
#
# Repo topology (since 2026-07-14):
#   origin  = github.com/btabaska/home-config      — the FULL planning repo
#   forgejo = forgejo:home/homelab (on the mini)   — the SAME full repo; hosts
#             consume it with paths prefixed foss-setup/ (ansible-pull plays
#             foss-setup/configs/ansible/site.yml, wiki-drift runs
#             foss-setup/scripts/wiki/wiki-drift-check.sh, etc.)
#
# HISTORY: home/homelab originally held only the foss-setup/ subtree, published
# via `git subtree split`. On 2026-07-14 the full repo main was pushed there
# (ai-01 session) and consumers were repointed to foss-setup/-prefixed paths,
# so this script is now a plain push of main to both remotes.
#
# Usage: ./foss-setup/scripts/docs/publish-deploy.sh

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "${ROOT}"

# fix-23: vault-completeness gate — a live service whose credential exists only on a
# host filesystem (vault key '') is the M26/M44/M45 incident class. Lint runs here
# because the vault lives only on this machine; the mini runner can't see it.
echo "[publish] linting the secrets vault..."
python3 "${ROOT}/foss-setup/scripts/secrets/vault-lint.py"

# fix-68 (SM48 / wiki-05): same-commit regen gate. ai-04's commit 554c560 added a
# check without regenerating its wiki page, so the published wiki drifted and the
# wiki-drift check went red for days. Fail the publish BEFORE it reaches the
# remotes if HEAD's committed sources don't match a fresh regeneration, and if the
# tracker sources are incoherent. This makes "commit a source without regenerating"
# unpushable rather than caught a day later by the mini runner.
echo "[publish] tracker-integrity gate..."
python3 "${ROOT}/foss-setup/scripts/verification/tracker-integrity.py"
echo "[publish] wiki-drift (same-commit) gate — regenerating HEAD in a throwaway worktree..."
if ! bash "${ROOT}/foss-setup/scripts/wiki/wiki-drift-check.sh"; then
  echo "[publish] ABORT: wiki drift or tooling error — regenerate (gen-*.py or build-wiki.sh)" >&2
  echo "[publish]        and commit the result in the SAME commit as the source change, then re-run." >&2
  exit 1
fi

echo "[publish] pushing main to origin (GitHub)..."
git push origin main

echo "[publish] pushing main to forgejo home/homelab..."
git push forgejo main:main

echo "[publish] done. Hosts pulling forgejo:home/homelab get this state on their next ansible-pull cycle."
