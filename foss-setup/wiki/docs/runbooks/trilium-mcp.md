# trilium-mcp (notes tools for AI)

Runbook for the `trilium-mcp-search-probe` verification check and the **trilium** tool
server (lai-16, local-ai buildout) — MCP access to the self-hosted [Trilium
trial](notes-trilium.md) so Open WebUI chat and opencode can search + read your notes.

> **This rides the revertable Trilium trial.** Trilium (read-27) is an
> Obsidian-replacement *trial*. If it is torn down or reverts to Obsidian,
> trilium-mcp retires **with** it — `scripts/notes-trial/teardown-trilium.sh` removes
> this check + the ETAPI token; the Obsidian path would use
> `obsidian-local-rest-api`'s built-in `/mcp/` endpoint instead.

- **Host:** rig (CachyOS, `192.168.10.12`) — runs *inside the mcpo container* (stdio) and
  as an opencode-spawned stdio process; no container of its own
- **Server:** [`OVDEN13/trilium-mcp`](https://github.com/OVDEN13/trilium-mcp) **v0.1.5**
  — a single **static Go binary** (no runtime deps), pinned + sha256-verified by
  `local-ai-tooling/scripts/fetch-trilium-mcp.sh` (the binary is a rebuildable artifact,
  `.gitignore`d like the model GGUFs). Bind-mounted `ro` into mcpo at `/opt/trilium-mcp`.
- **Tools:** 16 ETAPI tools. **Read:** `search_notes`, `get_note`, `get_note_subtree`,
  `list_attributes`. **Write (NOT exposed anywhere by default):** `create_note`,
  `batch_create_notes`, `update_note`, `append_content`, `delete_note`,
  `batch_delete_notes`, `move_note`, `clone_note`, `delete_branch`, `add_label`,
  `add_relation`, `remove_attribute`.
- **Read-mostly posture:** the MCP is young (v0.1.5) and writes to the user's real notes,
  so **both** OWUI and opencode are wired **read-only** for now. Revisit write access
  (opencode build/plan agents only) once the server matures.
- **Backend:** `TRILIUM_URL=https://trilium.tabaska.us` (resolves to the mini `.2` via
  AdGuard; Caddy vhost routes to the `trilium` container — the trial is edge-only, no
  host port) + `TRILIUM_TOKEN` = an **ETAPI token**. The token is passed via the **mcpo
  container env** (compose `environment:` ← `docker/.env TRILIUM_ETAPI_TOKEN`, gitignored)
  — mcpo merges its env into every stdio subprocess (`{**os.environ, **cfg.env}`), so the
  committed `mcpo-config.json` carries **no secret**. opencode reads the same value via
  `{env:TRILIUM_ETAPI_TOKEN}` (exported in the rig `~/.bashrc` from `docker/.env`).
- **Config:** `local-ai-tooling/docker/mcpo-config.json` (`trilium` server) +
  `docker/docker-compose.yml` (mcpo `./trilium-mcp:/opt/trilium-mcp:ro` bind + env) +
  `scripts/seed-owui-tool-servers.sh` (OWUI connection) + `opencode.json` (`mcp.trilium`).

## The ETAPI token

The trial's single-user login password was set interactively at first-run (read-27) and
is **unrecorded**, so `POST /etapi/auth/login` was unavailable. The token was minted by a
**direct `etapi_tokens` row insert** into the trial's `document.db` (a becca entity loaded
from its table at startup; Trilium's consistency check self-heals the missing
`entity_changes` row) + a `docker restart trilium`. Token format is `<etapiTokenId>_<hex>`,
sent as the `Authorization` header. Stored at vault **`trilium.etapi_token`**
(+ `trilium.url`, `trilium.probe_note_id`).

- **Rotate/revoke:** `DELETE FROM etapi_tokens WHERE ...` in `document.db` (or via the
  Trilium UI Options → ETAPI once you know the password), restart trilium, then re-mint,
  update vault + `docker/.env` + recreate mcpo. A revoked token → search returns 0 /
  `get_note` errors → the check goes RED.

