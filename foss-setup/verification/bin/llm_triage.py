#!/usr/bin/env python3
"""verify-04: per-check LLM triage.

For each failed check in results.json, issue a FRESH single-turn completion
(new context per check — no shared conversation) against the local model,
using the domain-scoped skill prompt from skills/*.md. Verdicts are appended
to /var/lib/verification/triage-<date>.md. Malformed JSON -> one retry, then
recorded as escalate:true. stdlib only.
"""
import datetime
import json
import os
import re
import sys
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "skills")
STATE_DIR = os.environ.get("VERIFICATION_STATE_DIR", "/var/lib/verification")
BASE_URL = os.environ.get("LLM_BASE_URL",
                          "http://cachyos.tailb31641.ts.net:11434/v1").rstrip("/")
MODEL = os.environ.get("LLM_MODEL", "qwen3-coder:30b")
API_KEY = os.environ.get("LLM_API_KEY", "")
MAX_CHECKS = int(os.environ.get("TRIAGE_MAX_CHECKS", "15"))

DOMAIN_SKILL = {
    "dns": "dns-triage.md",
    "mini-services": "docker-triage.md",
    "nas-services": "docker-triage.md",
    "rig": "docker-triage.md",
    "backups": "backup-triage.md",
    "git-hygiene": "git-hygiene-triage.md",
    "system": "system-triage.md",
}
REQUIRED_KEYS = {"diagnosis", "likely_cause", "suggested_fix_commands",
                 "confidence", "escalate"}


def complete(system_prompt, user_prompt):
    """One fresh, single-turn chat completion. No shared context."""
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": system_prompt},
                     {"role": "user", "content": user_prompt}],
        "temperature": 0,
        "max_tokens": 600,
    }).encode()
    req = urllib.request.Request(f"{BASE_URL}/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    if API_KEY:
        req.add_header("Authorization", f"Bearer {API_KEY}")
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


def parse_verdict(text):
    """Strict-ish JSON extraction: strip code fences, find outermost object."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.M)
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON object in response")
    verdict = json.loads(m.group(0))
    missing = REQUIRED_KEYS - set(verdict)
    if missing:
        raise ValueError(f"missing keys: {sorted(missing)}")
    if not isinstance(verdict["suggested_fix_commands"], list):
        raise ValueError("suggested_fix_commands is not a list")
    return verdict


def triage_one(check, skill_prompt):
    user_prompt = (
        "Failed check:\n"
        + json.dumps({k: check.get(k) for k in
                      ("id", "name", "host", "cmd", "severity", "task_id",
                       "exit_code", "output")}, indent=2)
    )
    last_err = None
    for attempt in (1, 2):
        try:
            raw = complete(skill_prompt, user_prompt)
            return parse_verdict(raw), attempt, None
        except (ValueError, json.JSONDecodeError) as e:
            last_err = f"malformed JSON (attempt {attempt}): {e}"
            user_prompt += ("\n\nREMINDER: respond with ONLY one strict JSON "
                            "object with keys diagnosis, likely_cause, "
                            "suggested_fix_commands, confidence, escalate. "
                            "No markdown, no prose.")
        except Exception as e:
            last_err = f"LLM request failed (attempt {attempt}): {e}"
    return ({"diagnosis": "triage failed — model did not return valid JSON",
             "likely_cause": last_err,
             "suggested_fix_commands": [],
             "confidence": 0.0,
             "escalate": True}, 2, last_err)


def main():
    results_path = os.path.join(STATE_DIR, "results.json")
    with open(results_path) as f:
        results = json.load(f)
    failed = [c for c in results["checks"] if c["status"] == "fail"]
    if not failed:
        print("no failed checks — nothing to triage")
        return
    failed = failed[:MAX_CHECKS]

    skills = {}
    now = datetime.datetime.now().astimezone()
    out_path = os.path.join(STATE_DIR, f"triage-{now:%Y-%m-%d}.md")
    blocks = [f"\n## Triage run {now.isoformat(timespec='seconds')} — "
              f"model `{MODEL}` @ {BASE_URL} — {len(failed)} failed check(s)\n"]
    escalations = 0
    for check in failed:
        skill_file = DOMAIN_SKILL.get(check.get("domain"), "system-triage.md")
        if skill_file not in skills:
            with open(os.path.join(SKILLS_DIR, skill_file)) as f:
                skills[skill_file] = f.read()
        verdict, attempts, err = triage_one(check, skills[skill_file])
        escalations += bool(verdict.get("escalate"))
        blocks.append(
            f"### {check['id']} (sev {check['severity']}, task {check['task_id']}, "
            f"skill {skill_file}, attempts {attempts})\n\n"
            "```json\n" + json.dumps(verdict, indent=2) + "\n```\n"
        )
        print(f"triaged {check['id']}: escalate={verdict.get('escalate')} "
              f"confidence={verdict.get('confidence')}")
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(out_path, "a") as f:
        f.write("\n".join(blocks))
    print(f"wrote {len(failed)} verdicts ({escalations} escalations) to {out_path}")


if __name__ == "__main__":
    main()
