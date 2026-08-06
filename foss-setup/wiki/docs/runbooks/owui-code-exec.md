# Open Terminal (OWUI server-side code execution)

Runbook for the `owui-code-exec` verification check and general operation of
**Open Terminal** — the sandboxed code-execution backend for Open WebUI (lai-09,
local-ai buildout). Service page: [open-terminal](../services/open-terminal.md).

- **Host:** Mac mini (`192.168.10.2`), Docker, stack `/opt/stacks/open-terminal` (project `open-terminal`)
- **URL:** `http://192.168.10.2:8020` — **LAN-only, no Caddy vhost** (it executes arbitrary code; consumers are the rig's OWUI and the verification probe, both over LAN). Swagger at `/docs`.
- **Compose:** live `/opt/stacks/open-terminal/compose.yaml`; repo mirror `foss-setup/configs/docker-stack/stacks/open-terminal/`
- **Image:** `ghcr.io/open-webui/open-terminal:0.11.34@sha256:5e040fe3...` (tag@digest pinned, full-toolkit variant — Python, Node, build tools, ffmpeg)
- **Secrets:** `OPEN_TERMINAL_API_KEY` in the gitignored `./.env` (vault `open_terminal.api_key`); every API request needs it as a Bearer token. The **same key** lives server-side in the rig OWUI terminal-server connection.
- **State:** `./data` == the sandbox `/home/user` (packages the model installs, files it writes, process logs). Disposable in principle; rides the nightly restic snapshot via `/opt/stacks`.
- **Isolation:** own compose network (not `edge`), no docker socket, no host mounts beyond `./data`, `mem_limit: 4g` / `cpus: 2` / `pids_limit: 512`. The in-container `user` has passwordless sudo **by design** (sandbox apt installs) — root inside the container only; never mount host paths or the docker socket here.

## How OWUI 0.10.2 wires it

**Not** via `CODE_EXECUTION_ENGINE` — in 0.10.x that knob (and
`CODE_INTERPRETER_ENGINE`) only knows `pyodide` | `jupyter`, and the run-button
endpoint (`/api/v1/utils/code/execute`) is jupyter-only server-side. Open
Terminal is the **terminal-server integration** instead:

1. The connection lives in PersistentConfig `terminal_server.connections`
   (**DB wins** — `webui.db`; a volume wipe silently erases it). Set it via the
   admin API, not env:
   `POST /api/v1/configs/terminal_servers` with
   `{"TERMINAL_SERVER_CONNECTIONS":[{"id":"open-terminal","name":"Open Terminal (mini)","enabled":true,"url":"http://192.168.10.2:8020","path":"/openapi.json","key":"<vault open_terminal.api_key>","auth_type":"bearer","config":null,"server_type":"terminal"}]}`
   (verify first with `POST /api/v1/configs/terminal_servers/verify` → `{"status":true,"type":"terminal"}`).
2. OWUI fetches the sandbox's `/openapi.json` and injects its tools
   (`run_command`, `read_file`, `write_file`, `grep_search`, ...) into chats
   that attach the terminal (model must be in **Native** function-calling mode).
3. All traffic proxies through OWUI (`/api/v1/terminals/{id}/...`) with the
   Bearer key held **server-side** — browsers never see it.
4. A commented rebuild seed lives in `local-ai-tooling docker/.env` (+
   `.env.example`); compose passes `TERMINAL_SERVER_CONNECTIONS` through with a
   safe `[]` default. Uncomment only to re-seed a **fresh** `open_webui_data`
   volume — the DB is authoritative once set.

## The consumer check

`owui-code-exec` (in `verification/checks.d/local-ai.yaml`, fast sweep, all-LAN,
no LLM call) POSTs deterministic arithmetic through the exact proxy route chat
tool calls take —
`POST $OWUI_URL/api/v1/terminals/open-terminal/execute?wait=60` with
`{"command":"python3 -c \"print(617*3)\""}` — and requires `exit_code == 0` and
the literal `1851` in the returned output. That one round-trip catches: the
PersistentConfig entry erased (404), the Bearer key rotated/invalid (401), the
container down/hung, and "liveness green but execution broken".

## Troubleshooting

- **`OWUI_CODEEXEC_BAD r=noresponse` / HTTP 404 "Terminal server not found".**
  The PersistentConfig connection is gone (OWUI volume wipe or admin-UI delete).
  Re-run the `POST /api/v1/configs/terminal_servers` call above (key from vault
  `open_terminal.api_key`; OWUI admin key `ai_stack.openwebui_rag_sync_api_key`).
- **401/403 through the proxy.** Key mismatch: the connection's `key` no longer
  matches `/opt/stacks/open-terminal/.env`. Rotate both together (vault first),
  then `docker compose up -d` the stack and re-POST the connection.
- **Execution hangs / `status: running` forever.** A wedged sandbox process —
  `ssh mini 'cd /opt/stacks/open-terminal && docker compose restart'`. State in
  `./data` survives restarts.
- **Sandbox full / runaway disk.** Everything the model writes lands in
  `./data`; process logs auto-expire after 7 days. Nuking `./data` is safe (the
  entrypoint re-seeds dotfiles) but loses installed packages and model files.
- **Upgrading.** Pick a release (`https://github.com/open-webui/open-terminal/releases`),
  update tag **and** digest in `compose.yaml` in **both** repos,
  `docker compose pull && docker compose up -d`, confirm `owui-code-exec` passes.
- **Security posture reminder.** Never add a Caddy vhost, never mount the docker
  socket or host paths, keep the port un-forwarded. If it must ever leave the
  LAN, put it behind forward-auth and a per-user isolation review first
  (`OPEN_TERMINAL_MULTI_USER` is explicitly not production-grade).
