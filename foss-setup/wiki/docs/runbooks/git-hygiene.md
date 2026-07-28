# Git hygiene & repo↔live drift (mini)

Checks in `verification/checks.d/git-hygiene.yaml`. They all guard the same
invariant, the one CLAUDE.md states first: **a fix that changes a live host but
not the repo (or vice-versa) creates drift** — and a later rebuild/redeploy
silently reverts it. The 2026-07-16 quality gate found four flavors of this
(M48–M51, remediated by fix-41); these checks keep them from coming back.

## The checks

| check | red means |
|---|---|
| `git-stacks-clean` | `/opt/stacks` (its own git repo → forgejo `home/docker-stacks`) has uncommitted changes |
| `git-foss-setup-clean` | the `home/homelab` clone at `/opt/foss-setup` has uncommitted changes (usually un-committed weekly manifest output) |
| `git-etckeeper-clean` | `/etc` drifted without an etckeeper commit |
| `wiki-drift` | a generated wiki page's source changed without regenerating the page in the same commit ("same-commit rule", wiki-05) |
| `stack-mirror-drift` | a live mini stack's top-level compose has **no repo mirror**, differs from it byte-wise, or its live `.env` holds keys the repo `.env.example` lacks |
| `manifest-image-purity` | `hosts/macmini/compose-images.txt` lists an image name no live top-level compose pins (phantom/pollution), or a live image name is missing from it |
| `tracker-integrity` | the tracker JSON **sources** are incoherent: an orphan status id, a duplicate task id, a contradictory status combo, or the retired `_meta` count fields crept back (M46 class) |

`stack-mirror-drift` and `manifest-image-purity` judge live state against a
fetched clone of `origin/main` HEAD (cache: `/var/lib/verification/wiki-drift-repo`,
shared with `wiki-drift`; each check `fetch` + `reset --hard`s it first), running
`scripts/verification/stack-mirror-check.sh` from **inside that clone** so the
logic self-updates with the repo.

## Fixing `stack-mirror-drift`

- **`MIRROR-MISSING: <name>`** — a stack was deployed to `/opt/stacks/<name>/`
  without a repo copy. Mirror the compose file (same filename!) to
  `configs/docker-stack/stacks/<name>/`, add a redacted `.env.example`, commit,
  `publish-deploy.sh`. This is exactly how forgejo — the deploy control plane
  itself — went unrebuildable-looking for weeks (M48: its mirror sat unfound in
  `configs/git/`, a path nothing else used; fix-41 folded it into `stacks/`).
  One deliberate exception: the mini's live `/opt/stacks/syncthing` (mesh node,
  foss-03) mirrors to `configs/docker-stack/stacks/syncthing-node/`, not
  `.../syncthing/`, so `gen-wiki-services.py` (keys pages by dir name, mini-tree
  first) doesn't let the node shadow the separate NAS-hub `syncthing` page. The
  check carries a `MIRROR_RENAME` map (`syncthing`→`syncthing-node`) for this one
  case; the mirrored compose stays byte-identical to live (glue-15).
