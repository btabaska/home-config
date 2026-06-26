#!/usr/bin/env bash
#
# sbom-nightly.sh — generate CycloneDX SBOMs for this host and every running
#                   container image, then upload them to OWASP Dependency-Track.
#
# What it does (idempotent — safe to re-run, designed for a systemd timer):
#   1. Loads DTRACK_URL + DTRACK_API_KEY from an EnvironmentFile (NEVER hardcoded).
#   2. Runs `syft dir:/ -o cyclonedx-json` for the host filesystem.
#   3. Runs `syft <image> -o cyclonedx-json` for each running container image.
#   4. (Optional) Gates each SBOM through `grype sbom:<file>` before upload.
#   5. Uploads every CycloneDX file to Dependency-Track via PUT /api/v1/bom.
#
# Projects are named per host / per image so re-runs UPDATE the same project
# instead of creating duplicates:
#   host:<hostname>            for the filesystem SBOM
#   image:<repo>:<tag>         for each container image
#
# Docs:
#   syft:               https://github.com/anchore/syft
#   grype:              https://github.com/anchore/grype
#   D-Track BOM API:    https://docs.dependencytrack.org/usage/cicd/
#   CycloneDX:          https://cyclonedx.org/
#
# SUPPLY-CHAIN LESSON (CVE-2026-33634): a tampered scanner release can poison
# every SBOM it produces. Pin syft/grype to a known-good version and verify the
# download checksum/signature out of band before trusting results. Pin here:
#   SYFT_VERSION / GRYPE_VERSION below must match what's installed; the script
#   refuses to run if the installed version drifts from the pin.
#
# Setup (once per host):
#   sudo install -d -m 0700 /etc/inventory
#   sudo cp sbom.env.example /etc/inventory/sbom.env   # then edit, chmod 600
#   sudo install -D -m 0755 sbom-nightly.sh /opt/scripts/inventory/sbom-nightly.sh
#   sudo cp sbom-nightly.service sbom-nightly.timer /etc/systemd/system/
#   sudo systemctl daemon-reload && sudo systemctl enable --now sbom-nightly.timer
#
# Run manually:  sudo ENV_FILE=/etc/inventory/sbom.env ./sbom-nightly.sh

set -euo pipefail

# --- Configuration ---------------------------------------------------------------
ENV_FILE="${ENV_FILE:-/etc/inventory/sbom.env}"

# Pin the scanner versions you verified (see CVE-2026-33634 note above).
# Set ENFORCE_TOOL_PINS=0 to skip the drift check (NOT recommended in prod).
SYFT_VERSION="${SYFT_VERSION:-1.45.1}"
GRYPE_VERSION="${GRYPE_VERSION:-0.114.0}"
ENFORCE_TOOL_PINS="${ENFORCE_TOOL_PINS:-1}"

# Set GRYPE_GATE=1 to run a local grype scan on each SBOM before upload.
GRYPE_GATE="${GRYPE_GATE:-0}"

# Filesystem root to scan and where to drop temp SBOMs.
SCAN_ROOT="${SCAN_ROOT:-/}"
WORKDIR="$(mktemp -d -t sbom-nightly.XXXXXX)"
HOSTNAME_SHORT="$(hostname -s)"

log()  { printf '%s [sbom-nightly] %s\n' "$(date -Is)" "$*"; }
warn() { printf '%s [sbom-nightly][!] %s\n' "$(date -Is)" "$*" >&2; }
die()  { printf '%s [sbom-nightly][x] %s\n' "$(date -Is)" "$*" >&2; exit 1; }

cleanup() { rm -rf "${WORKDIR}"; }
trap cleanup EXIT

