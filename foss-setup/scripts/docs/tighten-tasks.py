#!/usr/bin/env python3
"""Apply task-overrides.json to foss-setup/docs/index.html (tasks after net-13)."""
import json
import re
from copy import deepcopy
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HTML = REPO / "docs" / "index.html"
OVERRIDES = Path(__file__).parent / "task-overrides.json"


def merge_task(base: dict, patch: dict) -> dict:
    out = deepcopy(base)
    for k, v in patch.items():
        if k in ("steps", "commands", "files", "docs") and v:
            out[k] = v
        elif v is not None and k not in ("steps", "commands", "files", "docs"):
            out[k] = v
    # ensure minimum quality
    if len(out.get("steps", [])) < 5:
        out.setdefault("steps", []).append(
            "From MacBook: confirm completion matches the verify block below before checking this task done."
        )
    return out


def main():
    if not OVERRIDES.exists():
        raise SystemExit(f"Run generate-task-overrides.py first — missing {OVERRIDES}")

    overrides = json.loads(OVERRIDES.read_text())
    text = HTML.read_text()
    m = re.search(r"(id=\"taskData\">\s*)(\[.*?\])(\s*</script>)", text, re.S)
    if not m:
        raise SystemExit("taskData not found")

    tasks = json.loads(m.group(2))
    start = next(i for i, t in enumerate(tasks) if t["id"] == "net-14")
    applied = 0
    missing = []

    for i in range(start, len(tasks)):
        tid = tasks[i]["id"]
        if tid in overrides:
            tasks[i] = merge_task(tasks[i], overrides[tid])
            applied += 1
        else:
            missing.append(tid)

    HTML.write_text(text[: m.start(2)] + json.dumps(tasks, separators=(",", ":")) + text[m.end(2) :])
    print(f"Applied {applied} overrides to index.html")
    if missing:
        print(f"WARNING: no override for: {', '.join(missing)}")


if __name__ == "__main__":
    main()