- **`MIRROR-DRIFT: <name>`** — live compose edited without mirroring back (or a
  repo change never deployed). Diff them, decide which side is truth (live wins
  per the standing mandate unless it's an undeployed hardening), sync, commit.
- **`ENV-KEYS-UNMIRRORED: <name> [KEYS]`** — keys added to the live `.env` but
  not the example. Add them (names + safe defaults/comments, never real
  values). One-way on purpose: this is the rebuild-loses-config direction (M51 —
  caddy `ACME_EMAIL`, musicseerr `LIDARR_API_KEY`, navidrome `ND_BACKUP_*`,
  ntfy `NTFY_UPSTREAM_BASE_URL`). Fun root cause from the M51 batch: caddy's
  example lost its `ACME_EMAIL=` line to a docs page's Cloudflare
  email-obfuscation artifact — the file literally contained `[email protected]`.

## Fixing `manifest-image-purity`

- **`MANIFEST-PHANTOM-IMAGES`** — an image name in the manifest matches no live
  top-level compose. Historically: `export-manifests.sh` used to grep `image:`
  **recursively** across `/opt/stacks`, sweeping in a `compose.yaml.bak-*`
  (whose stale pin was a docker image *ID* mis-written as a digest — unpullable)
  plus 4 hotio images from recyclarr's embedded trash-guides clone (M49). The
  script now only reads each stack's own top-level compose; if this fires today
  it's either fresh pollution or a stack was retired without re-running the
  export.
- **`MANIFEST-MISSING-IMAGES`** — a stack/image went live without the manifest
  catching up. Re-run the export now (don't wait for Monday):
  `ssh mini sudo systemctl start export-manifests.service`, then commit the
  regenerated `hosts/macmini/` + `configs/inventory/inventory.md` in the mini
  clone (`/opt/foss-setup`) and push — the 100%-coverage tripwire says manifests
  update with **every** deploy/retire.

The weekly export itself is dead-man-monitored: healthchecks
`export-manifests-mini` (7d period + 24h grace) is pinged by the unit's
`ExecStartPost` only on success, and the script pings ntfy topic `verification`
on failure. A silently-dead timer or a failing run both page.

## Fixing the clean-tree checks

`git-stacks-clean` / `git-foss-setup-clean` / `git-etckeeper-clean`: ssh in,
`git status`, then either commit+push the intentional change (as `btabaska`,
not root — root has no forgejo ssh alias) or revert the accident. Expect
intentional short-lived drift while a concurrent agent session is mid-task.

For `wiki-drift` see the same-commit rule note in
[`verification.md`](verification.md): re-run the generators
(`gen-wiki-services.py`, `gen-roadmap-pages.py`, `gen-script-pages.py`,
`gen-todo.py`) and commit the regenerated pages with their source change.

## fix-43 · repo junk & dead paths

| check | what failing means | fix |
|---|---|---|
| `repo-tracked-ignored` | A file matching `.gitignore` is committed in the index — hidden from `git status` but shipped in every clone (the L68 `__pycache__` class) | `git ls-files -i -c --exclude-standard` to list, then `git rm --cached <file>` and commit |
| `tracker-count-sanity` | Generated tracker views disagree with `tasks.json`/`progress.json`: summary arithmetic broken, page stale, or a negative Open cell (L77) | Re-run `gen-todo.py` + `gen-roadmap-pages.py` and commit with the JSON change. Statuses are exclusive in the generators — retired wins over done for dual-status tasks (sbom-01/04) |
| `unit-file-drift` | A deployed hand-copied unit differs from its repo source: the `ansible-pull` units on mini + rig (`configs/ansible/`), or the rig's other static foss-setup host units (glue-13 — `gpu-power-tune.service`, the `export-manifests` service+timer; canonical sources mapped in `configs/host/rig/README.md`). Nothing converges these automatically, so drift is silent until a run misses (L6/L86) | Copy the repo file onto the drifted host (`/etc/systemd/system/`) + `systemctl daemon-reload`; or, if the live edit was the intentional one, land it in the repo instead |

## glue-04b · chezmoi dotfiles drift (rig + mini)

The personal terminal stack (Ghostty + Starship + zsh, `home/dotfiles`) is
chezmoi-managed and rolled out to **rig** and **mini** (glue-04b). Same
repo↔live invariant as the stacks above, one plane down: a live edit to
`~/.zshrc` / `~/.config/starship.toml` / `~/.config/ghostty/config` /
`~/.config/fish/config.fish` that never lands back in the source — or a source
update never `chezmoi apply`ed on a host — is silent drift.

| check | red means | fix |
|---|---|---|
| `dotfiles-content-clean` | A chezmoi-managed dotfile on mini or rig has **content** drift vs its applied source (the runner reaches rig over the shared cross-host ssh key; an unreachable rig also reds it) | On the drifted host: `chezmoi diff` to see it, then `chezmoi apply` (source is truth) or `chezmoi edit <file> && chezmoi apply && chezmoi cd && git push` + `chezmoi update` elsewhere (live edit is truth). Then re-run the check |

**Why content, not `chezmoi status`:** chezmoi derives a `dot_`-file's target
mode from the *runtime umask*. mini's login shells run `umask 002`
(group-writable) but the systemd verification runner defaults to `022`, so a
plain `chezmoi status` flaps 0↔7 on cosmetic mode bits alone and would page a
fake drift. The check counts real content hunks (`chezmoi diff | grep -c '^@@'`;
mode-only diffs carry no `@@` hunk) — umask-agnostic and uniform across both
hosts. The Linux `.chezmoiignore` OS-guard means only the terminal stack is
managed on these hosts; `~/.ssh/config`, `~/.gitconfig`, and nvim are never
touched.

## fix-44 · tracker source coherence

| check | what failing means | fix |
|---|---|---|
| `tracker-integrity` | The tracker JSON **sources** are incoherent (as opposed to `tracker-count-sanity`, which checks the generated *views*): an id in `progress.json` `done`/`retired`/`deferred`/`reopened` has no definition in `tasks.json` (the M46 `nas-00e` orphan class), a task id is defined twice, an id is both deferred and done/retired, or `_meta.task_count`/`completed_count` reappeared | Every status id must resolve: either add the missing task definition to `tasks.json` (what fix-44 did for `nas-00e` — the work was real, the definition was never written) or remove the bogus status key. The `_meta` count fields stay **dead**: they had no code consumer since the HTML tracker retired (f1bb884) and drifted every session (234/172 vs a reality of 269/188 when caught) — the generated `todo.md` + wiki roadmap are the only published counts. After any tracker JSON edit: `gen-todo.py` + `gen-roadmap-pages.py`, same commit |

Script: `scripts/verification/tracker-integrity.py`, run daily from the fetched
`origin/main` cache clone like its siblings. Monitoring: fails page via the
sweep's ntfy `verification` route; the sweep itself is dead-man-monitored
(healthchecks `verification-mini`), so a silently-dead runner also pages.
