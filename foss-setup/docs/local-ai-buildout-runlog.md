# Local-AI buildout — close-out runlog (lai-01…lai-20)

> **What this is:** the close-out record for the "local Claude / Claude Code equivalent" build-out
> (run 12, `lai-*`). It ships the fleet a private search + research stack, a local coding agent
> (opencode), voice + image + browser tools, an offline knowledge/maps layer, and an agent-memory
> layer — all served by the rig's single-GPU llama-swap and the mini's CPU services, monitored
> consumer-end by 20 new checks in `verification/checks.d/local-ai.yaml`.
> **Source of the plan:** the 2026-08-05 deep-research verdicts (memory `local-claude-buildout`,
> report artifact `https://claude.ai/code/artifact/330f997e-b41f-4d92-a753-a82f45c9ad94`).
> **Final state:** 18 items DONE (lai-01…14, 16, 17, 18, 19), 1 DEFERRED (lai-15, Cloudflare-blocked),
> this close-out (lai-20) DONE, and one open follow-up task registered (lai-21, OWUI 0.11.0 upgrade).

---

## 1. Shipped items

| id | title | one-line outcome | commit |
|----|-------|------------------|--------|
| `lai-01` | SearXNG metasearch (mini) | Private metasearch live `searxng.tabaska.us` + `:8888` JSON API (formats html+json, limiter off) — the OWUI web-search backend; replaces Kagi | `61a94ea` |
| `lai-02` | Local reranker (rig) | Official ggml-org Qwen3-Reranker-0.6B-Q8_0 (sha-pinned) as a separate CPU llama-server entry; real relevance spread verified | `859e125` |
| `lai-03` | OWUI search + RAG pass | Native web-search via SearXNG + hybrid RAG through the external qwen3-reranker; all set via admin REST API (PersistentConfig DB wins) | `fd7ed2a` |
| `lai-04` | OWUI MCP → native | fleet-mcp (rig `:8765/mcp`) + context7 connected as native streamable-HTTP MCP; mcpo kept for stdio bridges only | `be9facc` |
| `lai-05` | opencode (Mac + rig) | opencode pinned 1.18.10 (autoupdate off) + 6-plugin array; canonical config dual-homed repo↔rig; run-probe completes a real LiteLLM completion | `605e4fa` |
| `lai-06` | Skills bundle (Mac + rig) | 34-skill curated catalog (23 claude-code + 11 opencode), cap ≤40, names-only manifest + parity check | `a954df0` |
| `lai-07` | Pin last rolling images | rig AI stack fully digest-pinned (llama-swap, litellm, open-webui, mcpo, comfyui) — the fleet's last unpinned tags | `a286d21` |
| `lai-08` | local-deep-research (rig) | LDR 1.10.1 live `ldr.tabaska.us` / `:5000` — cited research via LiteLLM coder-strong + mini SearXNG | `12fa3f6` |
| `lai-09` | open-terminal code-exec | open-terminal sandbox on mini `:8020` (LAN-only, Bearer-keyed) wired into OWUI as the terminal server; real code round-trip | `ac98f5c` |
| `lai-10` | Voice (TTS + STT) | Kokoro-FastAPI CPU TTS on rig `:8880` + mini faster-whisper STT `:8010` wired into OWUI Audio; round-trip verified | `97bd2ad` |
| `lai-11` | Image / browser tools | OWUI image gen+edit = ComfyUI via gpu-arbiter; comfyui-mcp `:9000` + playwright-mcp `:8931` native MCP | `9fa5286` |
| `lai-12` | kiwix-serve ZIM library (NAS) | kiwix-serve 3.8.2 live `kiwix.tabaska.us` / NAS `:8092` over `/volume1/zim` (~150GB curated incl. Wikipedia en maxi 116G) | `aa17a13` |
| `lai-13` | openzim-mcp | openzim-mcp 2.5.5 over the NAS ZIM library (NAS share → rig RO CIFS → mcpo/opencode); AI-side ZIM search+fetch | `26f9605` |
| `lai-14` | GameFAQs private corpus | PRIVATE GameFAQs full-text ZIM (143,376 FAQs, libzim Xapian) served LAN-only from NAS kiwix | `f4ffcbd` |
| `lai-15` | StrategyWiki ZIM | **DEFERRED** — Cloudflare fingerprints+403s mwoffliner's Node client; pipeline fully scaffolded + self-detecting, check green in mode=blocked | `1c0eb0a` |
| `lai-16` | trilium-mcp | trilium-mcp v0.1.5 (read-mostly) over the read-27 Trilium trial ETAPI via mcpo/opencode | `064513f` |
| `lai-17` | Offline maps | `maps.tabaska.us` — CONUS PMTiles extract (pmtiles `:8899`) + Photon US geocoder (`:2322`) + OSM MCP; fully offline viewer | `5667fd0` |
| `lai-18` | Agent memory layer | DIY ~130-line opencode memory plugin (session.idle/compacting → local model → dated MEMORY.md) + OWUI native Memory finding | `2a8bb42` |
| `lai-19` | Consolidation sweep | Completeness audit + additive gap-fix over lai-01..18: coverage complete all hosts, wiki `--strict` clean, Homepage tiles resolve, all 3 repos clean+dual-pushed, Wikipedia 116G wired into kiwix | `72dd86c` |
| `lai-20` | Buildout close-out | This runlog + full-fleet audit-safe verification run (below) + ledger + publish | _this commit_ |

