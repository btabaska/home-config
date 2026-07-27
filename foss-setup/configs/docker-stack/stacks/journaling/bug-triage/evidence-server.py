#!/usr/bin/env python3
"""bug-02 read-only evidence collector — "mini is the eyes."

A tiny, dependency-free HTTP observer for the household bug-intake triage loop
(bug-02). On `GET /evidence?service=<key>` it runs a FIXED, per-service, READ-ONLY
probe playbook and returns a JSON evidence bundle:

  - docker  : live State/Health/RestartCount + last log lines for the mini-local
              containers that back the service (Docker Engine API over the socket,
              GET-only — never start/stop/exec/mutate).
  - http    : unauthenticated health/status probes of the service's own API (works
              cross-host over the LAN for NAS/rig services) — status code + snippet.
  - notes   : documented EXPECTED-STATE caveats the reasoning model must know so it
              does not misdiagnose a normal state as the bug (e.g. the Immich ML
              night-window, rig GPU contention).

Security-by-construction (bug-intake pitch, operator decision 2026-07-27):
  * The read-only ceiling is STRUCTURAL. This process only ever issues Docker API
    GETs and outbound HTTP GETs. There is no code path that mutates fleet state, and
    the `service` parameter is validated against a fixed allowlist (the playbook
    keys) — there is no passthrough of arbitrary docker commands or URLs.
  * It holds NO secrets. All probes are unauthenticated. The docker socket is mounted
    read-only; the API is used GET-only regardless.
  * It is INTERNAL only — reachable by n8n by container name on the `edge` network,
    never published to the host and never fronted by Caddy.

The reasoning half (rig LLM via LiteLLM) is reached only by n8n, never by this
observer — so the eyes never touch the fleet and the brain has no fleet access.
"""
import json
import os
import re
import socket
import http.client
import urllib.request
import urllib.error
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

DOCKER_SOCK = os.environ.get("DOCKER_SOCK", "/var/run/docker.sock")
LISTEN_PORT = int(os.environ.get("EVIDENCE_PORT", "8410"))
LOG_SINCE_SECS = int(os.environ.get("EVIDENCE_LOG_SINCE", "7200"))  # 2h window
LOG_TAIL = int(os.environ.get("EVIDENCE_LOG_TAIL", "40"))
HTTP_TIMEOUT = 6

