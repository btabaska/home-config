#!/usr/bin/env bash
#
# bootstrap-dotfiles.sh
# One-shot, idempotent dotfiles bootstrap using chezmoi.
#
# chezmoi is the recommended dotfile manager here over the bare-git-repo method
# and GNU Stow: it does cross-machine templating (per-host differences from one
# source), built-in secret handling (age/gpg + password-manager integration),
# and `init --apply` from a single URL on a brand-new machine. The bare-repo
# trick is clever but fragile; Stow only symlinks (no templating, no secrets).
#
# What this does, safely re-runnable:
#   1. Install chezmoi if it's missing (distro package manager, else official
#      installer to ~/.local/bin).
#   2. `chezmoi init` from your dotfiles repo (only if not already initialized).
#   3. `chezmoi apply` to bring $HOME to the desired state.
#
# Docs:
#   - Install:     https://www.chezmoi.io/install/
#   - Quick start: https://www.chezmoi.io/quick-start/
#   - Setup guide: https://www.chezmoi.io/user-guide/setup/
#
# Usage:
#   DOTFILES_REPO=git@codeberg.org:you/dotfiles.git ./bootstrap-dotfiles.sh
#   DOTFILES_REPO=https://github.com/you/dotfiles.git ./bootstrap-dotfiles.sh
#   DOTFILES_REPO=you ./bootstrap-dotfiles.sh        # GitHub user shorthand
#
# Optional env:
#   DOTFILES_BRANCH=main        # checkout a specific branch
#   CHEZMOI_NO_APPLY=1          # init only, review with `chezmoi diff` first
set -euo pipefail

DOTFILES_REPO="${DOTFILES_REPO:-}"
DOTFILES_BRANCH="${DOTFILES_BRANCH:-}"
CHEZMOI_NO_APPLY="${CHEZMOI_NO_APPLY:-0}"
BIN_DIR="${HOME}/.local/bin"

log()  { printf '\033[1;36m[dotfiles]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[dotfiles][!]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[dotfiles][x]\033[0m %s\n' "$*" >&2; exit 1; }

# Resolve the chezmoi binary even if it was just installed to ~/.local/bin and
# that dir isn't on PATH yet in this shell.
chezmoi_bin() {
  if command -v chezmoi >/dev/null 2>&1; then
    command -v chezmoi
  elif [[ -x "${BIN_DIR}/chezmoi" ]]; then
    printf '%s\n' "${BIN_DIR}/chezmoi"
  else
    return 1
  fi
}

install_chezmoi() {
  if chezmoi_bin >/dev/null 2>&1; then
    log "chezmoi already installed: $("$(chezmoi_bin)" --version | head -1)"
    return 0
  fi

  log "chezmoi not found; installing."
  # Prefer the native package manager so updates ride along with the system.
  if command -v pacman >/dev/null 2>&1; then
    log "Installing via pacman (Arch/CachyOS)."
    sudo pacman -S --needed --noconfirm chezmoi
  elif command -v apt-get >/dev/null 2>&1 && apt-cache show chezmoi >/dev/null 2>&1; then
    log "Installing via apt."
    sudo apt-get update -y && sudo apt-get install -y chezmoi
  elif command -v brew >/dev/null 2>&1; then
    log "Installing via Homebrew."
    brew install chezmoi
  else
    # Fallback: official installer drops a static binary in ~/.local/bin.
    log "Using official installer -> ${BIN_DIR}"
    mkdir -p "${BIN_DIR}"
    sh -c "$(curl -fsLS https://get.chezmoi.io)" -- -b "${BIN_DIR}"
  fi

  chezmoi_bin >/dev/null 2>&1 || die "chezmoi install failed; not on PATH or ${BIN_DIR}."
  log "Installed chezmoi: $("$(chezmoi_bin)" --version | head -1)"
}

init_and_apply() {
  local cz; cz="$(chezmoi_bin)"
  local src; src="$("${cz}" source-path 2>/dev/null || true)"

  # Already initialized? (source dir exists and is a git repo). Just pull+apply.
  if [[ -n "${src}" && -d "${src}/.git" ]]; then
    log "chezmoi already initialized at ${src}; updating."
    "${cz}" update --verbose || warn "chezmoi update hit an issue; continuing to apply."
    if [[ "${CHEZMOI_NO_APPLY}" != "1" ]]; then
      "${cz}" apply --verbose
    fi
    return 0
  fi

  [[ -n "${DOTFILES_REPO}" ]] || die "Set DOTFILES_REPO to your dotfiles repo URL (or GitHub username). See header."

  local -a init_args=(init "${DOTFILES_REPO}")
  [[ -n "${DOTFILES_BRANCH}" ]] && init_args+=(--branch "${DOTFILES_BRANCH}")

  if [[ "${CHEZMOI_NO_APPLY}" == "1" ]]; then
    log "init only (CHEZMOI_NO_APPLY=1): cloning ${DOTFILES_REPO}, NOT applying."
    "${cz}" "${init_args[@]}" --verbose
    warn "Review with: chezmoi diff   then apply with: chezmoi apply"
  else
    log "init + apply from ${DOTFILES_REPO}"
    "${cz}" "${init_args[@]}" --apply --verbose
  fi
}

main() {
  install_chezmoi
  init_and_apply
  log "Done. Manage from here with: chezmoi edit <file> / chezmoi apply / chezmoi update"
  case ":${PATH}:" in
    *":${BIN_DIR}:"*) ;;
    *) warn "Add ${BIN_DIR} to PATH if chezmoi was installed there (e.g. in your shell rc).";;
  esac
}

main "$@"
