# Checks — git-hygiene

`foss-setup/verification/checks.d/git-hygiene.yaml` — 15 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `git-stacks-clean`

/opt/stacks working tree is clean

- **host:** `mini` · **severity:** `warn` · **guards task:** `docker-12` · **enabled:** True
- **expects:** `^0$`

```bash
sudo git -C /opt/stacks status --porcelain | wc -l
```

## `git-foss-setup-clean`

/opt/foss-setup working tree is clean

- **host:** `mini` · **severity:** `warn` · **guards task:** `glue-08` · **enabled:** True
- **expects:** `^0$`

```bash
sudo git -C /opt/foss-setup status --porcelain | wc -l
```

## `git-etckeeper-clean`

/etc committed in etckeeper (no uncommitted drift)

- **host:** `mini` · **severity:** `warn` · **guards task:** `glue-01` · **enabled:** True
- **expects:** `1`

```bash
sudo etckeeper unclean
```

## `wiki-drift`

wiki generated pages in sync with sources (same-commit rule)

- **host:** `mini` · **severity:** `warn` · **guards task:** `wiki-05` · **enabled:** True
- **expects:** `0`

```bash
D=/var/lib/verification/wiki-drift-repo; { git -C "$D" rev-parse --git-dir >/dev/null 2>&1 || { rm -rf "$D"; git clone -q forgejo:home/homelab "$D"; }; } && git -C "$D" fetch -q origin main && git -C "$D" reset --hard -q FETCH_HEAD && git -C "$D" worktree prune 2>/dev/null && bash "$D/foss-setup/scripts/wiki/wiki-drift-check.sh"
```

## `stack-mirror-drift`

every live mini stack byte-mirrored in repo (+ .env keys in example)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-41` · **enabled:** True
- **expects:** `STACK-MIRRORS-OK`

```bash
D=/var/lib/verification/wiki-drift-repo; { git -C "$D" rev-parse --git-dir >/dev/null 2>&1 || { rm -rf "$D"; git clone -q forgejo:home/homelab "$D"; }; } && git -C "$D" fetch -q origin main && git -C "$D" reset --hard -q FETCH_HEAD && sudo bash "$D/foss-setup/scripts/verification/stack-mirror-check.sh" mirrors
```

## `manifest-image-purity`

compose-images.txt image names == live top-level compose image names

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-41` · **enabled:** True
- **expects:** `MANIFEST-PURITY-OK`

```bash
D=/var/lib/verification/wiki-drift-repo; { git -C "$D" rev-parse --git-dir >/dev/null 2>&1 || { rm -rf "$D"; git clone -q forgejo:home/homelab "$D"; }; } && git -C "$D" fetch -q origin main && git -C "$D" reset --hard -q FETCH_HEAD && sudo bash "$D/foss-setup/scripts/verification/stack-mirror-check.sh" manifest
```

## `repo-tracked-ignored`

no tracked-but-ignored files in the homelab repo (L68 class)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-43` · **enabled:** True
- **expects:** `^0$`

```bash
D=/var/lib/verification/wiki-drift-repo; { git -C "$D" rev-parse --git-dir >/dev/null 2>&1 || { rm -rf "$D"; git clone -q forgejo:home/homelab "$D"; }; } && git -C "$D" fetch -q origin main && git -C "$D" reset --hard -q FETCH_HEAD && git -C "$D" ls-files -i -c --exclude-standard | wc -l
```

## `tracker-count-sanity`

tracker views arithmetically consistent with tasks/progress JSONs

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-43` · **enabled:** True
- **expects:** `TRACKER-COUNTS-OK`

```bash
D=/var/lib/verification/wiki-drift-repo; { git -C "$D" rev-parse --git-dir >/dev/null 2>&1 || { rm -rf "$D"; git clone -q forgejo:home/homelab "$D"; }; } && git -C "$D" fetch -q origin main && git -C "$D" reset --hard -q FETCH_HEAD && python3 "$D/foss-setup/scripts/verification/tracker-count-check.py" "$D"
```

## `tracker-integrity`

tracker JSON sources coherent (ids resolve, no dup/contradiction, _meta counts dead)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-44` · **enabled:** True
- **expects:** `tracker coherent`

```bash
D=/var/lib/verification/wiki-drift-repo; { git -C "$D" rev-parse --git-dir >/dev/null 2>&1 || { rm -rf "$D"; git clone -q forgejo:home/homelab "$D"; }; } && git -C "$D" fetch -q origin main && git -C "$D" reset --hard -q FETCH_HEAD && python3 "$D/foss-setup/scripts/verification/tracker-integrity.py"
```

## `unit-file-drift`

deployed ansible-pull units byte-match the repo on mini + rig (L86 class)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-43` · **enabled:** True
- **expects:** `UNIT-DRIFT-OK`

