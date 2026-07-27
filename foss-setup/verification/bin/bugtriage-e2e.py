#!/usr/bin/env python3
"""bug-02 consumer-end probe — the household bug-intake READ-ONLY auto-triage loop.

Exercises the REAL loop end to end, not liveness:
  1. POST a synthetic household report through the LIVE n8n Form Trigger, carrying the
     triage SENTINEL (n8n-triage-probe) so the notify gate skips ntfy/Discord — a
     monitoring run never buzzes the operator's phone.
  2. Assert the report became a labeled Forgejo issue in home/household-bugs.
  3. Poll the issue for the auto-triage COMMENT that the observe(mini)->reason(rig) branch
     posts back. Two healthy outcomes:
       * a real diagnosis comment (the rig model answered)   -> BUGTRIAGE_OK
       * an evidence-only degrade comment (model unavailable  -> BUGTRIAGE_SKIP_MODEL_UNAVAILABLE
         under rig GPU contention; the pipeline still posted the machine-gathered evidence)
     No comment at all after the wait means the loop is broken -> BUGTRIAGE_FAIL.
  4. Assert the read-only footer is present (proxy for the structural read-only ceiling:
     the comment states no fleet state was changed) and the `triaged` label was applied.
  5. DELETE the probe issue -> zero residue in the repo the operator reads.

Both BUGTRIAGE_OK and BUGTRIAGE_SKIP_MODEL_UNAVAILABLE are PASSes (best-effort ceiling:
"the 24B may be GPU-contended by day" is expected, degrade not fail). Only a broken loop,
a missing comment, or a lost read-only footer FAILs.

Env (from /etc/verification/env): FORGEJO_API_URL, FORGEJO_PROBE_TOKEN
(write:issue + write:repository — read the created issue/comments and delete the probe).
Diagnostics -> stderr; only the final token -> stdout (runner matches `expect`).
task_id: bug-02
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error

N8N = os.environ.get("BUGREPORT_N8N_BASE", "http://localhost:5678")
FORM_PATH = os.environ.get("BUGREPORT_FORM_PATH", "/form/8f2c1a4b-6d3e-4a90-b1c2-a1b2c3d4e5f6")
API = os.environ.get("FORGEJO_API_URL", "http://localhost:3030/api/v1")
REPO = os.environ.get("BUGREPORT_REPO", "home/household-bugs")
TOK = os.environ.get("FORGEJO_PROBE_TOKEN", "")
SENTINEL = "n8n-triage-probe"
# The triage report is a Photos ("service:immich") case whose expected symptom the model
# should recognise as the documented ML night-window — but the check does NOT grade the
# diagnosis text (that is the E2E-of-reasoning tested at build time); it grades that the
# LOOP produced a grounded comment + label, degrade-aware.
ACTIVITY = "\U0001F5BC️ Photos"
WHAT = "Face search seems stuck this afternoon; browsing albums works fine."
POLL_TIMEOUT = int(os.environ.get("BUGTRIAGE_POLL_TIMEOUT", "150"))  # LLM cold-load headroom
POLL_INTERVAL = int(os.environ.get("BUGTRIAGE_POLL_INTERVAL", "5"))


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def emit(token, code):
    print(token)
    sys.exit(code)


def api(path, method="GET"):
    r = urllib.request.Request(API + path, method=method, headers={"Authorization": "token " + TOK})
    return urllib.request.urlopen(r, timeout=12)


def main():
    if not TOK:
        emit("BUGTRIAGE_FAIL: FORGEJO_PROBE_TOKEN unset in the runner env", 1)

    # 1) synthetic multipart submit carrying the triage sentinel (notify-suppressed)
    marker = f"{SENTINEL} {int(time.time())}"
    boundary = "----bugtriageprobe" + str(int(time.time()))

    def part(name, val):
        return f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{val}\r\n'

    body = (part("field-0", ACTIVITY) + part("field-1", f"{marker} {WHAT}")).encode("utf-8")
    body += f"--{boundary}--\r\n".encode("utf-8")
    req = urllib.request.Request(N8N + FORM_PATH, data=body, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        code = urllib.request.urlopen(req, timeout=20).status
    except Exception as e:  # noqa: BLE001
        emit(f"BUGTRIAGE_FAIL: form submit failed ({e}); workflow inactive or n8n down?", 1)
    if code != 200:
        emit(f"BUGTRIAGE_FAIL: form submit returned {code}", 1)

    # 2) confirm the submission became a Forgejo issue
    issue = None
    for _ in range(8):
        time.sleep(2)
        try:
            data = json.load(api(f"/repos/{REPO}/issues?state=all&limit=8&sort=created"))
        except Exception as e:  # noqa: BLE001
            emit(f"BUGTRIAGE_FAIL: could not read issues ({e})", 1)
        for i in data:
            if marker in (i.get("title") or "") or marker in (i.get("body") or ""):
                issue = i
                break
        if issue:
            break
    if not issue:
        emit("BUGTRIAGE_FAIL: synthetic report never became a Forgejo issue (form->n8n->Forgejo broken)", 1)

    num = issue["number"]
    log(f"issue #{num} created; polling for the auto-triage comment (<= {POLL_TIMEOUT}s)")

    # 3) poll for the triage comment (mini gathers evidence -> rig reasons -> comment)
    comment = None
    waited = 0
    while waited < POLL_TIMEOUT:
        time.sleep(POLL_INTERVAL)
        waited += POLL_INTERVAL
        try:
            cs = json.load(api(f"/repos/{REPO}/issues/{num}/comments"))
        except Exception as e:  # noqa: BLE001
            log(f"comment read error (retrying): {e}")
            continue
        for c in cs:
            if "Auto-triage" in (c.get("body") or ""):
                comment = c
                break
        if comment:
            break

    def cleanup():
        try:
            api(f"/repos/{REPO}/issues/{num}", "DELETE")
            return True
        except Exception as e:  # noqa: BLE001
            log(f"cleanup delete of #{num} failed: {e}")
            return False

    if not comment:
        cleanup()
        emit(f"BUGTRIAGE_FAIL: issue #{num} got no auto-triage comment within {POLL_TIMEOUT}s (triage loop broken)", 1)

    cbody = comment.get("body") or ""
    # 4) structural read-only ceiling proxy: the comment must state nothing was changed
    if "READ-ONLY" not in cbody or "No fleet state was changed" not in cbody:
        cleanup()
        emit("BUGTRIAGE_FAIL: triage comment posted but the read-only footer is missing (ceiling assertion failed)", 1)

    # label check + degrade classification
    try:
        i2 = json.load(api(f"/repos/{REPO}/issues/{num}"))
        labels = sorted(l["name"] for l in i2.get("labels", []))
    except Exception:  # noqa: BLE001
        labels = []
    has_triaged = "triaged" in labels
    degraded = "evidence only" in cbody.lower() or "reasoning model was unavailable" in cbody.lower()

    deleted = cleanup()

    if degraded:
        emit(f"BUGTRIAGE_SKIP_MODEL_UNAVAILABLE issue #{num} got the evidence-only degrade "
             f"comment (rig model contended); pipeline healthy; triaged={has_triaged} deleted={deleted}", 0)

    if not has_triaged:
        emit(f"BUGTRIAGE_FAIL: issue #{num} got a diagnosis comment but the 'triaged' label was not applied", 1)

    emit(f"BUGTRIAGE_OK issue #{num} diagnosis comment posted + labeled {labels} deleted={deleted}", 0)


if __name__ == "__main__":
    main()