## Consumer topology

| Consumer | Path | Tools visible |
|---|---|---|
| Open WebUI | `http://mcpo:8000/trilium` (OpenAPI bridge) | **2 of 16** — `search_notes` + `get_note` (operationId filter `tool_search_notes_post,tool_get_note_post`); OWUI total **40/40** |
| opencode (rig) | own stdio spawn of the pinned binary | **4 read tools** (build + plan agents: `trilium_search_notes/get_note/get_note_subtree/list_attributes`; writes off) |
| verification / scripts | `http://192.168.10.12:8000/trilium/<tool>` POST | all 16 |
| **Mac opencode** | **NOT wired** — deliberate | — |

The Mac is rig-side-only by design (the binary path + token are rig-local; mcpo speaks
OpenAPI, not MCP). Use OWUI or run opencode on the rig (`rig-code`).

> **OWUI budget:** adding trilium's read pair would have pushed OWUI to 41 tools (cap 40,
> guarded by `owui-mcp-tools` — small-model routing degrades past ~40). Room was freed by
> dropping serena's `tool_onboarding` from the OWUI filter (it *writes* project memories,
> so it never belonged in a read-only chat surface): serena 10→9, +trilium 2 = **40**.

## The consumer check

`trilium-mcp-search-probe` (in `verification/checks.d/local-ai.yaml`, from the mini):

1. `POST /trilium/search_notes` for the sentinel `TRILIUMMCPPROBESENTINEL` must return a
   hit;
2. `POST /trilium/get_note` (`include_content:true`) on that hit must return a note body
   containing the sentinel and non-trivially sized.

That one round-trip proves: mcpo up → trilium-mcp subprocess healthy → ETAPI token valid →
Trilium trial serving → a real note's content read. It targets a **dedicated stable marker
note** created via ETAPI as the check's fixed target — **"Fleet ETAPI Probe (lai-16)"**,
noteId **`Kw6fnQALxAH3`**, a root child (vault `trilium.probe_note_id`). Its body carries
the sentinel and a "do not delete/rename" banner, so ordinary trial-content churn never
breaks the check.

```bash
VERIFICATION_STATE_DIR=$(mktemp -d) /opt/verification/bin/run-checks.sh --no-notify --check trilium-mcp-search-probe
```

## Common failures

| Symptom | Cause / fix |
|---|---|
| Check fails, every `/trilium/*` call errors | mcpo lost the trilium subprocess — `docker logs mcpo`; `cd ~/Documents/GitHub/local-ai-tooling/docker && docker compose up -d --force-recreate mcpo` |
| `hits=0` but Trilium is up | Marker note deleted/renamed, or ETAPI token revoked/expired → re-create the marker via ETAPI (title "Fleet ETAPI Probe (lai-16)", body with `TRILIUMMCPPROBESENTINEL`), or re-mint the token (see above) |
| `get_note` errors / empty content | Token invalid, or Trilium mid-restart — check `curl -H "Authorization: $TOK" https://trilium.tabaska.us/etapi/app-info` |
| opencode `trilium failed` | Binary missing — `bash scripts/fetch-trilium-mcp.sh` (re-downloads + sha256-verifies); or `TRILIUM_ETAPI_TOKEN` not exported (login shell sources `~/.bashrc`) |
| OWUI chat can't see trilium tools | PersistentConfig wipe — re-run `scripts/seed-owui-tool-servers.sh` (budget guarded by `owui-mcp-tools`) |
| Whole thing gone after a trial teardown | Expected — trilium-mcp retires with the Trilium trial |

## Upgrade

Bump the pinned version in `scripts/fetch-trilium-mcp.sh` (`VERSION` + `SHA256` from the
release `.sha256`), re-run it on the rig, recreate mcpo, then re-run the
`trilium-mcp-search-probe` check + `opencode mcp list`. The `mcpo-config.json` command path
is version-agnostic (fixed binary name), so no other file changes for a patch bump.
