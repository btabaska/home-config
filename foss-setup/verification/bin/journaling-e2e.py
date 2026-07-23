#!/usr/bin/env python3
"""journaling-e2e.py — CONSUMER-END end-to-end probe for the journaling loop (journal-06).

Proves the whole pipeline actually works, not just that containers are up: it POSTs a
marked ``#journal`` test memo to Memos and waits for the n8n ``journal-analyze`` workflow
to write back EXACTLY ONE reflection comment. That single comment appearing proves, in
one shot, that (a) Memos delivered the ``memo.created`` webhook to n8n, (b) the Guard let
it through, (c) n8n reached the rig coach LLM and got a parseable reply, (d) the reflection
was written back as a COMMENT, and (e) the loop guard held (writing that comment fires two
more webhook events, neither of which may produce a second comment). Then it deletes the
test memo + its comment so nothing is left in the journal.

The reflection is BEST-EFFORT by design: the rig coach model (~17 GB) shares the single
3090 Ti with Immich ML and can be OOM-evicted, in which case the entry is still saved but
no comment is written (see docs/journaling-stack-plan.md risk 2). So this probe first checks
whether the coach model can actually load; if it can't, it SKIPS (does not post) rather than
false-failing on a condition that is expected and separately monitored
(``journaling-coach-model-reachable``). A real FAIL therefore means the loop itself is broken
(webhook lost, workflow unpublished, guard regressed) while the model was available.

Prints exactly one classification token as the LAST line of stdout:
  E2E_OK                      exactly one reflection comment appeared          -> PASS
  E2E_SKIP_COACH_UNAVAILABLE  coach model won't load right now (GPU busy);     -> PASS
                              nothing posted, reflection untestable now
  E2E_NO_COMMENT              coach WAS loadable but no reflection appeared     -> FAIL (loop broken)
  E2E_LOOP_MULTICOMMENT       more than one reflection comment                 -> FAIL (loop guard broke)
  E2E_ERROR:<detail>          Memos API / harness error                        -> FAIL

Runs on the mini verification runner (``bash -c``, ``/etc/verification/env`` loaded). Config
is read from the runner env, then the live stack ``.env`` (source of truth for whatever coach
model the workflow currently uses), then built-in defaults. Diagnostics go to stderr; only the
final token goes to stdout (the runner matches ``expect`` against stdout).
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

MEMOS_BASE = os.environ.get("MEMOS_BASE_URL", "http://localhost:5230") + "/api/v1"
STACK_ENV = os.environ.get("JOURNALING_ENV_FILE", "/opt/stacks/journaling/.env")
REFLECTION_SENTINEL = "\U0001f9ed"  # 🧭 — the exact marker the workflow's write-back starts with
COACH_PROBE_TIMEOUT = int(os.environ.get("E2E_COACH_PROBE_TIMEOUT", "75"))  # model cold-load headroom
POLL_TIMEOUT = int(os.environ.get("E2E_POLL_TIMEOUT", "150"))              # wait for the reflection
POLL_INTERVAL = int(os.environ.get("E2E_POLL_INTERVAL", "6"))


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def emit(token, code):
    print(token)
    sys.exit(code)


def stack_env(key):
    """Read KEY=VALUE from the live stack .env (source of truth for the running coach)."""
    try:
        with open(STACK_ENV) as f:
            for line in f:
                m = re.match(r"\s*" + re.escape(key) + r"=(.*)", line)
                if m:
                    return m.group(1).strip().strip('"').strip("'")
    except OSError:
        pass
    return None


def cfg(key, default=None):
    return os.environ.get(key) or stack_env(key) or default


TOKEN = cfg("MEMOS_API_TOKEN")
LLM_BASE = cfg("LLM_BASE_URL", "http://192.168.10.12:9292/v1")
LLM_MODEL = cfg("LLM_MODEL", "dolphin-venice-24b")
HDRS = {"Authorization": "Bearer " + (TOKEN or ""), "Content-Type": "application/json"}


def api(method, path, body=None, base=MEMOS_BASE, headers=HDRS, timeout=15):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode()
        return resp.status, (json.loads(raw) if raw.strip() else {})


def coach_loadable():
    """One tiny completion against the rig coach. True iff the model actually loads+answers.
    This both discriminates GPU-eviction from a broken loop AND warms the model so the
    workflow's own call (moments later) is fast."""
    body = {"model": LLM_MODEL, "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1, "temperature": 0}
    try:
        st, _ = api("POST", "/chat/completions", body, base=LLM_BASE,
                    headers={"Content-Type": "application/json"}, timeout=COACH_PROBE_TIMEOUT)
        return st == 200
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
        log(f"coach probe failed ({LLM_MODEL} @ {LLM_BASE}): {e}")
        return False


def reflections_on(name):
    """Return the list of reflection comments (content starting with the 🧭 sentinel)
    currently attached to memo `name`."""
    st, body = api("GET", f"/{name}/comments")
    memos = body.get("memos", []) if isinstance(body, dict) else []
    return [m for m in memos if (m.get("content") or "").strip().startswith(REFLECTION_SENTINEL)]


def main():
    if not TOKEN:
        emit("E2E_ERROR:no-memos-token", 1)
    if not coach_loadable():
        log("coach model unavailable (GPU busy / OOM) — reflection is best-effort, skipping")
        emit("E2E_SKIP_COACH_UNAVAILABLE", 0)

    created = []
    nonce = f"{int(time.time())}-{os.getpid()}"
    content = (f"#journal [e2e-probe {nonce}] automated pipeline verification — "
               "feeling steady and calm today, nothing much to report.")
    try:
        st, memo = api("POST", "/memos", {"content": content, "visibility": "PRIVATE"})
        name = memo.get("name")
        if st != 200 or not name:
            emit(f"E2E_ERROR:create-{st}", 1)
        created.append(name)
        log(f"posted test memo {name}; waiting up to {POLL_TIMEOUT}s for a reflection comment")

        deadline = time.monotonic() + POLL_TIMEOUT
        refs = []
        while time.monotonic() < deadline:
            time.sleep(POLL_INTERVAL)
            try:
                refs = reflections_on(name)
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
                log(f"poll error (transient): {e}")
                continue
            if refs:
                log(f"reflection comment(s) seen: {len(refs)} after "
                    f"{int(POLL_TIMEOUT - (deadline - time.monotonic()))}s")
                break

        if len(refs) == 1:
            emit("E2E_OK", 0)
        elif len(refs) == 0:
            emit("E2E_NO_COMMENT", 1)
        else:
            emit("E2E_LOOP_MULTICOMMENT", 1)
    except urllib.error.HTTPError as e:
        emit(f"E2E_ERROR:http-{e.code}", 1)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        emit(f"E2E_ERROR:{type(e).__name__}", 1)
    finally:
        # Always clean up: delete comment memos first (avoid orphans), then the parent.
        for name in created:
            try:
                for c in api("GET", f"/{name}/comments")[1].get("memos", []):
                    try:
                        api("DELETE", f"/{c['name']}")
                    except OSError:
                        pass
            except OSError:
                pass
            try:
                api("DELETE", f"/{name}")
                log(f"cleaned up {name}")
            except OSError as e:
                log(f"cleanup of {name} failed: {e}")


if __name__ == "__main__":
    main()
