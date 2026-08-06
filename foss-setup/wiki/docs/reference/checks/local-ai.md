# Checks — local-ai

`foss-setup/verification/checks.d/local-ai.yaml` — 2 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

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

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
