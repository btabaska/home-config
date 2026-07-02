#!/usr/bin/env python3
"""Resequence tasks in docs/index.html — see apply-workstream-sequencing.py for full workstream order."""
import importlib.util
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "apply_workstream_sequencing", _HERE / "apply-workstream-sequencing.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

if __name__ == "__main__":
    _mod.main()