```bash
D=/var/lib/verification/wiki-drift-repo; { git -C "$D" rev-parse --git-dir >/dev/null 2>&1 || { rm -rf "$D"; git clone -q forgejo:home/homelab "$D"; }; } && git -C "$D" fetch -q origin main && git -C "$D" reset --hard -q FETCH_HEAD && bash "$D/foss-setup/scripts/verification/unit-drift-check.sh" "$D"
```

## `dotfiles-content-clean`

chezmoi dotfiles have no uncommitted content drift on mini + rig (glue-04b)

- **host:** `mini` · **severity:** `warn` · **guards task:** `glue-04b` · **enabled:** True
- **expects:** `DOTFILES-CONTENT-CLEAN`

```bash
m=$(chezmoi diff 2>/dev/null | grep -c '^@@' || true); r=$(ssh -o BatchMode=yes -o ConnectTimeout=10 rig "chezmoi diff 2>/dev/null | grep -c '^@@'" </dev/null | tr -d '[:space:]'); echo "mini_hunks=$m rig_hunks=$r"; { [ "$m" = 0 ] && [ "$r" = 0 ]; } && echo DOTFILES-CONTENT-CLEAN
```

## `ai-tooling-clean-pushed`

rig local-ai-tooling repo is clean AND HEAD pushed to both remotes (ai-03)

- **host:** `rig` · **severity:** `warn` · **guards task:** `ai-03` · **enabled:** True
- **expects:** `AI-TOOLING-CLEAN-PUSHED`

```bash
cd ~/Documents/GitHub/local-ai-tooling && dirty=$(git status --porcelain | wc -l | tr -d '[:space:]') && head=$(git rev-parse HEAD) && o=$(git ls-remote origin HEAD | awk 'NR==1{print $1}') && f=$(git ls-remote forgejo HEAD | awk 'NR==1{print $1}') && echo "dirty=$dirty head=${head:0:12} origin=${o:0:12} forgejo=${f:0:12}" && { [ "$dirty" = 0 ] && [ -n "$head" ] && [ "$head" = "$o" ] && [ "$head" = "$f" ]; } && echo AI-TOOLING-CLEAN-PUSHED
```

## `ai-tooling-env-example-parity`

rig local-ai-tooling docker/.env keys all mapped in .env.example (ai-04)

- **host:** `rig` · **severity:** `warn` · **guards task:** `ai-04` · **enabled:** True
- **expects:** `ENV-EXAMPLE-PARITY-OK`

```bash
cd ~/Documents/GitHub/local-ai-tooling/docker && exk=$(grep -vE '^#|^$' .env.example | cut -d= -f1) && miss=$(for k in $(grep -vE '^#|^$' .env | cut -d= -f1); do echo "$exk" | grep -qx "$k" || echo "$k"; done | wc -l | tr -d '[:space:]') && echo "keys-missing-from-example=$miss" && [ "$miss" = 0 ] && echo ENV-EXAMPLE-PARITY-OK
```

## `dual-remote-mirror-parity`

dual-remoted repos: Forgejo mirror == GitHub mirror (both directions)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-65` · **enabled:** True
- **expects:** `DUAL-REMOTE-PARITY-OK`

```bash
df_f=$(git ls-remote forgejo:home/dotfiles main | awk 'NR==1{print $1}') && df_g=$(git ls-remote https://github.com/btabaska/dotfiles main | awk 'NR==1{print $1}') && ai_f=$(git ls-remote forgejo:home/local-ai-tooling main | awk 'NR==1{print $1}') && ai_g=$(git ls-remote https://github.com/btabaska/local-ai-tooling main | awk 'NR==1{print $1}') && echo "dotfiles f=${df_f:0:12} g=${df_g:0:12} | local-ai-tooling f=${ai_f:0:12} g=${ai_g:0:12}" && { [ -n "$df_f" ] && [ "$df_f" = "$df_g" ] && [ -n "$ai_f" ] && [ "$ai_f" = "$ai_g" ]; } && echo DUAL-REMOTE-PARITY-OK
```

## `export-manifests-inventory-fresh`

rig export-manifests refreshes inventory.md (helper present, no silent skip)

- **host:** `rig` · **severity:** `warn` · **guards task:** `fix-65` · **enabled:** True
- **expects:** `EXPORT-MANIFESTS-INVENTORY-OK`

```bash
test -x /opt/scripts/inventory/gen-inventory-md.sh && last=$(journalctl -u export-manifests.service --no-pager 2>/dev/null | grep -Eo 'Regenerating inventory.md|skipping inventory.md refresh' | tail -1) && echo "gen-inventory=present last-leg=${last:-none}" && [ "$last" = "Regenerating inventory.md" ] && echo EXPORT-MANIFESTS-INVENTORY-OK
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
