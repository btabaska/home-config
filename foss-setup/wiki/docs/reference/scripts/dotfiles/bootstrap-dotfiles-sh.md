# `bootstrap-dotfiles.sh`

> bootstrap-dotfiles.sh

**Path:** `foss-setup/scripts/dotfiles/bootstrap-dotfiles.sh` · **Category:** [Dotfiles](index.md) · **Type:** Bash

## What it does

```text
 bootstrap-dotfiles.sh
 One-shot, idempotent dotfiles bootstrap using chezmoi.

 chezmoi is the recommended dotfile manager here over the bare-git-repo method
 and GNU Stow: it does cross-machine templating (per-host differences from one
 source), built-in secret handling (age/gpg + password-manager integration),
 and `init --apply` from a single URL on a brand-new machine. The bare-repo
 trick is clever but fragile; Stow only symlinks (no templating, no secrets).

 What this does, safely re-runnable:
   1. Install chezmoi if it's missing (distro package manager, else official
      installer to ~/.local/bin).
   2. `chezmoi init` from your dotfiles repo (only if not already initialized).
   3. `chezmoi apply` to bring $HOME to the desired state.

 Docs:
   - Install:     https://www.chezmoi.io/install/
   - Quick start: https://www.chezmoi.io/quick-start/
   - Setup guide: https://www.chezmoi.io/user-guide/setup/

 Usage:
   DOTFILES_REPO=git@codeberg.org:you/dotfiles.git ./bootstrap-dotfiles.sh
   DOTFILES_REPO=https://github.com/you/dotfiles.git ./bootstrap-dotfiles.sh
   DOTFILES_REPO=you ./bootstrap-dotfiles.sh        # GitHub user shorthand

 Optional env:
   DOTFILES_BRANCH=main        # checkout a specific branch
   CHEZMOI_NO_APPLY=1          # init only, review with `chezmoi diff` first
```

## Environment / variables referenced

`BIN_DIR`, `CHEZMOI_NO_APPLY`, `DOTFILES_BRANCH`, `DOTFILES_REPO`

## See also

- [Dotfiles scripts](index.md) · [All scripts](../index.md)
