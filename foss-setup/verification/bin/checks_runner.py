#!/usr/bin/env python3
"""Continuous-verification check runner (verify-01/02/05).

Runs on mini. Loads checks.d/*.yaml (PyYAML — verified present on mini, 5.4.1),
executes enabled checks, writes results.json / last-summary.md /
reopen-suggestions.json under /var/lib/verification, sends ONE ntfy summary on
STATE TRANSITIONS (new failures or recoveries vs the previous run of the same
tier — a persistent unchanged failure set does not re-page; the unfiltered
daily sweep additionally pages while anything is still failing, as the
once-a-day reminder), exits nonzero if any crit check failed. stdlib + PyYAML
only — no third-party pip deps.
"""
import argparse
import datetime
import json
import os
import platform
import re
import subprocess
import sys
import time
import urllib.request

import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CHECKS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "checks.d")
STATE_DIR = os.environ.get("VERIFICATION_STATE_DIR", "/var/lib/verification")
ENV_FILE = os.environ.get("VERIFICATION_ENV_FILE", "/etc/verification/env")
CHECK_TIMEOUT = 60  # seconds per check
SSH_OPTS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
LOCAL_HOSTNAMES = ("macmini", "mini")  # runner host: 'mini'/'local' run without ssh


def load_env_file(path):
    """Best-effort KEY=VALUE loader for /etc/verification/env."""
    if not os.path.exists(path):
        return
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except PermissionError:
        pass


def load_checks(checks_dir):
    checks = []
    for fname in sorted(os.listdir(checks_dir)):
        # skip dotfiles — macOS scp can drop AppleDouble "._*.yaml" binaries
        # here, which crashed the whole runner (2026-07-10)
        if fname.startswith(".") or not fname.endswith((".yaml", ".yml")):
            continue
        domain = re.sub(r"\.ya?ml$", "", fname)
        with open(os.path.join(checks_dir, fname)) as f:
            doc = yaml.safe_load(f) or {}
        for c in doc.get("checks", []):
            c["domain"] = domain
            for field in ("id", "name", "host", "cmd", "severity", "task_id"):
                if field not in c:
                    raise ValueError(f"{fname}: check missing '{field}': {c}")
            if "expect" not in c and "expect_exit" not in c:
                raise ValueError(f"{fname}: {c['id']} needs expect or expect_exit")
            checks.append(c)
    return checks


def run_check(check):
    host = check["host"]
    cmd = check["cmd"]
    on_runner = platform.node().split(".")[0] in LOCAL_HOSTNAMES
    if host in ("local", "url") or (host == "mini" and on_runner):
        argv = ["bash", "-c", cmd]
    elif host in ("mini", "nas", "rig"):
        argv = ["ssh"] + SSH_OPTS + [host, cmd]
    else:
        return {"status": "fail", "exit_code": -1,
                "output": f"unknown host '{host}'", "duration_s": 0.0}
    start = time.monotonic()
    try:
        # errors="replace": one non-UTF-8 byte in any check's output (e.g. a
        # docker log line) must not crash the whole sweep (bit us 2026-07-10
        # via soularr's logs).
        proc = subprocess.run(argv, capture_output=True, text=True,
                              errors="replace", timeout=CHECK_TIMEOUT)
        out = (proc.stdout or "") + (proc.stderr or "")
        exit_code = proc.returncode
        stdout = proc.stdout or ""
    except subprocess.TimeoutExpired:
        out, stdout, exit_code = f"TIMEOUT after {CHECK_TIMEOUT}s", "", 124
    duration = round(time.monotonic() - start, 2)

    if "expect" in check:
        ok = re.search(check["expect"], stdout, re.M) is not None
    else:
        ok = exit_code == int(check["expect_exit"])
    return {"status": "pass" if ok else "fail", "exit_code": exit_code,
            "output": out.strip()[:2000], "duration_s": duration}


def previous_failed_ids(results_path):
    try:
        with open(results_path) as f:
            prev = json.load(f)
        return {c["id"] for c in prev.get("checks", []) if c["status"] == "fail"}
    except Exception:
        return set()


ACKS_PATH = os.path.join(STATE_DIR, "acks.json")


def load_acks():
    """Operator-acknowledged check ids: {id: {"until": iso, "reason": str}}.

    An acked check still RUNS and is recorded in results/summaries — it just
    stops paging until the ack expires (known/accepted outages, e.g. the
    playit upstream outage 2026-07-10, which otherwise flap-pages on every
    hourly quick run). Manage with ack-check.sh. Expired entries are pruned
    here on load.
    """
    try:
        with open(ACKS_PATH) as f:
            acks = json.load(f)
    except Exception:
        return {}
    now = datetime.datetime.now().astimezone()
    live = {}
    for cid, meta in acks.items():
        try:
            if datetime.datetime.fromisoformat(meta["until"]) > now:
                live[cid] = meta
        except Exception:
            continue
    if live != acks:
        try:
            with open(ACKS_PATH, "w") as f:
                json.dump(live, f, indent=2)
        except Exception:
            pass
    return live


