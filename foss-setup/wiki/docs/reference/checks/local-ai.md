# Checks — local-ai

`foss-setup/verification/checks.d/local-ai.yaml` — 25 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

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

## `ai-images-pinned`

rig AI-stack compose digest-pinned + running containers match (lai-07)

- **host:** `rig` · **severity:** `warn` · **guards task:** `lai-07` · **enabled:** True
- **expects:** `AI-IMAGES-PINNED-OK`

```bash
cd ~/Documents/GitHub/local-ai-tooling && rolling=$(grep -E '^ *image: ' docker/docker-compose.yml | grep -v '@sha256:' | grep -cE ':(latest|main|main-latest|cuda|nightly|dev)[[:space:]]*$'); fails=""; for s in llama-swap litellm open-webui mcpo comfyui; do img=$(awk -v s="$s" '$1=="image:"{i=$2} $1=="container_name:"&&$2==s{print i}' docker/docker-compose.yml); dig=${img#*@}; case "$img" in *@sha256:*) rd=$(docker image inspect "$(docker inspect -f '{{.Image}}' "$s" 2>/dev/null)" -f '{{range .RepoDigests}}{{.}} {{end}}' 2>/dev/null); case "$rd" in *"$dig"*) : ;; *) fails="$fails $s:running-digest-mismatch" ;; esac ;; *) fails="$fails $s:compose-unpinned" ;; esac; done; echo "rolling_tags=$rolling fails=${fails:-none}"; [ "${rolling:-1}" = "0" ] && [ -z "$fails" ] && echo AI-IMAGES-PINNED-OK
```

## `ldr-research-e2e`

local-deep-research completes a cited SearXNG+coder-strong research (lai-08)

- **host:** `rig` · **severity:** `warn` · **guards task:** `lai-08` · **enabled:** True
- **expects:** `^LDR_E2E_(OK|SKIP_GPU_BUSY)`

```bash
python3 $HOME/Documents/GitHub/local-ai-tooling/scripts/ldr-e2e.py
```

## `owui-code-exec`

OWUI terminal proxy runs real code on mini open-terminal (lai-09)

- **host:** `mini` · **severity:** `warn` · **guards task:** `lai-09` · **enabled:** True
- **expects:** `^OWUI_CODEEXEC_OK `

```bash
r=$(curl -s -m 90 -X POST -H "Authorization:Bearer $OWUI_API_KEY" -H "Content-Type:application/json" -d "{\"command\":\"python3 -c \\\"print(617*3)\\\"\"}" "$OWUI_URL/api/v1/terminals/open-terminal/execute?wait=60" | python3 -c 'import sys,json;d=json.load(sys.stdin);out="".join(e.get("data","") for e in d.get("output",[]));print(("OK" if d.get("exit_code")==0 and "1851" in out else "BAD")+" status="+str(d.get("status"))+" exit="+str(d.get("exit_code")))' 2>/dev/null); case "$r" in OK*) echo "OWUI_CODEEXEC_OK $r";; *) echo "OWUI_CODEEXEC_BAD r=${r:-noresponse}";; esac
```

## `voice-roundtrip`

Kokoro TTS -> mini whisper STT round-trip + OWUI audio config wired (lai-10)

- **host:** `mini` · **severity:** `warn` · **guards task:** `lai-10` · **enabled:** True
- **expects:** `^VOICE_OK `

```bash
cfg=$(curl -s -m 15 -H "Authorization:Bearer $OWUI_API_KEY" "$OWUI_URL/api/v1/audio/config" | python3 -c 'import sys,json;d=json.load(sys.stdin);t=d.get("tts",{});s=d.get("stt",{});print("WIRED" if (t.get("ENGINE")=="openai" and t.get("OPENAI_API_BASE_URL")=="http://kokoro:8880/v1" and t.get("MODEL")=="kokoro" and s.get("ENGINE")=="openai" and s.get("OPENAI_API_BASE_URL","").startswith("http://192.168.10.2:8010") and s.get("MODEL")=="Systran/faster-whisper-small") else "DRIFT")' 2>/dev/null); if [ "$cfg" != "WIRED" ]; then echo "VOICE_BAD config=${cfg:-noresponse}"; else d=$(mktemp -d); curl -s -m 60 -X POST -H "Content-Type:application/json" -d "{\"model\":\"kokoro\",\"input\":\"The fleet voice loop check says pomegranate.\",\"voice\":\"af_heart\",\"response_format\":\"wav\"}" "http://192.168.10.12:8880/v1/audio/speech" -o "$d/probe.wav"; sz=$(wc -c < "$d/probe.wav" 2>/dev/null); if [ "${sz:-0}" -lt 40000 ] || [ "$(head -c 4 "$d/probe.wav")" != "RIFF" ]; then echo "VOICE_BAD tts_bytes=${sz:-0}"; rm -rf "$d"; else txt=$(curl -s -m 200 -X POST -F "file=@$d/probe.wav" -F "model=Systran/faster-whisper-small" -F "response_format=json" "http://192.168.10.2:8010/v1/audio/transcriptions" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("text",""))' 2>/dev/null); rm -rf "$d"; low=$(printf "%s" "$txt" | tr "[:upper:]" "[:lower:]"); case "$low" in *fleet*voice*loop*pomegranate*) echo "VOICE_OK tts_bytes=$sz stt=$low";; *) echo "VOICE_BAD stt=${low:-empty}";; esac; fi; fi
```