Ledger registration commit (lai-01…lai-20 seeded): `2cf6c28`.
`lai-21` (Open WebUI 0.11.0 upgrade — sub-agents + startup-cached tool descriptions) is an **open** follow-up task, not part of this buildout's shipped set.

---

## 2. New / changed services and endpoints

| service | host | endpoint | purpose |
|---------|------|----------|---------|
| SearXNG | mini | `searxng.tabaska.us`, `:8888` | private metasearch + JSON API (OWUI/LDR web-search backend) |
| qwen3-reranker | rig | llama-swap `:9292/v1/rerank` | CPU reranker for OWUI hybrid RAG |
| local-deep-research | rig | `ldr.tabaska.us`, `:5000` | cited multi-source research (per-user SQLCipher login) |
| open-terminal | mini | `:8020` (LAN, Bearer) | OWUI server-side code execution sandbox |
| Kokoro-FastAPI | rig | `:8880` | CPU TTS (OWUI voice out) |
| faster-whisper | mini | `:8010` | CPU STT (OWUI voice in) — shared with journaling |
| comfyui-mcp / playwright-mcp | rig | `:9000/mcp`, `:8931/mcp` | image gen/edit + headless browser MCP tools |
| kiwix-serve | NAS | `kiwix.tabaska.us`, `:8092` | offline ZIM knowledge library (~150GB) |
| openzim-mcp | rig | mcpo `:8000/openzim` | AI-side ZIM search/fetch |
| trilium-mcp | rig | mcpo `:8000/trilium` | notes MCP over the Trilium trial (read-mostly) |
| maps (pmtiles + photon) | mini | `maps.tabaska.us` (`:8899`, `:2322`) | offline US basemap + geocoder |

MCP wiring (`lai-04/11/13/16`): fleet-mcp + context7 native; time/fetch/serena/seq-thinking/openzim/trilium/comfyui/playwright via the mcpo bridge or native, OWUI-visible tool budget held ≤40.

---

## 3. Monitoring — the 20 local-ai consumer checks

All in `verification/checks.d/local-ai.yaml`, severity `warn`, consumer-end (not liveness). GPU-heavy
ones are `tier: daily` and best-effort-aware (skip-as-pass under VRAM contention).

