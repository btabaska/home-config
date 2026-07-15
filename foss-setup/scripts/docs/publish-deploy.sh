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

echo "[publish] pushing main to origin (GitHub)..."
git push origin main

echo "[publish] pushing main to forgejo home/homelab..."
git push forgejo main:main

echo "[publish] done. Hosts pulling forgejo:home/homelab get this state on their next ansible-pull cycle."