## `image-browser-mcp`

comfyui-mcp + playwright-mcp handshake/nav + OWUI image-engine config (lai-11)

- **host:** `mini` · **severity:** `warn` · **guards task:** `lai-11` · **enabled:** True
- **expects:** `^IMGBROWSER_OK `

```bash
python3 /opt/verification/bin/image-browser-mcp.py
```

## `kiwix-search-consumer`

Kiwix library breadth + real search->article fetch (lai-12 consumer end)

- **host:** `mini` · **severity:** `warn` · **guards task:** `lai-12` · **enabled:** True
- **expects:** `^KIWIX_OK `

```bash
python3 /opt/verification/bin/kiwix-search-consumer.py
```

## `openzim-mcp-search`

openzim-mcp real ZIM search + article fetch via mcpo (lai-13 consumer end)

- **host:** `mini` · **severity:** `warn` · **guards task:** `lai-13` · **enabled:** True
- **expects:** `^OPENZIM_OK `

```bash
python3 -c "import json,urllib.request; Z='/zim/ifixit_en_all_2025-12.zim'; B='http://192.168.10.12:8000/openzim/'; b=json.dumps({'query':'battery replacement','zim_file_path':Z,'limit':3}).encode(); q=urllib.request.Request(B+'zim_search',data=b,headers={'Content-Type':'application/json'}); r=json.load(urllib.request.urlopen(q,timeout=75)); r=json.loads(r) if isinstance(r,str) else r; res=r.get('results',[]) if isinstance(r,dict) else []; p=res[0].get('path','') if res else ''; b2=json.dumps({'zim_file_path':Z,'entry_path':p}).encode(); q2=urllib.request.Request(B+'zim_get',data=b2,headers={'Content-Type':'application/json'}); g=json.load(urllib.request.urlopen(q2,timeout=75)) if p else {}; g=json.loads(g) if isinstance(g,str) else g; c=str(g.get('content','')) if isinstance(g,dict) else str(g); ok=bool(res) and len(c)>800 and 'battery' in c.lower(); print(('OPENZIM_OK' if ok else 'OPENZIM_BAD')+' results=%d path=%s content_bytes=%d'%(len(res),p,len(c)))"
```

## `gamefaqs-zim-search`

Private GameFAQs ZIM real search->FAQ fetch via kiwix-serve (lai-14 consumer end)

- **host:** `mini` · **severity:** `warn` · **guards task:** `lai-14` · **enabled:** True
- **expects:** `^GAMEFAQS_OK `

```bash
python3 -c "import re,urllib.request,urllib.parse; B='http://192.168.10.4:8092'; g=lambda p: urllib.request.urlopen(urllib.request.Request(B+p,headers={'User-Agent':'fleet-verification'}),timeout=90).read().decode('utf-8','replace'); cat=g('/catalog/v2/entries?count=-1'); ent=[e for e in re.findall(r'<entry>(.*?)</entry>',cat,re.S) if '<name>gamefaqs_en_private</name>' in e]; base=(re.search(r'/content/([A-Za-z0-9_.-]+)',ent[0]).group(1) if ent else ''); sr=(g('/search?books.name=%s&pattern=%s&pageLength=5'%(base,urllib.parse.quote('chrono trigger'))) if base else ''); links=[l for l in re.findall(r'/content/[A-Za-z0-9_./?#=&%-]+',sr) if base and (base+'/') in l and l.endswith('.html')]; art=(g(urllib.parse.quote(links[0],safe='/:#?=&%')) if links else ''); ok=bool(ent) and bool(links) and len(art)>800 and 'chrono' in art.lower() and 'PRIVATE archive' in art; print(('GAMEFAQS_OK' if ok else 'GAMEFAQS_BAD')+' base=%s results=%d bytes=%d'%(base or 'none',len(links),len(art)))"
```

## `strategywiki-zim-present`

StrategyWiki ZIM pipeline healthy / real search once landed (lai-15)

- **host:** `mini` · **severity:** `warn` · **guards task:** `lai-15` · **enabled:** True
- **expects:** `^STRATEGYWIKI_OK `

```bash
python3 /opt/verification/bin/strategywiki-zim.py
```

## `maps-pmtiles-serve`

Offline US map serves real vector tiles via Caddy (lai-17 consumer end)

- **host:** `mini` · **severity:** `warn` · **guards task:** `lai-17` · **enabled:** True
- **expects:** `^MAPS_PMTILES_OK `

```bash
bash /opt/verification/bin/maps-pmtiles-serve.sh
```

## `maps-photon-geocode`

Photon US offline geocoder (build-mode aware; real geocode once landed) (lai-17)

- **host:** `mini` · **severity:** `warn` · **guards task:** `lai-17` · **enabled:** True
- **expects:** `^MAPS_PHOTON_OK `

