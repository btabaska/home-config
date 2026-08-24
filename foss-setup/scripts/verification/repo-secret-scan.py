#!/usr/bin/env python3
"""repo-secret-scan — refuse to ship a committed secret (fix-84).

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
"""
import os
import re
import subprocess
import sys

SECRETY_KEY = re.compile(
    r"(pass|secret|token|api[_-]?key|apikey|[_-]key$|^key$|private|cred|seed|"
    r"diceware|password)", re.I)
PATTERNS = [
    ("ntfy-token", re.compile(r"\btk_[A-Za-z0-9]{20,}\b")),
    ("pem-private-key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    # KEY = long high-entropy value (>=32 chars, mixed) — the audit-doc-pastes-a-key class
    ("secret-assignment", re.compile(
        r"(?i)(secret|token|api[_-]?key|apikey|password|priv(ate)?[_-]?key)"
        r"['\"]?\s*[:=]\s*['\"]?([A-Za-z0-9+/_-]{32,})")),
]
REDACTION = re.compile(r"REDACTED", re.I)
# binary / vendored / expected-secret-holder paths to skip
SKIP_SUFFIX = (".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".webp",
               ".ico", ".woff", ".woff2", ".ttf", ".mp4", ".pmtiles",
               ".example")  # *.env.example / *.example are placeholder templates
SKIP_PATH = (".handoff-secrets.yaml.example",)  # documented placeholder file

# KNOWN, TRACKED exposures — allowlisted so the publish gate blocks NEW leaks but
# does not wedge on a pre-existing leak that already has an open remediation task.
# Format: repo-relative path prefix -> tracking task. REMOVE an entry the moment
# its task closes (so the file must then be clean or the gate fails).
ALLOWLIST = {
    # sec-10: arr API keys stored cleartext in unpackerr.conf (rotation +
    # externalisation is its own work item — do not let it block every publish).
    "foss-setup/configs/nas/media-automation/unpackerr/unpackerr.conf": "sec-10",
}


def load_vault_values(root):
    """Leaf secret values from the vault, if present (operator Mac only)."""
    vault = os.path.join(root, "foss-setup", ".handoff-secrets.yaml")
    if not os.path.exists(vault):
        return set()
    try:
        import yaml
    except ImportError:
        return set()
    vals = set()

    def walk(d, keyname=""):
        if isinstance(d, dict):
            for k, v in d.items():
                walk(v, str(k))
        elif isinstance(d, list):
            for v in d:
                walk(v, keyname)
        elif isinstance(d, str):
            if len(d.strip()) >= 16 and SECRETY_KEY.search(keyname):
                vals.add(d.strip())
    walk(yaml.safe_load(open(vault)))
    return vals


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True).strip()
    files = subprocess.check_output(
        ["git", "-C", root, "ls-files"], text=True).splitlines()
    vault_vals = load_vault_values(root)
    hits = []
    allowed = 0
    for rel in files:
        if rel.endswith(SKIP_SUFFIX) or any(rel.endswith(s) for s in SKIP_PATH):
            continue
        if rel in ALLOWLIST:
            allowed += 1
            continue
        path = os.path.join(root, rel)
        try:
            with open(path, "r", errors="replace") as fh:
                for n, line in enumerate(fh, 1):
                    if REDACTION.search(line):
                        continue
                    for v in vault_vals:
                        if v in line:
                            hits.append(f"{rel}:{n}: verbatim vault secret")
                            break
                    for name, pat in PATTERNS:
                        if pat.search(line):
                            hits.append(f"{rel}:{n}: {name}")
        except (IsADirectoryError, PermissionError):
            continue
    mode = "vault+pattern" if vault_vals else "pattern-only"
    if hits:
        print(f"SECRETS-FOUND ({mode}) {len(hits)} hit(s):")
        for h in hits[:50]:
            print("  " + h)
        sys.exit(1)
    print(f"SECRETS-CLEAN ({mode}) scanned {len(files)} tracked files, 0 leaks "
          f"({allowed} allowlisted: {','.join(sorted(set(ALLOWLIST.values())))})")


if __name__ == "__main__":
    main()
