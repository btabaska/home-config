#!/usr/bin/env python3
"""bug-01 consumer-end probe — the household "Report a Problem" intake.

Exercises the REAL pipeline end to end, not liveness:
  1. GET the n8n Form Trigger form  -> 200 + the two required fields render
     (proves n8n is up, the workflow is ACTIVE, and the form route is registered;
      an unpublished/deactivated workflow 404s here).
  2. POST a synthetic multipart submission carrying the healthcheck SENTINEL. The
     workflow creates the Forgejo issue (full form -> map -> label -> create path) but
     the notify gate SKIPS ntfy/Discord for sentinel reports, so a monitoring run never
     buzzes the operator's phone.
  3. Verify a matching issue appeared in home/household-bugs with the expected
     auto-labels (source:home + service:triage + sev:annoying).
  4. DELETE the probe issue -> zero residue in the repo the operator reads.

Env (from /etc/verification/env): FORGEJO_API_URL, FORGEJO_PROBE_TOKEN
(write:issue + write:repository, so it can read the created issue and delete it).

Prints BUGREPORT_OK on success; BUGREPORT_FAIL: <reason> + exit 1 otherwise.
task_id: bug-01
"""
import os, sys, json, time, urllib.request, urllib.error

N8N = os.environ.get("BUGREPORT_N8N_BASE", "http://localhost:5678")
FORM_PATH = os.environ.get("BUGREPORT_FORM_PATH", "/form/8f2c1a4b-6d3e-4a90-b1c2-a1b2c3d4e5f6")
API = os.environ.get("FORGEJO_API_URL", "http://localhost:3030/api/v1")
REPO = os.environ.get("BUGREPORT_REPO", "home/household-bugs")
TOK = os.environ.get("FORGEJO_PROBE_TOKEN", "")
SENTINEL = "n8n-bugreport-probe"


def fail(msg):
    print("BUGREPORT_FAIL: " + msg)
    sys.exit(1)


def main():
    # 1) form reachable + required fields present (form served + workflow active)
    try:
        html = urllib.request.urlopen(N8N + FORM_PATH, timeout=10).read().decode("utf-8", "replace")
    except Exception as e:
        fail(f"form GET {FORM_PATH} failed ({e}); workflow inactive or n8n down?")
    for needle in ("What were you trying to do?", "What happened?"):
        if needle not in html:
            fail(f"form served but missing required field: {needle!r}")

    # 2) synthetic multipart submit carrying the sentinel (notify-suppressed)
    marker = f"{SENTINEL} {int(time.time())}"
    boundary = "----bugprobe" + str(int(time.time()))
    def part(name, val):
        return f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{val}\r\n'
    body = (part("field-0", "❓ Something else") + part("field-1", marker)).encode("utf-8")
    body += f"--{boundary}--\r\n".encode("utf-8")
    req = urllib.request.Request(N8N + FORM_PATH, data=body, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        code = urllib.request.urlopen(req, timeout=20).status
    except Exception as e:
        fail(f"form submit failed: {e}")
    if code != 200:
        fail(f"form submit returned {code}")

    if not TOK:
        fail("FORGEJO_PROBE_TOKEN unset in the runner env")

    # 3) confirm the submission became a labeled Forgejo issue
    def api(path, method="GET"):
        r = urllib.request.Request(API + path, method=method, headers={"Authorization": "token " + TOK})
        return urllib.request.urlopen(r, timeout=10)

    found = None
    for _ in range(6):
        time.sleep(2)
        try:
            data = json.load(api(f"/repos/{REPO}/issues?state=all&limit=8&sort=created"))
        except Exception as e:
            fail(f"could not read issues to verify: {e}")
        for i in data:
            if marker in (i.get("title") or "") or marker in (i.get("body") or ""):
                found = i
                break
        if found:
            break
    if not found:
        fail("synthetic submission did not create a Forgejo issue (form->n8n->Forgejo chain broken)")

    labels = set(l["name"] for l in found.get("labels", []))
    num = found["number"]

    # 4) clean up (best-effort) then judge labels
    try:
        api(f"/repos/{REPO}/issues/{num}", "DELETE")
        deleted = True
    except Exception as e:
        deleted = False
        print(f"BUGREPORT_WARN: cleanup delete of #{num} failed: {e}", file=sys.stderr)

    need = {"source:home", "service:triage", "sev:annoying"}
    missing = need - labels
    if missing:
        fail(f"issue #{num} created but auto-labels wrong; missing {sorted(missing)} (got {sorted(labels)})")

    print(f"BUGREPORT_OK form+submit->issue #{num} labels={sorted(labels)} "
          f"deleted={deleted}")


if __name__ == "__main__":
    main()
