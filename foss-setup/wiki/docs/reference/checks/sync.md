# Checks — sync

`foss-setup/verification/checks.d/sync.yaml` — 3 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `syncthing-hub-mesh-direct`

syncthing NAS hub: rig + mini both connected over direct LAN (no cloud relay)

- **host:** `nas` · **severity:** `warn` · **guards task:** `foss-03` · **enabled:** True
- **expects:** `^syncthing_hub=ok peers_direct=2/2`

```bash
API=$(grep -o '<apikey>[^<]*</apikey>' /volume1/docker/syncthing/config/config.xml | sed 's/<[^>]*>//g'); curl -s -H "X-API-Key: $API" http://127.0.0.1:8384/rest/system/connections | python3 -c "import json,sys; d=json.load(sys.stdin)[\"connections\"]; peers={\"KDLS63N-KNX5Q4U-IAGLHGX-2BW7CS2-VGVQBNL-V7VOZ4R-O2NBHQZ-VMSCAQ7\":\"rig\",\"CCBXYGN-JOUDYOO-A3HIC73-MNTZWI4-6N4ZCVF-GYYSMJ7-OWUYGF4-NM4UWAU\":\"mini\"}; r=[(n,d.get(i,{}).get(\"connected\",False),d.get(i,{}).get(\"type\",\"\")) for i,n in peers.items()]; good=lambda c,t: c and t.startswith((\"tcp\",\"quic\")) and \"relay\" not in t; ok=[1 for _,c,t in r if good(c,t)]; bad=[\"%s(conn=%s,type=%s)\"%(n,c,t or \"none\") for n,c,t in r if not good(c,t)]; print(\"syncthing_hub=ok peers_direct=%d/2\"%len(ok) if not bad else \"syncthing_hub=DEGRADED \"+\";\".join(bad))"
```

## `syncthing-gui-urls`

syncthing GUI reverse-proxy URLs (hub + rig) serve via Caddy

- **host:** `mini` · **severity:** `warn` · **guards task:** `foss-03` · **enabled:** True
- **expects:** `^syncthing_urls syncthing.tabaska.us=ok syncthing-rig.tabaska.us=ok$`

```bash
out=""; for h in syncthing.tabaska.us syncthing-rig.tabaska.us; do c=$(curl -sk -m 10 -o /dev/null -w '%{http_code}' --resolve "$h:443:127.0.0.1" "https://$h/rest/noauth/health"); [ "$c" = "200" ] && out="$out $h=ok" || out="$out $h=FAIL($c)"; done; echo "syncthing_urls$out"
```

## `syncthing-hub-inotify-live`

syncthing NAS hub: every folder's inotify watcher is live (no watchError)

- **host:** `nas` · **severity:** `warn` · **guards task:** `foss-03` · **enabled:** True
- **expects:** `^syncthing_inotify=ok `

```bash
API=$(grep -o '<apikey>[^<]*</apikey>' /volume1/docker/syncthing/config/config.xml | sed 's/<[^>]*>//g'); FOLDERS=$(curl -s -H "X-API-Key: $API" http://127.0.0.1:8384/rest/config/folders | python3 -c "import sys,json;print(' '.join(f['id'] for f in json.load(sys.stdin)))"); bad=''; for f in $FOLDERS; do curl -s -H "X-API-Key: $API" "http://127.0.0.1:8384/rest/db/status?folder=$f" | grep -q '"watchError": "[^"]' && bad="$bad $f"; done; [ -z "$bad" ] && echo "syncthing_inotify=ok folders=[$FOLDERS]" || echo "syncthing_inotify=DEGRADED watchError:$bad"
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
