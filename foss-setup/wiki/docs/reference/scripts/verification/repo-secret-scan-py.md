# `repo-secret-scan.py`

> repo-secret-scan — refuse to ship a committed secret (fix-84).

**Path:** `foss-setup/scripts/verification/repo-secret-scan.py` · **Category:** [verification](index.md) · **Type:** Python

## Synopsis

```
repo-secret-scan.py [repo_root]     # default: git toplevel of cwd
```

## What it does

```text
repo-secret-scan — refuse to ship a committed secret (fix-84).

The 2026-08-23 sweep (UH2) found a live playit SECRET_KEY pasted verbatim into a
committed audit doc (quality-gate-2026-07-16.json/.md) and pushed to GitHub +
Forgejo — the vault-lint gate only checks the vault file, nothing scanned the rest
of the tree. This scanner runs over every git-tracked file and fails if it finds:

  1. VERBATIM vault secrets — any leaf string value from .handoff-secrets.yaml
     that lives under a secret-ish key (pass/secret/token/key/api/private/cred/
     seed/diceware) and is >=16 chars, appearing anywhere in a tracked file.
     (Only runs when the vault is readable — i.e. on the operator Mac at publish
     time. This is the strong, exact check.)
  2. SECRET-SHAPED strings by pattern (runs everywhere, no vault needed):
     - ntfy tokens  tk_[A-Za-z0-9]{20,}
     - PEM private-key headers
     - AWS-style AKIA keys
     - a secret-ish assignment KEY=<32+ char high-entropy value>

Never prints a secret value — only <file>:<line> and the rule that fired. Exit 0
clean, 1 on any hit. Redaction placeholders (<REDACTED...>) are ignored.

Usage:  repo-secret-scan.py [repo_root]     # default: git toplevel of cwd
```

## See also

- [`catalog-vhost-parity.py`](catalog-vhost-parity-py.md)
- [`deploy.sh`](deploy-sh.md)
- [`reopen-report.py`](reopen-report-py.md)
- [`stack-mirror-check.sh`](stack-mirror-check-sh.md)
- [`tracker-count-check.py`](tracker-count-check-py.md)
- [`tracker-integrity.py`](tracker-integrity-py.md)
- [`unit-drift-check.sh`](unit-drift-check-sh.md)
- [verification scripts](index.md) · [All scripts](../index.md)
