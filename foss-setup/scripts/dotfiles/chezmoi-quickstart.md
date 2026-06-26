# chezmoi quickstart — version-controlled dotfiles

> Goal: your shell, editor, and app configs live in one Git repo and apply to any
> machine with a single command. Survives a reinstall; consistent across your
> CachyOS rig, the Ubuntu box, and the Mac mini.

**Why chezmoi (vs. the alternatives):**
- **bare git repo** (`git --git-dir=$HOME/.dotfiles`): clever, zero-dependency,
  but error-prone (easy to accidentally add `$HOME`), no templating, no secrets.
- **GNU Stow**: pure symlink farm. Fine for one machine; no per-host differences,
  no secrets, no templating.
- **chezmoi** *(recommended)*: single static binary, one-command bootstrap on a
  fresh box, **templating** (one source → per-host output), and **built-in
  secrets** (age/gpg encryption + password-manager integration). Best fit for
  cross-machine + the set-and-forget priority.

Official docs: <https://www.chezmoi.io/> · install <https://www.chezmoi.io/install/>
· quick start <https://www.chezmoi.io/quick-start/>

---

## Mental model (read this once)

- **Source dir** `~/.local/share/chezmoi` — a normal Git repo; the *desired
  state* of your dotfiles.
- **Destination** `$HOME` — chezmoi makes the minimum changes so your home
  matches the source.
- `chezmoi apply` computes the diff and applies it. `chezmoi diff` previews it.
- Files are renamed in the source (e.g. `~/.zshrc` → `dot_zshrc`); chezmoi
  translates. You rarely touch the source filenames directly — use `chezmoi edit`.

---

## First machine (start from your existing configs)

```bash
# 1. Install + initialize an empty source repo
chezmoi init

# 2. Add the dotfiles you care about (chezmoi copies them into the source repo)
chezmoi add ~/.zshrc
chezmoi add ~/.config/nvim
chezmoi add ~/.gitconfig
chezmoi add ~/.config/kitty/kitty.conf   # whatever you actually use

# 3. Push the source repo to Forgejo (self-hosted) or a private GitHub repo
chezmoi cd                                # drops you into the source dir
git remote add origin git@codeberg.org:you/dotfiles.git   # or your Forgejo URL
git add -A && git commit -m "initial dotfiles"
git push -u origin main
exit
```

> Host it on your **Forgejo** instance (`configs/git/`) or a **private GitHub
> repo** — same config-as-code habit as your compose files.

---

## Any other machine (the one-liner)

If chezmoi is installed:

```bash
chezmoi init --apply git@codeberg.org:you/dotfiles.git
# GitHub shorthand if the repo is literally named "dotfiles":
chezmoi init --apply <github-username>
```

Brand-new machine without chezmoi — install + clone + apply in one shot:

```bash
sh -c "$(curl -fsLS https://get.chezmoi.io)" -- init --apply git@github.com:you/dotfiles.git
```

…or just use the wrapper in this folder (installs chezmoi if missing, idempotent):

```bash
DOTFILES_REPO=git@codeberg.org:you/dotfiles.git ./bootstrap-dotfiles.sh
# Cautious first run — clone but don't touch $HOME until you've reviewed:
DOTFILES_REPO=you CHEZMOI_NO_APPLY=1 ./bootstrap-dotfiles.sh
chezmoi diff      # review
chezmoi apply     # commit to it
```

---

## Day-to-day

```bash
chezmoi edit ~/.zshrc     # edit the source-managed version
chezmoi diff              # see what would change in $HOME
chezmoi apply             # apply changes
chezmoi cd                # go to source repo to commit + push
chezmoi update            # git pull the source repo, then apply (use on every box)
chezmoi managed           # list everything chezmoi controls
chezmoi re-add            # pull manual edits made directly in $HOME back into source
```

Typical loop: `chezmoi edit` → `chezmoi apply` → `chezmoi cd` → `git commit && git
push`. On your other machines: `chezmoi update`.

---

## Per-machine differences (templating)

One source, different output per host — no more divergent copies. chezmoi exposes
`.chezmoi.hostname`, `.chezmoi.os`, etc. Example `dot_gitconfig.tmpl`:

```gotmpl
[user]
    name = Brandon
{{- if eq .chezmoi.hostname "cachyos-rig" }}
    email = personal@example.com
{{- else }}
    email = work@example.com
{{- end }}
```

`chezmoi apply` renders the right branch on each box.

---

## Secrets (don't commit plaintext)

chezmoi handles secrets so they can live in (or alongside) your repo safely.

**Option A — age encryption (simple, recommended).** Generate a key once, store
the *private* key in Proton Pass:

```bash
age-keygen -o ~/.config/chezmoi/key.txt   # back up this key to Proton Pass!
```

Add to `~/.config/chezmoi/chezmoi.toml`:

```toml
encryption = "age"
[age]
    identity = "~/.config/chezmoi/key.txt"
    recipient = "age1...your-public-key..."
```

Then encrypt a secret file into the source repo (safe to push):

```bash
chezmoi add --encrypt ~/.ssh/id_ed25519
```

**Option B — password-manager template functions.** Pull secrets at apply-time
instead of storing them. chezmoi has built-ins for Bitwarden, 1Password, pass,
KeePassXC, etc. Example pulling from `pass`:

```gotmpl
github_token = {{ (output "pass" "tokens/github") | trim }}
```

> Rule: the **age private key** (or your password-manager vault) is the one thing
> that lives *only* in Proton Pass, never in Git. With it, a fresh clone fully
> re-hydrates; without it, the encrypted blobs are useless to a thief.

---

## Rebuild drill

On a wiped machine, your entire personal environment comes back with:

```bash
# 1. (if needed) restore the age key from Proton Pass to ~/.config/chezmoi/key.txt
# 2. one command:
sh -c "$(curl -fsLS https://get.chezmoi.io)" -- init --apply git@codeberg.org:you/dotfiles.git
```

That's the dotfiles half of "rebuild in an hour." The compose/services half is
`configs/git/repo-structure.md`.