# NAS = 192.168.10.4, rig = 192.168.10.12. Probes use raw IPs so the collector needs
# no DNS (net-16: mini-.2 AdGuard times out from containers). Only mini-local
# containers appear under `containers` (that is all the docker socket can see).
# Each playbook has:
#   containers       — mini-local container names to inspect over the docker socket
#   http             — unauthenticated health/status probes (work cross-host by LAN IP)
#   context          — BACKGROUND facts (host/port topology, where to look) — NEVER on
#                      their own a reason to call a symptom "expected"
#   expected_states  — documented NORMAL conditions that can PRODUCE a symptom; the
#                      reasoning model may answer "expected, not a fault" ONLY when one
#                      of these actually explains the report. Keeping these separate from
#                      `context` stops a small model misreading a topology note as an
#                      expected state (bug-02: the Immich ML night-window must land here).
PLAYBOOKS = {
    "immich": {
        "display": "Immich — photos (NAS)",
        "containers": [],
        "http": [
            {"name": "immich-server ping", "url": "http://192.168.10.4:2283/api/server/ping"},
            {"name": "immich-server version", "url": "http://192.168.10.4:2283/api/server/version"},
        ],
        "context": [
            "Immich runs on the NAS (192.168.10.4:2283). Photo browse/upload/timeline "
            "use the NAS immich-server and do not depend on the rig ML at all.",
        ],
        "expected_states": [
            "Immich machine-learning (face detection, smart/CLIP search) is time-gated "
            "to a NIGHT window 01:00-07:00 EDT on the rig (glue-14): by DAY rig ML is "
            "intentionally DOWN and only smart-search/face-detection BACKFILL is deferred "
            "to that window. So during the day, 'AI face/subject search seems stuck / "
            "new-photo smart results missing' while browsing/upload work fine is EXPECTED, "
            "NOT a fault. 'rig ML down by day / 0 ML jobs / rig VRAM pinned' is also normal.",
        ],
    },
    "plex": {
        "display": "Plex / Jellyfin — watch (NAS)",
        "containers": ["tautulli"],
        "http": [
            {"name": "plex identity", "url": "http://192.168.10.4:32400/identity"},
            {"name": "jellyfin health", "url": "http://192.168.10.4:8096/health"},
        ],
        "context": [
            "Plex (192.168.10.4:32400) and Jellyfin (:8096) run on the NAS; Tautulli "
            "(mini) is the Plex activity monitor — its logs can reveal a Plex that is "
            "unreachable or unauthorized even when the port answers. A raw /identity 200 "
            "means Plex is up but says nothing about a specific library or the user's "
            "client; a household 'can't play' may be client/network, not the server.",
        ],
        "expected_states": [],
    },
    "navidrome": {
        "display": "Navidrome / Audiobookshelf — listen",
        "containers": ["navidrome"],
        "http": [
            {"name": "navidrome ping", "url": "http://192.168.10.2:4533/ping"},
            {"name": "audiobookshelf health", "url": "http://192.168.10.4:13378/healthcheck"},
        ],
        "context": [
            "Navidrome runs on the mini (:4533); Audiobookshelf on the NAS (:13378), on "
            "a read-only CIFS mount of the library.",
        ],
        "expected_states": [
            "Greyed-out / missing tracks in Navidrome are usually a SCAN artifact "
            "(media_file.missing=1) after files move on the CIFS mount, not an outage — "
            "the container stays healthy and a full rescan clears it. A few missing "
            "tracks with a healthy container is expected, not a service fault.",
        ],
    },
    "komga": {
        "display": "Reading — Audiobookshelf / Komga / Calibre-Web / Suwayomi",
        "containers": [],
        "http": [
            {"name": "komga", "url": "http://192.168.10.4:25600/"},
            {"name": "audiobookshelf health", "url": "http://192.168.10.4:13378/healthcheck"},
            {"name": "calibre-web-automated", "url": "http://192.168.10.4:8083/"},
            {"name": "suwayomi (manga)", "url": "http://192.168.10.12:4567/"},
        ],
        "context": [
            "Reading spans the NAS (Komga :25600, Audiobookshelf :13378, Calibre-Web "
            "8083) and the rig (Suwayomi/manga :4567). Suwayomi FEEDS Komga's manga "
            "library over a CIFS mount, so 'new manga missing' can be a Suwayomi "
            "download/mount issue rather than Komga.",
        ],
        "expected_states": [
            "Calibre-Web-Automated returns HTTP 302 (redirect to its login page) when "
            "healthy — a 302 here is normal, not an error.",
        ],
    },
    "journaling": {
        "display": "Journaling — Memos / n8n",
        "containers": ["memos", "n8n"],
        "http": [
            {"name": "memos health", "url": "http://192.168.10.2:5230/healthz"},
            {"name": "n8n health", "url": "http://192.168.10.2:5678/healthz"},
        ],
        "context": [
            "Memos (the journal) + n8n (the automation) run on the mini. Whisper "
            "dictation is CPU-only on the mini and lazy-loads its model on first use.",
        ],
        "expected_states": [
            "The journaling COACH / reflection reply is generated by the rig LLM "
            "(llama-swap/LiteLLM), which shares the single 3090 Ti with Immich ML and "
            "can be GPU-contended (rig-gpu-vram-contention). A missing or very slow "
            "reflection while Memos + n8n are healthy is a best-effort inference degrade, "
            "not a Memos/n8n outage — the entry itself was still saved.",
        ],
    },
    "homepage": {
        "display": "Homepage — the dashboard",
        "containers": ["homepage", "caddy"],
        "http": [
            {"name": "homepage services API", "url": "http://192.168.10.2:3010/api/services"},
        ],
        "context": [
            "Homepage (mini :3010, fronted by Caddy) renders tiles CLIENT-SIDE from "
            "/api/services per request. A single red/'API Error' tile usually means the "
            "UPSTREAM service that tile points at is down — Homepage itself is fine if "
            "/api/services returns JSON. The '/' HTML is a static Next.js skeleton and is "
            "NOT evidence of tile health (Homepage-quirks).",
        ],
        "expected_states": [],
    },
    "games": {
        "display": "Games — AMP / Palworld (rig)",
        "containers": [],
        "http": [
            {"name": "AMP web", "url": "http://192.168.10.12:8080/"},
        ],
        "context": [
            "Game servers run on the rig, managed by AMP (:8080). The rig's single 3090 "
            "Ti is shared with LLM/Immich ML, so a game server can be memory/CPU starved "
            "under load; AMP logs (not visible from the mini) hold the detail.",
        ],
        "expected_states": [
            "Palworld's REST API (:8211) requires auth, so it is NOT probed "
            "unauthenticated here — the absence of a Palworld HTTP result in this "
            "evidence is expected and is not itself a fault.",
        ],
    },
    "seerr": {
        "display": "Requests — Seerr / Musicseerr / Libreseerr",
        "containers": ["seerr", "musicseerr", "libreseerr"],
        "http": [
            {"name": "seerr status", "url": "http://192.168.10.2:5055/api/v1/status"},
            {"name": "musicseerr status", "url": "http://192.168.10.2:8688/api/v1/status"},
            {"name": "libreseerr", "url": "http://192.168.10.2:8789/"},
        ],
        "context": [
            "The *seerr request front-ends run on the mini. A request that never "
            "'arrives' is often a DOWNSTREAM arr/indexer/download-client issue on the "
            "NAS + seedbox, which is NOT probed here — a healthy status endpoint only "
            "proves the request UI is up, not that the download pipeline works.",
        ],
        "expected_states": [],
    },
    "triage": {
        "display": "Unknown — needs manual triage",
        "containers": ["caddy", "homepage"],
        "http": [
            {"name": "homepage services API", "url": "http://192.168.10.2:3010/api/services"},
        ],
        "context": [
            "The household form could not map this report to a specific service. Only "
            "general reachability of the dashboard/reverse-proxy is available; the "
            "service is UNKNOWN and the operator must map it by hand.",
        ],
        "expected_states": [],
    },
}


