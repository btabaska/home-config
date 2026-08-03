#!/usr/bin/env python3
"""triage-wellformed.py (fix-61) — cheap regression guard for SH17.

The LLM auto-triage layer was 91% nonfunctional (68/75 verdicts were the hardcoded
"triage failed — model did not return valid JSON" fallback) for weeks while its
live probe stayed green. This is the CONSUMER-END check on the OUTPUT the runner
actually wrote: it parses the newest triage-<date>.md and fails if too large a
fraction of the latest run's verdicts are fallbacks — catching a re-regression of
the reasoning-budget/empty-content class without spending a model call. Sibling of
llm-triage-completion-e2e (which probes the model live). stdlib only.
"""
import glob
import os
import re
import sys

STATE_DIR = os.environ.get("VERIFICATION_STATE_DIR", "/var/lib/verification")
# The fallback verdict's diagnosis always contains this ASCII substring (the
# em-dash in "triage failed — …" is JSON-escaped to — in the file, so match
# on the stable tail instead).
FALLBACK = "did not return valid JSON"
MAX_FALLBACK_FRAC = float(os.environ.get("TRIAGE_MAX_FALLBACK_FRAC", "0.34"))

files = sorted(glob.glob(os.path.join(STATE_DIR, "triage-*.md")))
if not files:
    print("TRIAGE_WELLFORMED_OK verdicts=0 (no triage file yet)")
    sys.exit(0)

newest = files[-1]
text = open(newest).read()
# Each run appends a "## Triage run <iso> — …" header; evaluate only the last run.
runs = text.split("## Triage run")
section = runs[-1] if len(runs) > 1 else text
verdicts = len(re.findall(r"^### ", section, re.M))
fallbacks = section.count(FALLBACK)
base = os.path.basename(newest)

if verdicts == 0:
    print(f"TRIAGE_WELLFORMED_OK verdicts=0 file={base}")
    sys.exit(0)

frac = fallbacks / verdicts
if frac > MAX_FALLBACK_FRAC:
    print(f"TRIAGE_WELLFORMED_BAD fallbacks={fallbacks}/{verdicts} "
          f"frac={frac:.2f} (> {MAX_FALLBACK_FRAC}) file={base}")
    sys.exit(1)
print(f"TRIAGE_WELLFORMED_OK fallbacks={fallbacks}/{verdicts} "
      f"frac={frac:.2f} file={base}")
