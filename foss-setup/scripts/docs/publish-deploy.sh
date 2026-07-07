#!/usr/bin/env bash
#
# publish-deploy.sh — publish foss-setup/ as the deployment repo (fix-07)
#
# Repo topology:
#   origin  = github.com/btabaska/home-config      — the FULL planning repo
#   forgejo = forgejo:home/homelab (on the mini)   — DEPLOY repo = foss-setup/ subtree;
#             hosts run ansible-pull against it, so its root is configs/, scripts/, docs/
#
# This script splits the foss-setup/ prefix into a synthetic branch and pushes it
# to forgejo main. git subtree split is deterministic for a given history, so
# subsequent publishes fast-forward. Run from anywhere inside the repo.
#
# First publish after the 2026-07-07 topology reconciliation used --force (the
# old forgejo lineage was unrelated; its unique content was imported first —
# see commit "Import macmini sbom manifest exports").
#
# Usage: ./foss-setup/scripts/docs/publish-deploy.sh [--force]

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "${ROOT}"

FORCE=""
[[ "${1:-}" == "--force" ]] && FORCE="--force"

echo "[publish] splitting foss-setup/ subtree..."
SPLIT_SHA="$(git subtree split --prefix=foss-setup)"
echo "[publish] subtree head: ${SPLIT_SHA}"

echo "[publish] pushing to forgejo main..."
git push ${FORCE} forgejo "${SPLIT_SHA}:refs/heads/main"

echo "[publish] done. Hosts pulling forgejo:home/homelab get this state on their next ansible-pull cycle."
echo "[publish] NOTE: after a --force publish, refresh host clones: ssh mini 'rm -rf ~/.ansible-pull' (re-clones on next timer fire)."
