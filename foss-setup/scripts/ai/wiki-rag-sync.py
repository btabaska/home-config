#!/usr/bin/env python3
"""wiki-rag-sync — keep the Open WebUI "homelab-wiki" knowledge collection
in sync with the wiki markdown sources (ai-01 RAG pillar).

Runs on the mini (wiki-rag-sync.timer, daily). Flow:
  1. freshen a dedicated clone of the homelab repo (forgejo:home/homelab)
     at /var/lib/verification/wiki-rag-repo (fetch + hard reset to origin/main)
  2. diff wiki/docs/**/*.md against the local state manifest (sha256)
  3. upload new/changed files to OWUI (/api/v1/files/), wait for processing
     (chunk + embed via LiteLLM `embed` alias -> llama-swap nomic on the rig),
     then attach to the knowledge collection; remove deleted/stale versions
  4. save the manifest

Env (from /etc/verification/env): OWUI_URL (default https://ai.tabaska.us),
OWUI_API_KEY (created 2026-07-15, admin "rag-sync (ai-01)" key).

Stdlib only (mini has Python 3.10 — no oikb, which needs 3.11+).
"""
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
import uuid

OWUI_URL = os.environ.get("OWUI_URL", "https://ai.tabaska.us").rstrip("/")
API_KEY = os.environ.get("OWUI_API_KEY", "")
REPO_DIR = "/var/lib/verification/wiki-rag-repo"
REPO_REMOTE = "forgejo:home/homelab"
DOCS_SUBDIR = "foss-setup/wiki/docs"   # repo root is Home/; foss-setup is a subdir
STATE_PATH = "/var/lib/verification/wiki-rag-state.json"
COLLECTION_NAME = "homelab-wiki"


def api(method, path, body=None, raw=None, content_type="application/json", timeout=60):
    url = OWUI_URL + path
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": "Bearer " + API_KEY,
                                          "Content-Type": content_type})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        text = r.read()
    return json.loads(text) if text else None


def upload_file(relpath, content: bytes):
    """Multipart upload; returns the file id."""
    boundary = uuid.uuid4().hex
    fname = relpath.replace("/", "__")
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
            f"filename=\"{fname}\"\r\nContent-Type: text/markdown\r\n\r\n").encode()
    body += content + f"\r\n--{boundary}--\r\n".encode()
    return api("POST", "/api/v1/files/", raw=body,
               content_type=f"multipart/form-data; boundary={boundary}", timeout=120)["id"]


def wait_processed(file_id, budget=180):
    """Poll processing status; tolerate builds without the status endpoint."""
    t0 = time.time()
    while time.time() - t0 < budget:
        try:
            st = api("GET", f"/api/v1/files/{file_id}/process/status")
            status = (st or {}).get("status", "")
            if status in ("completed", "success"):
                return True
            if status == "failed":
                return False
        except urllib.error.HTTPError as e:
            if e.code == 404:      # older API: no status endpoint; give it a beat
                time.sleep(3)
                return True
            raise
        time.sleep(2)
    return False


def kb_file(action, kid, file_id):
    """add/remove a file on the collection; retry adds (processing races)."""
    for attempt in range(5):
        try:
            api("POST", f"/api/v1/knowledge/{kid}/file/{action}", {"file_id": file_id})
            return True
        except urllib.error.HTTPError as e:
            detail = e.read()[:200].decode(errors="replace")
            if action == "add" and e.code == 400 and attempt < 4:
                time.sleep(5)
                continue
            if action == "remove" and e.code in (400, 404):
                return True    # already gone
            print(f"  {action} {file_id}: HTTP {e.code} {detail}", file=sys.stderr)
            return False
    return False


def main():
    if not API_KEY:
        sys.exit("OWUI_API_KEY not set")

    # 1. freshen the repo clone
    if not os.path.isdir(os.path.join(REPO_DIR, ".git")):
        subprocess.run(["git", "clone", "-q", REPO_REMOTE, REPO_DIR], check=True)
    subprocess.run(["git", "-C", REPO_DIR, "fetch", "-q", "origin", "main"], check=True)
    subprocess.run(["git", "-C", REPO_DIR, "reset", "--hard", "-q", "FETCH_HEAD"], check=True)

    docs_root = os.path.join(REPO_DIR, DOCS_SUBDIR)
    local = {}
    for root, _dirs, files in os.walk(docs_root):
        for f in files:
            if f.endswith(".md"):
                p = os.path.join(root, f)
                rel = os.path.relpath(p, docs_root)
                local[rel] = hashlib.sha256(open(p, "rb").read()).hexdigest()

    # 2. find/create the collection (paginated shape: {"items": [...], "total": n})
    resp = api("GET", "/api/v1/knowledge/") or {}
    kbs = resp.get("items", resp) if isinstance(resp, dict) else resp
    kid = next((k["id"] for k in kbs if k.get("name") == COLLECTION_NAME), None)
    if not kid:
        kid = api("POST", "/api/v1/knowledge/create",
                  {"name": COLLECTION_NAME,
                   "description": "Homelab wiki (auto-synced daily from forgejo by wiki-rag-sync, ai-01)"})["id"]
        print(f"created collection {COLLECTION_NAME} ({kid})")

    state = {}
    if os.path.exists(STATE_PATH):
        state = json.load(open(STATE_PATH))

    added = replaced = removed = failed = 0
    # 3a. new + changed
    for rel, digest in sorted(local.items()):
        old = state.get(rel)
        if old and old["sha256"] == digest:
            continue
        content = open(os.path.join(docs_root, rel), "rb").read()
        try:
            fid = upload_file(rel, content)
            wait_processed(fid)
            if not kb_file("add", kid, fid):
                failed += 1
                continue
            if old:
                kb_file("remove", kid, old["file_id"])
                replaced += 1
            else:
                added += 1
            state[rel] = {"sha256": digest, "file_id": fid}
        except Exception as e:
            failed += 1
            print(f"  FAILED {rel}: {type(e).__name__}: {e}", file=sys.stderr)

    # 3b. deletions
    for rel in [r for r in list(state) if r not in local]:
        kb_file("remove", kid, state[rel]["file_id"])
        del state[rel]
        removed += 1

    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    json.dump(state, open(STATE_PATH, "w"), indent=1)
    print(f"sync done: +{added} ~{replaced} -{removed} !{failed} (total tracked {len(state)})")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
