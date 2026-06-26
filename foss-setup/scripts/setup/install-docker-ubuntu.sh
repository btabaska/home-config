#!/usr/bin/env bash
#
# install-docker-ubuntu.sh
# Idempotent install of Docker Engine + Compose plugin on Ubuntu Server,
# following the official Docker apt-repository method.
#
# Docs: https://docs.docker.com/engine/install/ubuntu/
#       https://docs.docker.com/engine/install/linux-postinstall/
#
# Safe to re-run: it skips steps already satisfied. Run with sudo (or as root).
#
#   sudo ./install-docker-ubuntu.sh
#
set -euo pipefail

readonly DOCKER_GPG="/etc/apt/keyrings/docker.asc"
readonly DOCKER_LIST="/etc/apt/sources.list.d/docker.list"

log()  { printf '\033[1;32m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    die "Run as root or with sudo (e.g. 'sudo $0')."
  fi
}

check_ubuntu() {
  [[ -r /etc/os-release ]] || die "Cannot read /etc/os-release; unsupported OS."
  # shellcheck disable=SC1091
  . /etc/os-release
  if [[ "${ID:-}" != "ubuntu" ]]; then
    warn "Detected ID='${ID:-unknown}', not 'ubuntu'. Continuing anyway (Debian-like assumed)."
  fi
  log "Target: ${PRETTY_NAME:-unknown} (codename: ${VERSION_CODENAME:-unknown})"
}

remove_conflicting() {
  # Old/unofficial packages that conflict with Docker CE. Removal is best-effort.
  local pkgs=(docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc)
  local found=()
  local p
  for p in "${pkgs[@]}"; do
    if dpkg -s "${p}" >/dev/null 2>&1; then
      found+=("${p}")
    fi
  done
  if [[ "${#found[@]}" -gt 0 ]]; then
    log "Removing conflicting packages: ${found[*]}"
    apt-get remove -y "${found[@]}" || warn "Could not remove some conflicting packages; continuing."
  else
    log "No conflicting legacy packages found."
  fi
}

setup_repo() {
  log "Installing prerequisites (ca-certificates, curl)."
  apt-get update -y
  apt-get install -y ca-certificates curl

  install -m 0755 -d /etc/apt/keyrings

  if [[ ! -s "${DOCKER_GPG}" ]]; then
    log "Fetching Docker GPG key."
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o "${DOCKER_GPG}"
    chmod a+r "${DOCKER_GPG}"
  else
    log "Docker GPG key already present."
  fi

  # shellcheck disable=SC1091
  . /etc/os-release
  local arch codename
  arch="$(dpkg --print-architecture)"
  # UBUNTU_CODENAME is correct even on derivatives; fall back to VERSION_CODENAME.
  codename="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"
  [[ -n "${codename}" ]] || die "Could not determine Ubuntu codename."

  local repo_line="deb [arch=${arch} signed-by=${DOCKER_GPG}] https://download.docker.com/linux/ubuntu ${codename} stable"
  if [[ ! -f "${DOCKER_LIST}" ]] || ! grep -qxF "${repo_line}" "${DOCKER_LIST}" 2>/dev/null; then
    log "Writing Docker apt repository for '${codename}'."
    printf '%s\n' "${repo_line}" >"${DOCKER_LIST}"
  else
    log "Docker apt repository already configured."
  fi

  apt-get update -y
}

install_docker() {
  log "Installing Docker Engine, CLI, containerd, Buildx and Compose plugin."
  apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin
}

enable_service() {
  log "Enabling and starting the docker service."
  systemctl enable --now docker
}

add_user_to_group() {
  # Add the invoking (non-root) user to the 'docker' group so they can run docker
  # without sudo. Takes effect on next login / `newgrp docker`.
  local target="${SUDO_USER:-}"
  if [[ -z "${target}" || "${target}" == "root" ]]; then
    warn "No non-root SUDO_USER detected; skipping docker group setup."
    return 0
  fi
  if ! getent group docker >/dev/null 2>&1; then
    groupadd docker
  fi
  if id -nG "${target}" | tr ' ' '\n' | grep -qx docker; then
    log "User '${target}' is already in the docker group."
  else
    log "Adding user '${target}' to the docker group."
    usermod -aG docker "${target}"
    warn "Log out and back in (or run 'newgrp docker') for group changes to apply."
  fi
}

verify() {
  log "Verifying installation."
  docker --version
  docker compose version
  log "Docker Engine + Compose plugin are installed."
  warn "If port 53 will be used by AdGuard/Pi-hole, free systemd-resolved's stub first:"
  warn "  sudo sed -i 's/^#\\?DNSStubListener=.*/DNSStubListener=no/' /etc/systemd/resolved.conf"
  warn "  sudo ln -sf /run/systemd/resolve/resolv.conf /etc/resolv.conf && sudo systemctl restart systemd-resolved"
}

main() {
  require_root
  check_ubuntu
  remove_conflicting
  setup_repo
  install_docker
  enable_service
  add_user_to_group
  verify
}

main "$@"
