# Checks — local-ai

`foss-setup/verification/checks.d/local-ai.yaml` — 7 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `searxng-json-probe`

SearXNG JSON API returns real results (lai-01 consumer end)

- **host:** `mini` · **severity:** `warn` · **guards task:** `lai-01` · **enabled:** True
- **expects:** `^SEARXNG_OK `

```bash
r=$(curl -s -m 20 'http://127.0.0.1:8888/search?q=wikipedia&format=json' | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('results',[])))" 2>/dev/null); if [ "${r:-0}" -gt 0 ] 2>/dev/null; then echo "SEARXNG_OK results=$r"; else sleep 3; r=$(curl -s -m 20 'http://127.0.0.1:8888/search?q=debian+linux&format=json' | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('results',[])))" 2>/dev/null); if [ "${r:-0}" -gt 0 ] 2>/dev/null; then echo "SEARXNG_OK results=$r retry=1"; else echo "SEARXNG_BAD results=${r:-invalid}"; fi; fi
```

## `rerank-spread`

llama-swap /v1/rerank scores relevant >> irrelevant (lai-02 broken-GGUF guard)

- **host:** `url` · **severity:** `warn` · **guards task:** `lai-02` · **enabled:** True
- **expects:** `^RERANK_OK `

```bash
python3 -c "import json,urllib.request; body=json.dumps({'model':'qwen3-reranker','query':'How do I restart a systemd service on Linux?','documents':['Use systemctl restart nginx.service to restart the unit, then systemctl status to confirm it is active again.','My favorite pancake recipe uses two eggs, a cup of flour, some milk and a pinch of salt.']}).encode(); req=urllib.request.Request('http://cachyos.tailb31641.ts.net:9292/v1/rerank', data=body, headers={'Content-Type':'application/json'}); r=json.load(urllib.request.urlopen(req, timeout=180)); s={d['index']:d['relevance_score'] for d in r['results']}; ok=s[0]>=0.5 and (s[0]-s[1])>=0.4; print(('RERANK_OK' if ok else 'RERANK_BAD')+' rel=%.4f irr=%.4f spread=%.4f'%(s[0],s[1],s[0]-s[1]))"
```

## `owui-agentic-search`

OWUI web search consumer path returns SearXNG-sourced pages (lai-03)

- **host:** `mini` · **severity:** `warn` · **guards task:** `lai-03` · **enabled:** True
- **expects:** `^OWUI_SEARCH_OK `

```bash
w=$(curl -s -m 15 -H "Authorization:Bearer $OWUI_API_KEY" "$OWUI_URL/api/v1/retrieval/config" | python3 -c 'import sys,json;d=json.load(sys.stdin);b=d.get("web",{});print("WIRED" if (b.get("ENABLE_WEB_SEARCH") and b.get("WEB_SEARCH_ENGINE")=="searxng" and b.get("SEARXNG_QUERY_URL","").startswith("http://192.168.10.2:8888/search") and d.get("ENABLE_RAG_HYBRID_SEARCH") and d.get("RAG_RERANKING_ENGINE")=="external" and d.get("RAG_RERANKING_MODEL")=="qwen3-reranker") else "DRIFT")' 2>/dev/null); if [ "$w" != "WIRED" ]; then echo "OWUI_SEARCH_BAD config=${w:-noresponse}"; else n=$(curl -s -m 110 -X POST -H "Authorization:Bearer $OWUI_API_KEY" -H "Content-Type:application/json" -d "{\"queries\":[\"debian stable release\"]}" "$OWUI_URL/api/v1/retrieval/process/web/search" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(int(d.get("loaded_count") or 0))' 2>/dev/null); if [ "${n:-0}" -gt 0 ] 2>/dev/null; then echo "OWUI_SEARCH_OK loaded=$n"; else sleep 5; n=$(curl -s -m 110 -X POST -H "Authorization:Bearer $OWUI_API_KEY" -H "Content-Type:application/json" -d "{\"queries\":[\"linux kernel news\"]}" "$OWUI_URL/api/v1/retrieval/process/web/search" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(int(d.get("loaded_count") or 0))' 2>/dev/null); if [ "${n:-0}" -gt 0 ] 2>/dev/null; then echo "OWUI_SEARCH_OK loaded=$n retry=1"; else echo "OWUI_SEARCH_BAD loaded=${n:-invalid}"; fi; fi; fi
```

