# Checks — seedbox

`foss-setup/verification/checks.d/seedbox.yaml` — 12 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `seedbox-public-lockdown`

seedbox: admin ports closed on public IP incl. retired syncthing 12104/16878 (H2/L9/M25 + SH5)

- **host:** `mini` · **severity:** `crit` · **guards task:** `fix-21` · **enabled:** True
- **expects:** `^CLOSED_ALL$`

```bash
open=""; for p in 3254 5945 13091 5030 5031 12104 16878; do timeout 5 bash -c "</dev/tcp/betty.bysh.me/$p" 2>/dev/null && open="$open $p"; done; [ -z "$open" ] && echo CLOSED_ALL || echo "STILL_OPEN:$open"
```

## `seedbox-loopback-binds`

seedbox: deluge RPC/web + slskd bound to 127.0.0.1 only

- **host:** `seedbox` · **severity:** `crit` · **guards task:** `fix-21` · **enabled:** True
- **expects:** `^LOOPBACK_OK$`

```bash
bad=""; for p in 3254 5945 5030; do ss -tln | grep -q "127.0.0.1:$p " || bad="$bad missing:$p"; ss -tln | grep -E "(0.0.0.0|\*):$p " >/dev/null && bad="$bad public:$p"; done; [ -z "$bad" ] && echo LOOPBACK_OK || echo "BAD:$bad"
```

## `seedbox-arr-deluge-e2e`

seedbox: sonarr -> Deluge over tailnet (download-client test passes)

- **host:** `mini` · **severity:** `crit` · **guards task:** `fix-21` · **enabled:** True
- **expects:** `^200$`

```bash
D=$(curl -sm 20 -H "X-Api-Key: $SONARR_API_KEY" http://192.168.10.4:8989/api/v3/downloadclient | python3 -c 'import json,sys; print(json.dumps([d for d in json.load(sys.stdin) if d["implementation"]=="Deluge"][0]))'); curl -sm 40 -X POST -H "X-Api-Key: $SONARR_API_KEY" -H "Content-Type: application/json" -d "$D" -o /dev/null -w '%{http_code}' http://192.168.10.4:8989/api/v3/downloadclient/test
```

## `seedbox-slskd-e2e`

seedbox: slskd over tailnet Connected+LoggedIn to Soulseek (M25 regression)

- **host:** `mini` · **severity:** `crit` · **guards task:** `fix-21` · **enabled:** True
- **expects:** `Connected.*LoggedIn`

```bash
curl -sm 15 -H "X-API-Key: $SLSKD_API_KEY" http://100.119.134.94:5030/api/v0/server | python3 -c 'import json,sys; print(json.load(sys.stdin).get("state",""))'
```

## `seedbox-services-manifest`

seedbox: running services match coverage manifest (qbittorrent + syncthing retired)

- **host:** `seedbox` · **severity:** `warn` · **guards task:** `fix-21` · **enabled:** True
- **expects:** `^MANIFEST_OK$`

```bash
bad=""; for s in deluged deluge-web slskd tailscaled; do pgrep -u "$(whoami)" -x "$s" >/dev/null || bad="$bad down:$s"; done; for r in qbittorrent-nox syncthing; do pgrep -u "$(whoami)" -x "$r" >/dev/null && bad="$bad retired-but-running:$r"; done; [ -z "$bad" ] && echo MANIFEST_OK || echo "BAD:$bad"
```

## `seedbox-syncthing-retired`

seedbox: syncthing fully retired — no process, :12104/:16878 closed, binary+launcher gone (SH5)

- **host:** `seedbox` · **severity:** `crit` · **guards task:** `fix-52` · **enabled:** True
- **expects:** `^RETIRED_OK$`

```bash
bad=""; pgrep -u "$(whoami)" -x syncthing >/dev/null && bad="$bad process-running"; ss -tln 2>/dev/null | grep -qE "(0.0.0.0|\*|127.0.0.1):(12104|16878) " && bad="$bad port-listening"; [ -e "$HOME/apps/syncthing/syncthing" ] && bad="$bad binary-present"; [ -e "$HOME/.startup/syncthing" ] && bad="$bad launcher-present"; [ -z "$bad" ] && echo RETIRED_OK || echo "BAD:$bad"
```

## `deluge-preimport-stuck`

seedbox: no torrent 100% done >48h still in a pre-import label

- **host:** `seedbox` · **severity:** `warn` · **guards task:** `fix-25` · **enabled:** True
- **expects:** `^PREIMPORT_OK`

```bash
~/venvs/deluge/bin/python ~/scripts/deluge-preimport-stuck.py
```

## `books-preimport-unimported`

seedbox: no completed books grab stuck >24h in the 'bookshelf' pre-import label (fix-57 SH11)

- **host:** `seedbox` · **severity:** `warn` · **guards task:** `fix-57` · **enabled:** True
- **expects:** `^BOOKS_PREIMPORT_OK`

```bash
~/venvs/deluge/bin/python ~/scripts/deluge-bookshelf-preimport.py
```

## `seedbox-extracted-reaped`

seedbox: no extracted leftovers older than 7d in ~/media/extracted

- **host:** `seedbox` · **severity:** `warn` · **guards task:** `fix-45` · **enabled:** True
- **expects:** `^0$`

```bash
find media/extracted -type f -mtime +7 2>/dev/null | wc -l
```

## `seedbox-tmp-arr-junk`

seedbox: no *arr _update/_backup leftovers in ~/tmp

- **host:** `seedbox` · **severity:** `warn` · **guards task:** `fix-45` · **enabled:** True
- **expects:** `^0$`

```bash
find tmp -maxdepth 1 \( -name '*_update' -o -name '*_backup' \) 2>/dev/null | wc -l
```

## `deluge-payload-present`

seedbox: no pre-import torrent Seeding-100% with a deleted payload / move_completed wedge (SH2/SH9/SM26)

- **host:** `seedbox` · **severity:** `warn` · **guards task:** `fix-54` · **enabled:** True
- **expects:** `^PAYLOAD_OK`

```bash
~/venvs/deluge/bin/python ~/scripts/deluge-payload-audit.py
```

## `seedbox-quota-headroom`

seedbox: user quota has headroom (< soft limit and >100G to hard) — pre-EDQUOT guard (SM17)

- **host:** `seedbox` · **severity:** `warn` · **guards task:** `fix-54` · **enabled:** True
- **expects:** `^QUOTA_OK`

```bash
quota -s | awk '/\/dev\//{u=$2+0;s=$3+0;h=$4+0;hr=h-u; print ((u<s && hr>100)?"QUOTA_OK":"QUOTA_LOW")" headroom_to_hard="hr"G used="u"G soft="s"G hard="h"G"}'
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
