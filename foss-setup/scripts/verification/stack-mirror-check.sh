#!/usr/bin/env bash
# stack-mirror-check.sh — repo↔live drift guard for the mini compose fleet
# (fix-41; classes M48 "live stack with no repo mirror", M49 "polluted image
# manifest", M51 "live .env keys missing from the repo example").
#
# Designed to run ON the mini FROM a fetched clone of home/homelab at origin/main
# HEAD (same pattern as wiki-drift-check.sh) so it always judges live state
# against what a rebuild would actually check out. Invoked by the `stack-mirror-
# drift` and `manifest-image-purity` checks in verification/checks.d/git-hygiene.yaml.
#
# Usage:  stack-mirror-check.sh mirrors|manifest
#
#   mirrors  — every live /opt/stacks/<name>/ that has a top-level compose file
#              must have configs/docker-stack/stacks/<name>/<same filename>
#              byte-identical in the repo, and (if the stack has a .env) every
#              live .env key must exist in the repo .env.example. One-way on
#              purpose: a live-only key is what a rebuild silently drops; an
#              example-only key is cosmetic.
#   manifest — the image NAME set in hosts/<host>/compose-images.txt must equal
#              the name set greped from live top-level compose files. Names, not
#              pins: pin bumps between weekly export runs are expected snapshot
#              lag, a name that exists nowhere live is pollution (phantom image,
#              .bak sweep-in) or a stale add/retire.
#
# Exit 0 + STACK-MIRRORS-OK / MANIFEST-PURITY-OK on success; exit 1 with one
# line per violation otherwise. Runbook: wiki/docs/runbooks/git-hygiene.md

set -euo pipefail

MODE="${1:?usage: stack-mirror-check.sh mirrors|manifest}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # …/foss-setup in the clone
STACKS_DIR="${STACKS_DIR:-/opt/stacks}"
MIRROR="${ROOT}/configs/docker-stack/stacks"
HOST="$(hostname -s)"
COMPOSE_NAMES=(compose.yaml compose.yml docker-compose.yml docker-compose.yaml)

env_keys() { grep -oE '^[A-Za-z_][A-Za-z0-9_]*=' "$1" 2>/dev/null | tr -d '=' | sort -u; }

live_compose_files() {
  find "${STACKS_DIR}" -mindepth 2 -maxdepth 2 \
       \( -name 'compose.yaml' -o -name 'compose.yml' \
          -o -name 'docker-compose.yml' -o -name 'docker-compose.yaml' \) 2>/dev/null | sort
}

fail=0

case "${MODE}" in
  mirrors)
    for d in "${STACKS_DIR}"/*/; do
      name="$(basename "$d")"
      compose=""
      for f in "${COMPOSE_NAMES[@]}"; do
        [[ -f "${d}${f}" ]] && { compose="$f"; break; }
      done
      [[ -z "$compose" ]] && continue          # data-only / retired dirs
      if [[ ! -f "${MIRROR}/${name}/${compose}" ]]; then
        echo "MIRROR-MISSING: ${name} (live ${compose} has no repo copy under configs/docker-stack/stacks/)"
        fail=1
        continue
      fi
      if ! cmp -s "${d}${compose}" "${MIRROR}/${name}/${compose}"; then
        echo "MIRROR-DRIFT: ${name}/${compose} differs from repo copy"
        fail=1
      fi
      if [[ -f "${d}.env" ]]; then
        if [[ ! -f "${MIRROR}/${name}/.env.example" ]]; then
          echo "ENV-EXAMPLE-MISSING: ${name} has a live .env but no repo .env.example"
          fail=1
        else
          missing="$(comm -23 <(env_keys "${d}.env") <(env_keys "${MIRROR}/${name}/.env.example") | xargs || true)"
          if [[ -n "${missing}" ]]; then
            echo "ENV-KEYS-UNMIRRORED: ${name} [${missing}] — a rebuild from the example would drop these"
            fail=1
          fi
        fi
      fi
    done
    [[ ${fail} -eq 0 ]] && echo "STACK-MIRRORS-OK"
    ;;
  manifest)
    manifest="${ROOT}/hosts/${HOST}/compose-images.txt"
    if [[ ! -f "${manifest}" ]]; then
      echo "MANIFEST-FILE-MISSING: ${manifest}"
      exit 1
    fi
    strip() { sed -E 's/[@:].*$//' | sort -u; }
    live_names="$(live_compose_files | xargs -r grep -hoE '^[[:space:]]*image:[[:space:]]*\S+' 2>/dev/null \
                    | sed -E 's/^[[:space:]]*image:[[:space:]]*//' | strip)"
    manifest_names="$(strip < "${manifest}")"
    only_manifest="$(comm -23 <(printf '%s\n' "${manifest_names}") <(printf '%s\n' "${live_names}") | xargs || true)"
    only_live="$(comm -13 <(printf '%s\n' "${manifest_names}") <(printf '%s\n' "${live_names}") | xargs || true)"
    if [[ -n "${only_manifest}" ]]; then
      echo "MANIFEST-PHANTOM-IMAGES: [${only_manifest}] in compose-images.txt but in no live top-level compose (pollution or a retired stack awaiting the weekly export)"
      fail=1
    fi
    if [[ -n "${only_live}" ]]; then
      echo "MANIFEST-MISSING-IMAGES: [${only_live}] live but absent from compose-images.txt (re-run export-manifests.sh + commit — 100%-coverage tripwire)"
      fail=1
    fi
    [[ ${fail} -eq 0 ]] && echo "MANIFEST-PURITY-OK"
    ;;
  *)
    echo "unknown mode: ${MODE}" >&2
    exit 2
    ;;
esac

exit ${fail}
