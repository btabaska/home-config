# Checks — edge

`foss-setup/verification/checks.d/edge.yaml` — 5 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `edge-wan-port-posture`

edge: no unexpected WAN ports open (only 32400/Plex allowed)

- **host:** `mini` · **severity:** `crit` · **guards task:** `fix-24` · **enabled:** True
- **expects:** `^NO_UNEXPECTED_PORTS$`

```bash
WAN=$(curl -s -m 10 https://ifconfig.me); echo "$WAN" | grep -qE '^([0-9]{1,3}\.){3}[0-9]{1,3}$' || { echo NO_WAN_IP; exit 0; }; extra=$(ssh -o BatchMode=yes -o ConnectTimeout=10 seedbox "for p in 22 80 443 853 2222 3000 3254 5000 5001 5945 6969 7878 8123 8443 8686 8787 8789 8790 8989 9696 13091 32400; do (timeout 4 bash -c \"</dev/tcp/$WAN/\$p\" >/dev/null 2>&1 && echo \$p) & done; wait" | grep -v '^32400$' | sort -n | xargs); [ -z "$extra" ] && echo NO_UNEXPECTED_PORTS || echo "UNEXPECTED_OPEN:$extra"
```

## `edge-plex-remote-identity`

edge: WAN :32400 serves the NAS Plex (Remote Access intentional, id pinned)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-24` · **enabled:** True
- **expects:** `machineIdentifier="70ffcfbb5dc9389e315070cf3a8af99c5fb340b4"`

```bash
WAN=$(curl -s -m 10 https://ifconfig.me); ssh -o BatchMode=yes -o ConnectTimeout=10 seedbox "curl -s -m 10 http://$WAN:32400/identity"
```

## `edge-plex-version-current`

edge: exposed Plex build not >14 days behind latest Synology release

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-24` · **enabled:** True
- **expects:** `^VERSION_OK:`

```bash
WAN=$(curl -s -m 10 https://ifconfig.me); exp=$(ssh -o BatchMode=yes -o ConnectTimeout=10 seedbox "curl -s -m 10 http://$WAN:32400/identity" | grep -oE 'version="[^"]+"' | head -1 | cut -d'"' -f2); curl -s -m 15 https://plex.tv/api/downloads/5.json | EXPOSED="$exp" python3 -c 'import json,os,sys,time; d=json.load(sys.stdin)["nas"]["Synology (DSM 7.2.2+)"]; exp=os.environ["EXPOSED"]; age=(time.time()-d["release_date"])/86400.0; print("VERSION_OK:current" if exp==d["version"] else ("VERSION_OK:grace_%.0fd" % age if age < 14 else "VERSION_STALE:exposed="+exp+"_latest="+d["version"]))'
```

## `edge-public-dns-no-rfc1918`

edge: Cloudflare tabaska.us zone has no A/AAAA record with a private IP

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-24` · **enabled:** True
- **expects:** `^ZONE_CLEAN$`

```bash
curl -s -m 15 -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID_TABASKA_US/dns_records?per_page=100" | python3 -c 'import json,sys,ipaddress; rs=json.load(sys.stdin)["result"]; bad=[r["name"]+"->"+r["content"] for r in rs if r["type"] in ("A","AAAA") and ipaddress.ip_address(r["content"]).is_private]; print("ZONE_CLEAN" if not bad else "RFC1918_LEAK:"+",".join(bad))'
```

## `edge-public-dns-www-nxdomain`

edge: www.tabaska.us is NXDOMAIN in public DNS (1.1.1.1)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-24` · **enabled:** True
- **expects:** `^WWW_NXDOMAIN$`

```bash
out=$(dig +short +time=3 +tries=2 @1.1.1.1 www.tabaska.us A); [ -z "$out" ] && echo WWW_NXDOMAIN || echo "WWW_RESOLVES:$out"
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