# --- Docker Engine API over the unix socket (GET-only) -----------------------------
class _UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__("localhost")
        self._unix_path = path

    def connect(self):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(HTTP_TIMEOUT)
        s.connect(self._unix_path)
        self.sock = s


def _docker_get(path):
    """Issue a GET against the Docker Engine API. Returns (status, bytes)."""
    conn = _UnixHTTPConnection(DOCKER_SOCK)
    try:
        conn.request("GET", path)
        resp = conn.getresponse()
        return resp.status, resp.read()
    finally:
        conn.close()


def _demux_logs(raw):
    """Docker multiplexes non-TTY logs as 8-byte-framed chunks; strip the frames.
    Falls back to a best-effort decode if the stream is not framed (TTY containers)."""
    out = []
    i, n = 0, len(raw)
    framed = True
    while i + 8 <= n:
        stream_type = raw[i]
        if stream_type not in (0, 1, 2):
            framed = False
            break
        size = int.from_bytes(raw[i + 4 : i + 8], "big")
        payload = raw[i + 8 : i + 8 + size]
        out.append(payload.decode("utf-8", "replace"))
        i += 8 + size
    if not framed:
        return raw.decode("utf-8", "replace")
    return "".join(out)


def _container_evidence(name):
    ev = {"name": name}
    try:
        status, body = _docker_get("/containers/json?all=1")
        if status != 200:
            ev["error"] = f"docker list HTTP {status}"
            return ev
        containers = json.loads(body)
    except Exception as e:  # noqa: BLE001
        ev["error"] = f"docker unreachable: {e}"
        return ev

    match = None
    for c in containers:
        if any(nm.lstrip("/") == name for nm in c.get("Names", [])):
            match = c
            break
    if not match:
        ev["error"] = "container not found on this host"
        return ev

    cid = match["Id"]
    ev["state"] = match.get("State")          # running / exited / restarting ...
    ev["status"] = match.get("Status")        # "Up 3 days (healthy)" ...
    ev["image"] = match.get("Image")

    try:
        s2, b2 = _docker_get(f"/containers/{cid}/json")
        if s2 == 200:
            insp = json.loads(b2)
            st = insp.get("State", {})
            ev["restart_count"] = insp.get("RestartCount")
            ev["started_at"] = st.get("StartedAt")
            ev["exit_code"] = st.get("ExitCode")
            health = st.get("Health") or {}
            if health:
                ev["health"] = health.get("Status")
                last = (health.get("Log") or [])[-1:]
                if last:
                    ev["last_health_output"] = (last[0].get("Output") or "").strip()[:200]
    except Exception as e:  # noqa: BLE001
        ev["inspect_error"] = str(e)

    # recent logs (read-only) — since a bounded window, tail-limited, trimmed
    try:
        since = int(datetime.now(timezone.utc).timestamp()) - LOG_SINCE_SECS
        s3, b3 = _docker_get(
            f"/containers/{cid}/logs?stdout=1&stderr=1&timestamps=1&tail={LOG_TAIL}&since={since}"
        )
        if s3 == 200:
            text = _demux_logs(b3)
            lines = [ln for ln in (l.rstrip() for l in text.splitlines()) if ln]
            # keep the tail; hard-cap width so a runaway line can't bloat the bundle
            ev["recent_logs"] = [ln[:400] for ln in lines[-LOG_TAIL:]]
        else:
            ev["logs_error"] = f"HTTP {s3}"
    except Exception as e:  # noqa: BLE001
        ev["logs_error"] = str(e)
    return ev


