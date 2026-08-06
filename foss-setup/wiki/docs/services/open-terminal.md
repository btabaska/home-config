# open-terminal

Open Terminal — server-side code-execution backend for Open WebUI (lai-09,

| | |
|---|---|
| **Host** | [mini](../hosts/mini.md) |
| **URL** | — (no web UI / not proxied) |
| **Source** | `foss-setup/configs/docker-stack/stacks/open-terminal/compose.yaml` |
| **Notes** | Sandboxed code-execution backend for the rig's Open WebUI (lai-09, local-ai buildout) — ghcr.io/open-webui/open-terminal 0.11.34 (tag@digest pinned, full toolkit). Replaces browser Pyodide with a real persistent Linux sandbox; OWUI 0.10.2 wires it as a terminal-server connection (PersistentConfig terminal_server.connections, Bearer key vault open_terminal.api_key) and proxies run_command/files tool calls via /api/v1/terminals/open-terminal/*. DELIBERATELY LAN-only, no Caddy vhost, no Homepage tile (it executes arbitrary code); own compose network, no docker socket, mem/cpu/pids capped. Consumer check owui-code-exec. |
| **Upstream docs** | <https://github.com/open-webui/open-terminal> · <https://docs.openwebui.com/features/open-terminal/> |

## About

Open Terminal is the server-side code-execution backend for the rig's Open WebUI (lai-09, local-ai buildout) — a persistent sandboxed Linux "computer" the models can actually use, replacing the browser-Pyodide default. It runs as `ghcr.io/open-webui/open-terminal:0.11.34` (tag@digest pinned, the full-toolkit variant: Python, Node, build tools, ffmpeg) on the Mac mini at `/opt/stacks/open-terminal`, publishing host `:8020` (container `:8000`) — DELIBERATELY LAN-only with NO Caddy vhost and no Homepage tile, because the whole point of the service is executing arbitrary code. Every API request needs the Bearer key (`OPEN_TERMINAL_API_KEY` in the gitignored `./.env`, vault `open_terminal.api_key`). The subtle part is how OWUI 0.10.2 consumes it: NOT via `CODE_EXECUTION_ENGINE` (that knob only knows pyodide/jupyter, and the run-button endpoint /api/v1/utils/code/execute is jupyter-only server-side) but as a terminal-server connection — PersistentConfig `terminal_server.connections` (DB wins; set via POST /api/v1/configs/terminal_servers, a commented rebuild seed lives in local-ai-tooling docker/.env), after which OWUI reads the sandbox's /openapi.json, injects its tools (run_command, read_file, write_file, grep_search, ...) into chats in Native function-calling mode, and proxies every call through /api/v1/terminals/open-terminal/* with the key held server-side. Isolation: its own compose network (not `edge`), no docker socket, no host mounts beyond `./data` (the sandbox home == /home/user, restic-covered via /opt/stacks), and mem 4g / cpus 2 / pids 512 caps so a runaway loop cannot take the docker host down. The in-container `user` has passwordless sudo BY DESIGN (sandbox apt installs) — root inside the container only. Consumer check: `owui-code-exec` POSTs deterministic arithmetic through the exact OWUI proxy route chat tool calls take and requires the real stdout back.

## Containers

| Service | Image (pinned) | Ports |
|---|---|---|
| `open-terminal` | `ghcr.io/open-webui/open-terminal:0.11.34@sha256:5e040fe357ce4fbd3d5e59c40247dd32172fa10c51c22ded3a7843e739d06a0e` | `8020:8000` |

## Volumes

| Service | Volume |
|---|---|
| `open-terminal` | `./data:/home/user` |

## Environment (`.env`)

Variable names from `.env.example` — real values live in `.env` on the host, sourced from the vault (never committed):

- `OPEN_TERMINAL_API_KEY`

## Troubleshooting

- **owui-code-exec fails with HTTP 404 "Terminal server 'open-terminal' not found" (or the terminal disappeared from OWUI's UI).** — The PersistentConfig connection was erased — an open_webui_data volume wipe or an admin-UI delete (it lives ONLY in webui.db, terminal_server.connections). Re-wire via the admin API: POST /api/v1/configs/terminal_servers with the connection JSON (id open-terminal, url http://192.168.10.2:8020, auth_type bearer, key from vault open_terminal.api_key; OWUI admin key vault ai_stack.openwebui_rag_sync_api_key). The commented TERMINAL_SERVER_CONNECTIONS seed in local-ai-tooling docker/.env re-wires a FRESH volume if uncommented before `docker compose up -d open-webui`.
- **Proxied execution returns 401/403 (or open-terminal answers 401 to direct LAN curl with the key).** — Key mismatch between the OWUI connection and the container: `/opt/stacks/open-terminal/.env` OPEN_TERMINAL_API_KEY must equal the connection's `key` field. Rotate both together — vault first (open_terminal.api_key), then the stack .env + `docker compose up -d`, then re-POST /api/v1/configs/terminal_servers.
- **Commands hang, /execute returns status "running" forever, or the sandbox is out of disk.** — A wedged or runaway process inside the sandbox — `ssh mini 'cd /opt/stacks/open-terminal && docker compose restart'` (state in ./data survives). Disk growth all lands in ./data (packages + files the model writes + process logs; logs auto-expire after 7 days). Nuking ./data is safe (the entrypoint re-seeds dotfiles) but loses installed packages.
- **Someone wants to expose the file-browser UI via Caddy / add a Homepage tile.** — Do not. This service executes arbitrary shell commands with a single shared Bearer key and its multi-user mode is explicitly not production-grade — the LAN-only, no-vhost posture is deliberate (catalog `url: null`, `ui: false`). If remote access is ever truly needed, front it with forward-auth and revisit isolation first.

## Operations

```bash
ssh mini 'cd /opt/stacks/open-terminal && docker compose ps'
ssh mini 'cd /opt/stacks/open-terminal && docker compose logs --tail 50'
ssh mini 'cd /opt/stacks/open-terminal && docker compose pull && docker compose up -d'
```

Update procedure: [Runbooks → Update images](../runbooks/update-images.md). Full add/change loop: [Runbooks → Add a service](../runbooks/add-a-service.md).

*Generated by `scripts/docs/gen-wiki-services.py` — do not edit by hand; edit the compose file and regenerate.*
