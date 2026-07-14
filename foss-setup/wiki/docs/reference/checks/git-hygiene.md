# Checks — git-hygiene

`foss-setup/verification/checks.d/git-hygiene.yaml` — 3 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

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

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