```bash
bash /opt/verification/bin/maps-photon-geocode.sh
```

## `agent-memory-plugin`

opencode agent-memory plugin present+valid on rig AND a well-formed MEMORY.md exists (lai-18)

- **host:** `rig` · **severity:** `warn` · **guards task:** `lai-18` · **enabled:** True
- **expects:** `^MEM_OK `

```bash
P="$HOME/.config/opencode/plugins/memory.ts"; D="${OPENCODE_MEMORY_DIR:-$HOME/.local/share/opencode/memory}"; if [ ! -f "$P" ]; then echo MEM_NO_PLUGIN; exit 0; fi; if ! grep -q "experimental.session.compacting" "$P" || ! grep -q "session.idle" "$P" || ! grep -q "chat/completions" "$P"; then echo MEM_PLUGIN_STRUCT_BAD; exit 0; fi; if ! node --experimental-strip-types --check "$P" >/dev/null 2>&1; then echo MEM_PLUGIN_SYNTAX_BAD; exit 0; fi; f=$(ls -t "$D"/*.md 2>/dev/null | head -1); if [ -z "$f" ]; then echo MEM_NO_FILE; exit 0; fi; sec=$(grep -cE "^## .*\((idle|compacting)\)$" "$f" | tr -d "[:space:]"); bul=$(grep -cE "^- " "$f" | tr -d "[:space:]"); if [ "${sec:-0}" -ge 1 ] && [ "${bul:-0}" -ge 1 ]; then echo "MEM_OK plugin=ok syntax=ok sections=$sec bullets=$bul file=$(basename "$f")"; else echo "MEM_MALFORMED sec=${sec:-0} bul=${bul:-0}"; fi
```

## `bioclip-identify-consumer`

bioclip-api ranks the golden dandelion as genus Taraxacum (lai-22)

- **host:** `mini` · **severity:** `warn` · **guards task:** `lai-22` · **enabled:** True
- **expects:** `^BIOCLIP_OK `

```bash
g=$(curl -s -m 120 -X POST -F "file=@/opt/verification/assets/plant-id-dandelion.jpg" "http://192.168.10.12:8199/identify?k=1" | python3 -c 'import sys,json;print((json.load(sys.stdin).get("predictions") or [{}])[0].get("genus",""))' 2>/dev/null); if [ "$g" = "Taraxacum" ]; then echo "BIOCLIP_OK genus=$g"; else echo "BIOCLIP_BAD genus=${g:-noresponse}"; fi
```

## `owui-plant-id-e2e`

OWUI identify_plant tool chain narrates the golden dandelion (lai-22)

- **host:** `mini` · **severity:** `warn` · **guards task:** `lai-22` · **enabled:** True
- **expects:** `^PLANT_ID_E2E_OK `

```bash
PLANT_MODEL=coder-swarm python3 /opt/verification/bin/owui-plant-id-e2e.py
```

## `owui-plant-id-ui-path`

identify_plant resolves the image from UI-shaped messages (image_url parts, files stripped)

- **host:** `mini` · **severity:** `warn` · **guards task:** `lai-22` · **enabled:** True
- **expects:** `^PLANT_UI_PATH_OK `

```bash
python3 /opt/verification/bin/owui-plant-id-ui-path.py
```

## `owui-chat-vision`

chat-vision lane native vision describes the golden image via OWUI (lai-22)

- **host:** `mini` · **severity:** `warn` · **guards task:** `lai-22` · **enabled:** True
- **expects:** `^CHAT_VISION_OK `

```bash
python3 /opt/verification/bin/owui-chat-vision.py
```

## `unsloth-studio-e2e`

Unsloth Studio API-key chat rides llama-swap qwen3.8-27b + config drift gate

- **host:** `mini` · **severity:** `warn` · **guards task:** `lai-28` · **enabled:** True
- **expects:** `^UNSLOTH_E2E_OK `

```bash
python3 /opt/verification/bin/unsloth-studio-e2e.py
```

## `plant-scout-preset`

Plant Scout preset intact (active, base=chat-vision, vision, identify_plant tool)

- **host:** `mini` · **severity:** `warn` · **guards task:** `lai-22` · **enabled:** True
- **expects:** `^SCOUT_OK`

```bash
curl -s -m 15 -H "Authorization:Bearer $OWUI_API_KEY" "$OWUI_URL/api/v1/models/model?id=plant-scout" | python3 -c 'import sys,json;d=json.load(sys.stdin);m=d.get("meta") or {};ok=(d.get("is_active") and d.get("base_model_id")=="chat-vision" and (m.get("capabilities") or {}).get("vision") is True and "identify_plant" in (m.get("toolIds") or []) and "Rochester" in ((d.get("params") or {}).get("system") or ""));print("SCOUT_OK" if ok else "SCOUT_DRIFT "+json.dumps({"active":d.get("is_active"),"base":d.get("base_model_id"),"tools":m.get("toolIds")}))' 2>/dev/null || echo "SCOUT_DRIFT noresponse"
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
