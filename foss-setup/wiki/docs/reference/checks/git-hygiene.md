# Checks — git-hygiene

`foss-setup/verification/checks.d/git-hygiene.yaml` — 4 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

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

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
