#!/usr/bin/env bash
#
# build-wiki.sh — build and deploy wiki.tabaska.us (wiki-04)
#
# What it does (idempotent, safe to re-run):
#   1. rsync foss-setup/wiki/ to the mini (/tmp/wiki-src)
#   2. dockerized, PINNED mkdocs build ON the mini:
#        docker run --rm -v /tmp/wiki-src:/docs squidfunk/mkdocs-material:9.5 build --strict
#      (tag verified present on the mini; --strict fails on broken internal links)
#   3. sudo rsync the built site/ into /opt/stacks/wiki/site, which Caddy
#      serves at https://wiki.tabaska.us via file_server
#
# Regenerate service pages first if compose files changed:
#   python3 foss-setup/scripts/docs/gen-wiki-services.py
#
# Usage: ./foss-setup/scripts/docs/build-wiki.sh   (from the operator MacBook)
#   env: MINI=<ssh alias> (default: mini)

set -euo pipefail

MINI="${MINI:-mini}"
IMAGE="squidfunk/mkdocs-material:9.5"
WIKI_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../wiki" && pwd)"
REMOTE_SRC="/tmp/wiki-src"
SITE_DIR="/opt/stacks/wiki/site"

echo "[wiki] syncing source ${WIKI_DIR} -> ${MINI}:${REMOTE_SRC}"
rsync -a --delete --exclude 'site/' "${WIKI_DIR}/" "${MINI}:${REMOTE_SRC}/"

echo "[wiki] building on ${MINI} with ${IMAGE} (--strict)"
ssh "${MINI}" "docker run --rm -v ${REMOTE_SRC}:/docs ${IMAGE} build --strict"

echo "[wiki] deploying -> ${MINI}:${SITE_DIR}"
ssh "${MINI}" "sudo mkdir -p ${SITE_DIR} && sudo rsync -a --delete ${REMOTE_SRC}/site/ ${SITE_DIR}/"

ssh "${MINI}" "test -f ${SITE_DIR}/index.html" \
  && echo "[wiki] OK — ${SITE_DIR}/index.html in place" \
  || { echo "[wiki] FAIL — index.html missing"; exit 1; }

echo "[wiki] verify vhost (needs the Caddy wiki vhost live):"
echo "  curl --resolve wiki.tabaska.us:443:192.168.10.2 -so /dev/null -w '%{http_code}\\n' https://wiki.tabaska.us"
