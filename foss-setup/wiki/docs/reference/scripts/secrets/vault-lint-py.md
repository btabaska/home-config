# `vault-lint.py`

> the vault-completeness class check (fix-23, quality-gate M26/M44/M45).

**Path:** `foss-setup/scripts/secrets/vault-lint.py` · **Category:** [secrets](index.md) · **Type:** Python

## What it does

```text
vault-lint.py — the vault-completeness class check (fix-23, quality-gate M26/M44/M45).

The incident class: a service is live on a host with working credentials in its own
config, but the handoff vault (.handoff-secrets.yaml) says '' — so the "ALL credentials
live in the vault" mandate silently breaks and disaster recovery loses the credential
(soulseek.* empty while slskd ran on betty; forgejo admin empty while Forgejo was the
deploy control plane; whisparr key only in config.xml).

This must run on the macbook — the vault never leaves it — so it cannot be a
verification/checks.d check (the runner lives on the mini). It is wired into
publish-deploy.sh instead: every publish lints the vault and fails loudly on empty keys.

Keys that are INTENTIONALLY empty (service not deployed / credential genuinely N/A)
belong in ALLOW_EMPTY with a reason, not silently blank.
```

## See also

- [secrets scripts](index.md) · [All scripts](../index.md)
