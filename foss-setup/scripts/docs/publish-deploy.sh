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

echo "[publish] pushing main to origin (GitHub)..."
git push origin main

echo "[publish] pushing main to forgejo home/homelab..."
git push forgejo main:main

echo "[publish] done. Hosts pulling forgejo:home/homelab get this state on their next ansible-pull cycle."