| check id | task | what it proves (consumer end) |
|----------|------|-------------------------------|
| `searxng-json-probe` | lai-01 | `/search?...&format=json` returns real results (guards format/limiter/DNS breakage) |
| `rerank-spread` | lai-02 | reranker scores relevant ≫ irrelevant (guards the broken-GGUF near-zero-score mode) |
| `owui-agentic-search` `daily` | lai-03 | OWUI web-search config wired + `/retrieval/process/web/search` returns loaded SearXNG pages |
| `owui-mcp-tools` | lai-04 | real MCP handshake with fleet-mcp + both native connections registered + tool budget ≤40 |
| `opencode-config-parity` | lai-05 | rig live opencode config == repo canonical + pinned version installed |
| `opencode-run-probe` `daily` | lai-05 | opencode completes a real completion through LiteLLM→llama-swap on the rig |
| `skills-manifest-parity` | lai-06 | rig skill roots == manifest + catalog cap ≤40 |
| `ai-images-pinned` | lai-07 | rig AI-stack compose digest-pinned + running containers match |
| `ldr-research-e2e` `daily` | lai-08 | LDR completes a cited SearXNG+coder-strong research (GPU-busy → skip-pass) |
| `owui-code-exec` | lai-09 | OWUI terminal proxy runs real code on the mini open-terminal sandbox |
| `voice-roundtrip` `daily` | lai-10 | Kokoro TTS → mini whisper STT round-trip + OWUI audio config wired |
| `image-browser-mcp` | lai-11 | comfyui-mcp + playwright-mcp handshake/nav + OWUI image-engine config |
| `kiwix-search-consumer` | lai-12 | Kiwix library breadth + real Xapian search → article fetch |
| `openzim-mcp-search` | lai-13 | openzim-mcp real ZIM search + article fetch via mcpo (full CIFS chain) |
| `gamefaqs-zim-search` | lai-14 | private GameFAQs ZIM real search → FAQ fetch (with PRIVATE-archive marker) |
| `strategywiki-zim-present` | lai-15 | pipeline health / real search once landed (green in mode=blocked) |
| `trilium-mcp-search-probe` | lai-16 | trilium-mcp real note search + content fetch via mcpo |
| `maps-pmtiles-serve` | lai-17 | offline US map serves a real gzipped MVT vector tile via Caddy |
| `maps-photon-geocode` | lai-17 | Photon US geocoder returns a CONUS feature (build-mode aware) |
| `agent-memory-plugin` | lai-18 | opencode memory plugin present+valid on rig AND a well-formed MEMORY.md exists |

---

## 4. Final full-fleet audit-safe verification run

Run 2026-08-06 from the mini runner as `btabaska`, ALL hosts/domains, audit-safe
(`VERIFICATION_STATE_DIR=$(mktemp -d)` + `--no-notify` — isolated state, no paging), including
every `tier: daily` check. Sequential runner (no parallel NAS fan-out), ~9 min wall.

**Result: 360 passed / 377 run / 383 defined · 17 failed · 1 crit · 6 skipped (disabled).**

Reference baseline: the post-fleet-sweep audit-safe run (2026-08-02) was **343/362, 0 crit**; the
buildout added **20 local-ai checks** (§3), so the expected shape is ~363/382. Actual defined 383
(+21 = the 20 lai checks + net check churn from `fix-*` closures since 08-02).

**All 20 local-ai checks PASSED** — zero AI-stack regressions. The `ldr-research-e2e`,
`opencode-run-probe`, and `voice-roundtrip` daily best-effort checks all completed green (no GPU-busy
skips were needed this run).

### Triage of every non-pass (17)

**(c) Genuine lai-introduced drift — FIXED this session (additive/safe):**

- `lan-listeners-drift-mini` — `mini:2322,8020,8888,8899` (photon/lai-17, open-terminal/lai-09,
  searxng/lai-01, pmtiles/lai-17)
- `lan-listeners-drift-rig` — `rig:5000,8880,8931,9000` (ldr/lai-08, kokoro/lai-10,
  playwright-mcp/lai-11, comfyui-mcp/lai-11)
- `lan-listeners-drift-nas` — `nas:8092` (kiwix/lai-12)

  The buildout published 9 new all-interface service ports (all documented, intended LAN/tailnet
  exposures per the service catalog — the same accepted flat-VLAN posture as the rest of the fleet,
  Caddy is the auth edge) but the `fix-51` intended-exposure baselines were never updated.
  **Resolved here:** the 9 ports were codified in `verification/assets/expected-listeners/{mini,rig,nas}.ports`
  (repo + deployed to `/opt/verification`), and all three checks re-verified `LISTENER_DRIFT=NONE`.
  This is the only regression class the AI buildout introduced, and it is closed.

**(b) Best-effort GPU / AI-stack contention artifact (not a regression):**

- `rig-crash-storm-quiet` (`fix-64`) — `CRASH_STORM 60 llama-server`. All 60 were SIGSEGV in a tight
  10-minute window (10:38→10:48 EDT), a llama-swap `fast-3b` "upstream command exited prematurely"
  crash-loop — the documented `rig-gpu-vram-contention` pattern (single-3090 Ti VRAM contention →
  premature model-load exit; "contention is policy, not an incident"). Self-healed by 10:49; **0
  crashes in the audit window and since**, and every AI consumer check (incl. `opencode-run-probe`,
  which loads `fast-3b`) is green. The check correctly caught a real transient; it will clear on its
  own once the morning's coredumps age past the 24h window. Not lai-attributable.

**(a) Pre-existing / expected residuals (NOT regressions, none lai-related) — 13:**