## `owui-mcp-tools`

OWUI native MCP tool servers wired + visible-tool budget (lai-04)

- **host:** `mini` · **severity:** `warn` · **guards task:** `lai-04` · **enabled:** True
- **expects:** `^OWUI_MCP_OK `

```bash
python3 /opt/verification/bin/owui-mcp-tools.py
```

## `opencode-config-parity`

rig live opencode config == repo canonical AND pinned version installed (lai-05)

- **host:** `rig` · **severity:** `warn` · **guards task:** `lai-05` · **enabled:** True
- **expects:** `OPENCODE-CONFIG-PARITY-OK`

```bash
cd ~/Documents/GitHub/local-ai-tooling && pin=$(cat clients/opencode.version) && ver=$($HOME/.opencode/bin/opencode --version 2>/dev/null | tail -1) && c1=$(sha256sum opencode.json | cut -c1-64) && l1=$(sha256sum $HOME/.config/opencode/opencode.json | cut -c1-64) && c2=$(sha256sum agentic/opencode/dcp.jsonc | cut -c1-64) && l2=$(sha256sum $HOME/.config/opencode/dcp.jsonc | cut -c1-64) && c3=$(sha256sum clients/opencode.json | cut -c1-64) && c4=$(sha256sum agentic/opencode/opencode.json | cut -c1-64) && echo "ver=$ver pin=$pin cfg live=${l1:0:12} repo=${c1:0:12} dcp live=${l2:0:12} repo=${c2:0:12}" && { [ -n "$pin" ] && [ "$ver" = "$pin" ] && [ "$c1" = "$l1" ] && [ "$c2" = "$l2" ] && [ "$c3" = "$c1" ] && [ "$c4" = "$c1" ]; } && echo OPENCODE-CONFIG-PARITY-OK
```

## `opencode-run-probe`

opencode run completes a real completion through LiteLLM on the rig (lai-05)

- **host:** `rig` · **severity:** `warn` · **guards task:** `lai-05` · **enabled:** True
- **expects:** `^OPENCODE_RUN_OK`

```bash
export LITELLM_API_KEY="$(grep -s "^CODING_LITELLM_KEY=" "$HOME/Documents/GitHub/local-ai-tooling/docker/.env" | cut -d= -f2-)" && cd /tmp && out=$(timeout 240 $HOME/.opencode/bin/opencode run -m litellm/utility "Reply with exactly: E2E_PROBE_OK. Do not use any tools." 2>/dev/null); if echo "$out" | grep -q "E2E_PROBE_OK"; then echo "OPENCODE_RUN_OK"; else echo "OPENCODE_RUN_BAD tail=$(echo "$out" | tail -c 160 | tr "\n" " ")"; fi
```

## `skills-manifest-parity`

rig live skill roots match skills-manifest.yaml + catalog cap (lai-06)

- **host:** `rig` · **severity:** `warn` · **guards task:** `lai-06` · **enabled:** True
- **expects:** `SKILLS-MANIFEST-PARITY-OK`

```bash
cd ~/Documents/GitHub/local-ai-tooling && want=$(grep -E '^ *- skill: ' agentic/opencode/skills-manifest.yaml | awk '{print $NF}' | sort) && have=$(ls -1 $HOME/.claude/skills | sort) && n=$(printf '%s\n' "$have" | grep -c .) && m=$(ls -1 $HOME/.config/opencode/skills | grep -c .) && total=$((n+m)) && echo "claude=$n opencode=$m total=$total cap=40" && [ "$want" = "$have" ] && diff -rq agentic/opencode/skills "$HOME/.config/opencode/skills" >/dev/null && [ "$total" -le 40 ] && echo SKILLS-MANIFEST-PARITY-OK
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