def _http_probe(name, url):
    probe = {"name": name, "url": url}
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "bug-triage-evidence/1"})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            body = r.read(600).decode("utf-8", "replace")
            probe["status"] = r.status
            probe["snippet"] = re.sub(r"\s+", " ", body).strip()[:200]
    except urllib.error.HTTPError as e:
        probe["status"] = e.code
        probe["snippet"] = f"HTTP {e.code} {e.reason}"
    except Exception as e:  # noqa: BLE001
        probe["status"] = None
        probe["error"] = str(e)
    return probe


def build_evidence(service):
    pb = PLAYBOOKS[service]
    bundle = {
        "service": service,
        "display": pb["display"],
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "read_only": True,
        "docker": [_container_evidence(n) for n in pb["containers"]],
        "http": [_http_probe(p["name"], p["url"]) for p in pb["http"]],
        "context": list(pb.get("context", [])),
        "expected_states": list(pb.get("expected_states", [])),
    }
    return bundle


class Handler(BaseHTTPRequestHandler):
    server_version = "bug-triage-evidence/1"

    def _send(self, code, obj):
        payload = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            self._send(200, {"ok": True, "services": sorted(PLAYBOOKS)})
            return
        if parsed.path != "/evidence":
            self._send(404, {"error": "not found"})
            return
        service = (parse_qs(parsed.query).get("service") or [""])[0].strip().lower()
        if service not in PLAYBOOKS:
            self._send(400, {"error": "unknown service", "valid": sorted(PLAYBOOKS)})
            return
        try:
            self._send(200, build_evidence(service))
        except Exception as e:  # noqa: BLE001
            self._send(500, {"error": str(e)})

    def log_message(self, fmt, *args):  # quieter logs
        pass


def main():
    srv = ThreadingHTTPServer(("0.0.0.0", LISTEN_PORT), Handler)
    print(f"bug-triage-evidence listening on :{LISTEN_PORT} (read-only observer)", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