| check | task | note |
|-------|------|------|
| `arr-grabbed-not-imported` **CRIT** | fix-25 | known media-import flap (in `progress.json.reopened`); also crit at the 10:28 scheduled run — transient, pre-existing |
| `alert-kuma-none-down` | sec-03 | the "1 Kuma monitor to eyeball on /status/fleet" residual (CLAUDE.md Current priority) |
| `immich-user-zero-assets` | fix-60 | Kaelyn must enable backup on her device (CLAUDE.md residual) |
| `sys-docker-subnet-squat` | ha-19 | docker subnet squatters → open task ha-19 (CLAUDE.md residual) |
| `nas-immich-backup-freshness` | fix-35 | known Immich backup-freshness residual (reopened ledger) |
| `nas-immich-ffmpeg-nocrash` | fix-60 | known ffmpeg segfault on one corrupt .mov |
| `bazarr-synced-from-arrs` | media-12 | pre-existing probe traceback (media subtitles) |
| `nas-jellyfin-serves` | media-05 | pre-existing probe traceback (jellyfin) |
| `sonarr-queue-stuck` | verify-06 | pre-existing media-queue residual |
| `nas-core-dumps` | fix-45 | pre-existing NAS core-dump residual |
| `game-playit-udp-register-errors` | fix-34 | pre-existing playit UDP-register residual |
| `mini-scratch-hygiene` | fix-69 | pre-existing scratch-file hygiene residual |
| `unpackerr-host-retired` | fix-69 | pre-existing unpackerr host-unit residual |

**Skipped (6, all deliberately disabled — not failures):** `ha-hacs-loaded`,
`meme-review-{api-health,spa-served,auth-wall}`, `nas-immich-mobile-paired`, `sys-seedbox-ssh`.

**Bottom line:** zero genuine AI-stack regressions from lai-01…19; the only lai-attributable
failures (3 listener-drift checks) were closed additively this session. Effective post-fix state:
**363/377 pass**, with the remaining non-pass being 1 pre-existing media-flap crit + 12 documented
warn residuals + 1 self-healed transient — none introduced by this buildout.

---

## 5. Human follow-ups (LISTED, not actioned — additive/read-only close-out)

1. **[SECURITY, urgent] Rotate `sudo.rig_password`.** During lai-13's NAS-mount credential write, a
   cached-sudo stdin fall-through wrote the rig sudo password into the cred file's first line and a
   verification `head` echoed it into that subagent's transcript. The file was immediately rewritten
   clean (verified), but the secret **value** was exposed in a transcript. Rotate it following the
   security-change-guard protocol (consumer inventory → vault-first store+read-back → walk consumers
   → negative-test old value dead → rollback plan first). Details in `configs/host/rig/nas-mounts/`
   README + the lai-13 progress note.
2. **Subscribe a phone to the ntfy topic `opencode`** (`opencode-ntfy.sh`). The daily ~07:15
   "Agent Idle" probe ping from `opencode-run-probe` is expected, not an error.
3. **Register an operator account at `ldr.tabaska.us`** (local-deep-research; open registration,
   per-user SQLCipher-encrypted DB — passwords are unrecoverable by design).
4. **File the public openZIM zim-request for `strategywiki.org`** (openZIM infra handles Cloudflare),
   then add the resulting `.zim` URL to the NAS `zim-download-queue.sh`. This is the real path to a
   StrategyWiki ZIM (unblocks the deferred lai-15).
5. **Trilium-vs-Obsidian decision at trial end** — `trilium-mcp` (lai-16) retires with the read-27
   trial if it reverts to Obsidian.
6. **Decide whether Kagi is fully retired or kept as a fallback** search engine (SearXNG replaced it
   in OWUI).
7. **Schedule the OWUI 0.11.0 upgrade window** — registered as open task `lai-21` (sub-agents +
   startup-cached tool descriptions; re-verify OWUI PersistentConfig env keys at the upgrade).

---

## 6. Ledger state (consistency check)

- **DONE (19):** lai-01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 16, 17, 18, 19, **20**.
- **DEFERRED (1):** lai-15 (Cloudflare mwoffliner block; scaffolded + self-detecting).
- **OPEN follow-up (1):** lai-21 (OWUI 0.11.0 upgrade).

Total `lai-*` = 21 registered = 19 done + 1 deferred + 1 open. Regenerated `todo.md` +
roadmap pages after marking lai-20 done.
