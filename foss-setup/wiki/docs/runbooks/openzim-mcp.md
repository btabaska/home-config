# openzim-mcp (ZIM library tools for AI)

Runbook for the `openzim-mcp-search` verification check and the **openzim-mcp** tool
server (lai-13, local-ai buildout) — libzim-native MCP access to the NAS offline ZIM
library for Open WebUI chat and opencode. Library operation itself:
[Kiwix runbook](kiwix.md).

- **Host:** rig (CachyOS, `192.168.10.12`) — runs *inside the mcpo container* (stdio) and
  as opencode-spawned stdio processes; no container of its own
- **Package:** `openzim-mcp==2.5.5` (PyPI, pinned; pulls `libzim<4`, pins `mcp<2` itself
  so it dodges the SDK-2.0 `McpError` rename that broke time/fetch at the 2026-08-03 reboot)
- **Mode:** `--mode advanced` = **8 tools** (`zim_query` NL router, `zim_search`, `zim_get`,
  `zim_get_section`, `zim_browse`, `zim_metadata`, `zim_links`, `zim_health`);
  default `simple` mode would serve only `zim_query`
- **Data:** NAS `zim` share → rig **RO persistent CIFS mount** `/mnt/nas-zim` (dedicated
  low-priv NAS user `zimro`, vault `hosts.nas.zimro_smb_password`; see
  `configs/host/rig/nas-mounts/`) → bind-mounted `ro` into mcpo at `/zim`
- **Config:** `local-ai-tooling/docker/mcpo-config.json` (`openzim` server) +
  `docker/docker-compose.yml` (mcpo `/mnt/nas-zim:/zim:ro` bind) +
  `scripts/seed-owui-tool-servers.sh` (OWUI connection) + `opencode.json` (`mcp.openzim`)
- **Why not OWUI Knowledge/RAG:** ZIMs ship their own Xapian fulltext index — libzim
  searches it natively; re-embedding ~150GB on a CPU 0.6B embedder is absurd (verified
  verdict, memory `local-claude-buildout`)

## Consumer topology

| Consumer | Path | Tools visible |
|---|---|---|
| Open WebUI | `http://mcpo:8000/openzim` (OpenAPI bridge) | **3 of 8** — `zim_query` + `zim_search` + `zim_get` (operationId filter `tool_zim_*_post`); OWUI total 40/40 |
| opencode (rig) | own stdio spawn: `uvx openzim-mcp==2.5.5 --mode advanced /mnt/nas-zim` | all 8 (build + plan agents, `openzim*` glob) |
| verification / scripts | `http://192.168.10.12:8000/openzim/<tool>` POST | all 8 |
| **Mac opencode** | **NOT wired** — deliberate | — |

The Mac is rig-side-only by design: mcpo speaks OpenAPI (not MCP), so the Mac's opencode
can't consume it without a bridge, and a Mac-local stdio spawn would need its own
persistent SMB mount of the zim share — maintenance for near-zero value. Use OWUI or run
opencode on the rig (`rig-code`).

## The consumer check

`openzim-mcp-search` (in `verification/checks.d/local-ai.yaml`, from the mini):

1. `POST /openzim/zim_search` on the iFixit ZIM (`battery replacement`) must return real
   Xapian results;
2. `POST /openzim/zim_get` on the first hit must return an article whose content mentions
   the search term and is non-trivially sized.

That one round-trip proves: mcpo up → openzim-mcp process healthy → `/zim` bind present →
rig CIFS mount alive → NAS share serving → libzim reads the actual ZIM. It pins the
iFixit *filename* (`ifixit_en_all_2025-12.zim`) — same pinned-filename convention as the
download queue; growth of the library never breaks it, but **refreshing the iFixit ZIM to
a newer date means updating the filename in the check** (repo + deployed copy).

```bash
VERIFICATION_STATE_DIR=$(mktemp -d) /opt/verification/bin/run-checks.sh --no-notify --check openzim-mcp-search
```

## Common failures

| Symptom | Cause / fix |
|---|---|
| Check fails, every `/openzim/*` call errors | mcpo lost the openzim subprocess — `docker logs mcpo`; `cd ~/Documents/GitHub/local-ai-tooling/docker && docker compose up -d --force-recreate mcpo` (uvx re-resolves on start, needs outbound net once) |
| "Security Validation Error" on a path | The `zim_file_path` isn't under the allowed dir — inside mcpo the library is `/zim/<file>.zim` (NOT `/mnt/nas-zim/...`); for opencode it IS `/mnt/nas-zim/<file>.zim` |
| Empty file list / mount dead | Rig CIFS mount: `findmnt /mnt/nas-zim || sudo systemctl reset-failed; sudo mount /mnt/nas-zim`; then recreate mcpo (a bind over a re-made mount does NOT propagate into the running container) |
| Auth failures on the mount | NAS side: `zimro` user or `zim` share perms changed — share is `btabaska` RW / `zimro` RO + ACLs (see `configs/nas/kiwix/README.md`); password at vault `hosts.nas.zimro_smb_password` → `/etc/samba/cred-nas-zim` |
| OWUI chat can't see zim tools | PersistentConfig wipe — re-run `scripts/seed-owui-tool-servers.sh` (OWUI budget incl. openzim = 40/40; guarded by `owui-mcp-tools`) |
| opencode `openzim failed: uvx not found` | Non-login shell PATH artifact — `uvx` is `~/.local/bin`; real sessions (login shell) are fine |
| Searches slow / time out | NAS under heavy I/O (Wikipedia queue still running, or a scrub) — expected while the library grows; the check has generous timeouts |

## Upgrade

Bump the `openzim-mcp==X.Y.Z` pin in **four places, same commit**:
`docker/mcpo-config.json`, root `opencode.json` + `clients/opencode.json` +
`agentic/opencode/opencode.json` (byte-identical — `opencode-config-parity` enforces it),
deploy the live `~/.config/opencode/opencode.json`, recreate mcpo, then re-run the
`openzim-mcp-search` check and `opencode mcp list`.