def send_ntfy(message, title, priority):
    url = os.environ.get("NTFY_URL", "http://127.0.0.1:8080/verification")
    token = os.environ.get("NTFY_TOKEN", "")
    req = urllib.request.Request(url, data=message.encode(), method="POST")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Title", title)
    req.add_header("Priority", priority)
    req.add_header("Tags", "warning" if priority == "high" else "white_check_mark")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status


def main():
    ap = argparse.ArgumentParser(description="Run verification checks")
    ap.add_argument("--host", help="only run checks whose host or domain matches "
                                   "(e.g. --host rig; also enables disabled checks "
                                   "of that host/domain)")
    ap.add_argument("--json", action="store_true", help="print results JSON to stdout")
    ap.add_argument("--checks-dir", default=DEFAULT_CHECKS_DIR)
    ap.add_argument("--no-notify", action="store_true", help="skip ntfy notification")
    ap.add_argument("--notify", action="store_true",
                    help="send ntfy on filtered (--host) runs too — used by the "
                         "scheduled quick tier; ad-hoc filtered runs stay silent "
                         "by default")
    ap.add_argument("--tier", help="only run enabled checks tagged `tier: <name>` "
                                   "(e.g. --tier fast); writes results-tier-<name>.json "
                                   "and, unlike --host, RESPECTS 'enabled' — it is a "
                                   "scheduled tier, not an operator override")
    args = ap.parse_args()

    load_env_file(ENV_FILE)
    os.makedirs(STATE_DIR, exist_ok=True)
    # Filtered (--host) runs are ad-hoc operator runs: they write to a side
    # file and never touch the daily state (results.json, reopen-suggestions,
    # last-summary) or send notifications.
    filtered = bool(args.host) or bool(args.tier)
    if args.tier:
        results_path = os.path.join(STATE_DIR, f"results-tier-{args.tier}.json")
    elif args.host:
        results_path = os.path.join(STATE_DIR, f"results-{args.host}.json")
    else:
        results_path = os.path.join(STATE_DIR, "results.json")
    prev_failed = previous_failed_ids(results_path)

    checks = load_checks(args.checks_dir)
    if args.host:
        checks = [c for c in checks
                  if c["host"] == args.host or c["domain"] == args.host]
        # explicit host filter is an operator action: include disabled checks
        # (e.g. checks still disabled for other reasons, like the seedbox;
        # rig checks are enabled in the daily cycle now — rig is 24/7)
        runnable = checks
    elif args.tier:
        # scheduled fast tier: run only checks tagged `tier: <name>`, and — unlike
        # --host — RESPECT `enabled` (a scheduled tier must not resurrect a
        # deliberately-disabled check, e.g. the dns-02 NAS-secondary crits).
        checks = [c for c in checks if c.get("tier") == args.tier]
        runnable = [c for c in checks if c.get("enabled", True)]
    else:
        runnable = [c for c in checks if c.get("enabled", True)]

    results, skipped = [], []
    for c in checks:
        entry = {k: c.get(k) for k in
                 ("id", "name", "host", "domain", "cmd", "severity",
                  "task_id", "runbook")}
        if c in runnable and (args.host or c.get("enabled", True)):
            entry.update(run_check(c))
        else:
            entry.update({"status": "skipped", "exit_code": None,
                          "output": "disabled", "duration_s": 0.0})
            skipped.append(c["id"])
        results.append(entry)

    ran = [r for r in results if r["status"] != "skipped"]
    failed = [r for r in ran if r["status"] == "fail"]
    crit_failed = [r for r in failed if r["severity"] == "crit"]
    failed_ids = {r["id"] for r in failed}
    new_failures = sorted(failed_ids - prev_failed)
    recovered = sorted(prev_failed - failed_ids)
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    doc = {
        "timestamp": now,
        "runner_host": platform.node(),
        "host_filter": args.host,
        "summary": {"total": len(ran), "passed": len(ran) - len(failed),
                    "failed": len(failed), "crit_failed": len(crit_failed),
                    "skipped": len(skipped)},
        "checks": results,
    }
    with open(results_path, "w") as f:
        json.dump(doc, f, indent=2)

    # verify-05: reopen suggestions for the AI session-start protocol.
    reopen = sorted({r["task_id"] for r in failed if r.get("task_id")})
    if not filtered:
        with open(os.path.join(STATE_DIR, "reopen-suggestions.json"), "w") as f:
            json.dump({"generated": now,
                       "task_ids": reopen,
                       "failed_checks": [{"id": r["id"], "task_id": r["task_id"],
                                          "severity": r["severity"]}
                                         for r in failed],
                       "note": "consumed by the AI session-start protocol; "
                               "the runner never commits to git by design"},
                      f, indent=2)

    # last-summary.md
    lines = [f"# Verification run — {now}", "",
             f"**{doc['summary']['passed']}/{doc['summary']['total']} passed**, "
             f"{len(failed)} failed ({len(crit_failed)} crit), "
             f"{len(skipped)} skipped.", ""]
    if failed:
        lines += ["## Failed", "",
                  "| id | sev | task | output (first line) |",
                  "|---|---|---|---|"]
        for r in failed:
            first = (r["output"].splitlines() or [""])[0][:100].replace("|", "\\|")
            lines.append(f"| {r['id']} | {r['severity']} | {r['task_id']} | {first} |")
        lines.append("")
    if recovered:
        lines += ["## Recovered since last run", ""] + [f"- {i}" for i in recovered] + [""]
    lines += ["## All checks", ""]
    for r in results:
        mark = {"pass": "PASS", "fail": "FAIL", "skipped": "skip"}[r["status"]]
        lines.append(f"- [{mark}] {r['id']} ({r['severity']}) — {r['name']}")
    if not filtered:
        with open(os.path.join(STATE_DIR, "last-summary.md"), "w") as f:
            f.write("\n".join(lines) + "\n")

    # ONE ntfy summary, on TRANSITIONS only (new failures / recoveries vs the
    # previous run of the same tier). A persistent unchanged failure set must
    # NOT re-page every run — the hourly quick tier re-paged the same playit
    # upstream outage all morning on 2026-07-10 ("failures like this are
    # unacceptable" — user). The UNfiltered daily sweep still pages while
    # anything is failing: one reminder per day so nothing rots silently.
    # Filtered runs are silent unless --notify (the quick tier timer); their
    # state diff uses their own results-<host>.json, so tiers don't clobber
    # each other's transition tracking.
    # Acked checks (operator-acknowledged known outages) are excluded from all
    # paging math but stay visible in results/summaries.
    acks = load_acks()
    page_new = [i for i in new_failures if i not in acks]
    page_recovered = [i for i in recovered if i not in acks]
    page_failed_ids = {i for i in failed_ids if i not in acks}
    page_crit = [r for r in crit_failed if r["id"] not in acks]
    transition = bool(page_new or page_recovered)
    daily_reminder = (not filtered) and bool(page_failed_ids)
    if ((not filtered or args.notify) and not args.no_notify
            and (transition or daily_reminder)):
        parts = []
        if page_new:
            parts.append(f"NEW failures ({len(page_new)}): "
                         + ", ".join(page_new))
        if page_recovered:
            parts.append("recovered: " + ", ".join(page_recovered))
        still = sorted(page_failed_ids - set(page_new))
        if still:
            parts.append(f"still failing ({len(still)}): " + ", ".join(still))
        acked_failing = sorted(failed_ids & set(acks))
        if acked_failing:
            parts.append("acked/suppressed: " + ", ".join(
                f"{i} (until {acks[i]['until'][:16]})" for i in acked_failing))
        if page_crit:
            parts.append("crit: " + ", ".join(r["id"] for r in page_crit))
        if reopen:
            parts.append("reopen candidates: " + ", ".join(reopen))
        tier = f" [{args.host} tier]" if filtered else ""
        if page_new:
            title = f"Verification{tier}: {len(page_new)} NEW failure(s)"
        elif page_failed_ids:
            title = f"Verification{tier}: still failing"
        else:
            title = f"Verification{tier}: all recovered"
        try:
            send_ntfy("\n".join(parts), title,
                      "high" if page_crit else "default")
            print(f"ntfy: sent ({title})", file=sys.stderr)
        except Exception as e:
            print(f"ntfy: send FAILED: {e}", file=sys.stderr)

    if args.json:
        print(json.dumps(doc, indent=2))
    else:
        print(f"{doc['summary']['passed']}/{doc['summary']['total']} passed, "
              f"{len(failed)} failed ({len(crit_failed)} crit), "
              f"{len(skipped)} skipped — see {results_path}")
        for r in failed:
            print(f"  FAIL [{r['severity']}] {r['id']} (task {r['task_id']})")
    sys.exit(1 if crit_failed else 0)


if __name__ == "__main__":
    main()
