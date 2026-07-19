# Checks — git-hygiene

`foss-setup/verification/checks.d/git-hygiene.yaml` — 9 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

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

## `unit-file-drift`

deployed ansible-pull units byte-match the repo on mini + rig (L86 class)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-43` · **enabled:** True
- **expects:** `UNIT-DRIFT-OK`

```bash
D=/var/lib/verification/wiki-drift-repo; { git -C "$D" rev-parse --git-dir >/dev/null 2>&1 || { rm -rf "$D"; git clone -q forgejo:home/homelab "$D"; }; } && git -C "$D" fetch -q origin main && git -C "$D" reset --hard -q FETCH_HEAD && bash "$D/foss-setup/scripts/verification/unit-drift-check.sh" "$D"
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
