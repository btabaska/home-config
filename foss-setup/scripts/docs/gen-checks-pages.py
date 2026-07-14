#!/usr/bin/env python3
"""gen-checks-pages.py — wiki reference for every verification check (wiki build-out).

Reads verification/checks.d/*.yaml and emits one small linked page per domain
(file), documenting each check: id, what it proves, host, severity, the exact cmd,
expected match, and the task it guards. Plus an index with counts. Deterministic.

Usage: python3 foss-setup/scripts/docs/gen-checks-pages.py
"""
import re, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
CHECKS = REPO / "verification" / "checks.d"
OUT = REPO / "wiki" / "docs" / "reference" / "checks"
MKDOCS = REPO / "wiki" / "mkdocs.yml"
try:
    import yaml
except ImportError:
    yaml = None

def load(p):
    if yaml:
        return (yaml.safe_load(p.read_text()) or {}).get("checks", [])
    # crude fallback: not expected to run (mini/CI have pyyaml)
    return []

OUT.mkdir(parents=True, exist_ok=True)
for old in OUT.glob("*.md"):
    old.unlink()

domains = {}
for f in sorted(CHECKS.glob("*.yaml")):
    checks = load(f)
    domains[f.stem] = checks
    lines = [f"# Checks — {f.stem}", "",
             f"`foss-setup/verification/checks.d/{f.name}` — {len(checks)} check(s). "
             f"Run hourly/daily by the verification harness; page via ntfy. See "
             f"[Verification runbook](../../runbooks/verification.md).", ""]
    for c in checks:
        cid = c.get("id", "?")
        lines += [f"## `{cid}`", "",
                  f"{c.get('name','')}", "",
                  f"- **host:** `{c.get('host','?')}` · **severity:** `{c.get('severity','?')}` "
                  f"· **guards task:** `{c.get('task_id','—')}` · **enabled:** {c.get('enabled', True)}",
                  f"- **expects:** `{c.get('expect', c.get('expect_exit','?'))}`", ""]
        cmd = str(c.get("cmd", "")).strip()
        if cmd:
            lines += ["```bash", cmd, "```", ""]
    lines += ["[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)", ""]
    (OUT / f"{f.stem}.md").write_text("\n".join(lines))

total = sum(len(v) for v in domains.values())
idx = ["# Verification checks", "",
       f"Every acceptance/regression check the fleet runs — **{total} checks across "
       f"{len(domains)} domains**, generated from `verification/checks.d/` by "
       f"`scripts/docs/gen-checks-pages.py`. These probe OUTCOMES (does the user-visible "
       f"result work), not just liveness. See the [Verification runbook](../../runbooks/verification.md) "
       f"and [Acceptance-testing framework](../../runbooks/acceptance-testing.md).", "",
       "| Domain | Checks | crit | warn |", "|---|---|---|---|"]
for d in sorted(domains):
    cs = domains[d]
    crit = sum(1 for c in cs if c.get("severity") == "crit")
    idx.append(f"| [{d}]({d}.md) | {len(cs)} | {crit} | {len(cs)-crit} |")
idx += ["", f"_Total: {total} checks._", ""]
(OUT / "index.md").write_text("\n".join(idx))

nav = ["      # BEGIN GENERATED CHECKS NAV (managed by scripts/docs/gen-checks-pages.py)",
       "      - Overview: reference/checks/index.md"]
for d in sorted(domains):
    nav.append(f"      - {d}: reference/checks/{d}.md")
nav.append("      # END GENERATED CHECKS NAV")
navblock = "\n".join(nav)
y = MKDOCS.read_text()
if "BEGIN GENERATED CHECKS NAV" in y:
    y = re.sub(r"      # BEGIN GENERATED CHECKS NAV.*?      # END GENERATED CHECKS NAV", navblock, y, flags=re.S)
else:
    y = y.replace("  - Scripts reference:", "  - Verification checks:\n" + navblock + "\n  - Scripts reference:", 1)
MKDOCS.write_text(y)
print(f"generated {total} checks across {len(domains)} domains")