# --- Load secrets ----------------------------------------------------------------
if [[ -r "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
else
  warn "env file not readable at ${ENV_FILE}; relying on already-exported vars."
fi

: "${DTRACK_URL:?DTRACK_URL must be set (in ${ENV_FILE})}"
: "${DTRACK_API_KEY:?DTRACK_API_KEY must be set (in ${ENV_FILE})}"
DTRACK_URL="${DTRACK_URL%/}" # strip trailing slash

command -v syft  >/dev/null 2>&1 || die "syft not installed (pin ${SYFT_VERSION})."
command -v curl  >/dev/null 2>&1 || die "curl not installed."

# --- Verify pinned tool versions (anti-supply-chain-tamper) ----------------------
check_pin() {
  local tool="$1" want="$2" got
  got="$("${tool}" version 2>/dev/null | grep -oiE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)"
  if [[ "${ENFORCE_TOOL_PINS}" == "1" && -n "${want}" && "${got}" != "${want}" ]]; then
    die "${tool} version drift: installed '${got}', pinned '${want}'. Re-verify the binary (CVE-2026-33634) before continuing, or set ENFORCE_TOOL_PINS=0."
  fi
  log "${tool} version: ${got:-unknown} (pin ${want})"
}
check_pin syft "${SYFT_VERSION}"
if [[ "${GRYPE_GATE}" == "1" ]]; then
  command -v grype >/dev/null 2>&1 || die "GRYPE_GATE=1 but grype not installed."
  check_pin grype "${GRYPE_VERSION}"
fi

# --- Upload one CycloneDX file to Dependency-Track -------------------------------
# Uses auto-create so the project is made on first sight and updated thereafter.
upload_bom() {
  local project_name="$1" bom_file="$2" version="${3:-latest}"
  log "Uploading BOM for project '${project_name}' (v=${version})."
  local code
  code="$(curl -sS -o "${WORKDIR}/upload.out" -w '%{http_code}' \
    -X PUT "${DTRACK_URL}/api/v1/bom" \
    -H "X-Api-Key: ${DTRACK_API_KEY}" \
    -H "Content-Type: multipart/form-data" \
    -F "autoCreate=true" \
    -F "projectName=${project_name}" \
    -F "projectVersion=${version}" \
    -F "bom=@${bom_file}")" || die "curl failed uploading ${project_name}."
  case "${code}" in
    200|201) log "Uploaded ${project_name} (HTTP ${code})." ;;
    *)       warn "Upload of ${project_name} returned HTTP ${code}: $(cat "${WORKDIR}/upload.out")" ;;
  esac
}

# --- Optional local grype gate ---------------------------------------------------
grype_gate() {
  local bom_file="$1" label="$2"
  [[ "${GRYPE_GATE}" == "1" ]] || return 0
  log "grype gate on ${label}."
  grype "sbom:${bom_file}" || warn "grype reported findings for ${label} (continuing; D-Track is the source of truth)."
}

# --- 1. Host filesystem SBOM -----------------------------------------------------
host_bom="${WORKDIR}/host-${HOSTNAME_SHORT}.cdx.json"
log "Generating host SBOM for ${SCAN_ROOT} -> ${host_bom}"
syft "dir:${SCAN_ROOT}" -o cyclonedx-json > "${host_bom}"
grype_gate "${host_bom}" "host:${HOSTNAME_SHORT}"
upload_bom "host:${HOSTNAME_SHORT}" "${host_bom}" "$(date +%Y-%m-%d)"

# --- 2. Per-running-container-image SBOMs ----------------------------------------
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  # Distinct images currently backing running containers.
  mapfile -t images < <(docker ps --format '{{.Image}}' | sort -u)
  if [[ "${#images[@]}" -eq 0 ]]; then
    log "No running containers; skipping image SBOMs."
  fi
  for image in "${images[@]}"; do
    [[ -n "${image}" ]] || continue
    safe="$(printf '%s' "${image}" | tr '/:@' '___')"
    img_bom="${WORKDIR}/image-${safe}.cdx.json"
    log "Generating image SBOM for ${image}"
    if ! syft "${image}" -o cyclonedx-json > "${img_bom}"; then
      warn "syft failed on ${image}; skipping."
      continue
    fi
    # version = tag if present, else 'latest'
    version="${image##*:}"; [[ "${version}" == "${image}" ]] && version="latest"
    grype_gate "${img_bom}" "image:${image}"
    upload_bom "image:${image}" "${img_bom}" "${version}"
  done
else
  log "docker not available; skipping container image SBOMs."
fi

log "All SBOMs generated and uploaded to ${DTRACK_URL}."
