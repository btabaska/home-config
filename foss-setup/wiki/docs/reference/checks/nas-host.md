# Checks — nas-host

`foss-setup/verification/checks.d/nas-host.yaml` — 8 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `nas-timezone-eastern`

NAS host timezone is Eastern in all three sources (M5)

- **host:** `nas` · **severity:** `warn` · **guards task:** `fix-40` · **enabled:** True
- **expects:** `^tz=E[SD]T:link=/usr/share/zoneinfo/US/Eastern:posix=EST5EDT,M3\.2\.0,M11\.1\.0:conf=timezone="Eastern"$`

```bash
echo "tz=$(date +%Z):link=$(readlink -f /etc/localtime):posix=$(cat /etc/TZ):conf=$(grep -o 'timezone="[A-Za-z]*"' /etc/synoinfo.conf)"
```

## `fleet-timezone-consistent`

mini, nas and rig all report the same UTC offset (M5 class)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-40` · **enabled:** True
- **expects:** `^TZ_CONSISTENT=yes`

```bash
m=$(date +%z); n=$(ssh -o ConnectTimeout=5 nas date +%z </dev/null); r=$(ssh -o ConnectTimeout=5 rig date +%z </dev/null); if [ -n "$m" ] && [ "$m" = "$n" ] && [ "$m" = "$r" ]; then echo "TZ_CONSISTENT=yes offset=$m"; else echo "TZ_CONSISTENT=no mini=$m nas=$n rig=$r"; fi
```

## `nas-adguard-client-attribution`

AdGuard-NAS querylog attributes queries to real LAN IPs (M28)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-40` · **enabled:** True
- **expects:** `^ATTRIB_OK client=192\.168\.10\.\d+$`

```bash
/opt/verification/bin/adguard-nas-attribution.py
```

## `nas-soularr-failed-imports-fresh`

soularr: no failed import parked >3 days, 5-min cycle alive (M6/M24)

- **host:** `nas` · **severity:** `warn` · **guards task:** `fix-40` · **enabled:** True
- **expects:** `^stale=0:cycling=yes$`

```bash
python3 -c "import json,os,time; p='/volume1/docker/soularr/'; d=json.load(open(p+'failed_imports.json')); now=time.time(); stale=[v['title'] for v in d.values() if now-time.mktime(time.strptime(v['failed_at'][:19],'%Y-%m-%dT%H:%M:%S'))>3*86400]; age=(now-os.path.getmtime(p+'soularr.log'))/60; print('stale=%d:cycling=%s' % (len(stale),'yes' if age<20 else 'no'), *stale)"
```

## `nas-md-arrays-healthy`

NAS md topology exactly healthy: 3x[U] data + [UUU_] system (M4)

- **host:** `nas` · **severity:** `crit` · **guards task:** `fix-40` · **enabled:** True
- **expects:** `^md0=\[UUU_\]:md1=\[UUU_\]:md2=\[U\]:md3=\[U\]:md4=\[U\]:faulty=0$`

```bash
for m in md0 md1 md2 md3 md4; do printf "%s=%s:" "$m" "$(grep -A1 "^$m :" /proc/mdstat | grep -o '\[[U_]*\]' | tail -1)"; done; echo "faulty=$(grep -c '(F)' /proc/mdstat)"
```

## `nas-core-dumps`

NAS: no core.gz crash dumps at /volume1 root

- **host:** `nas` · **severity:** `warn` · **guards task:** `fix-45` · **enabled:** True
- **expects:** `^0$`

```bash
ls /volume1/ 2>/dev/null | grep -c 'core\.gz' || true
```

## `nas-docker-macos-junk`

NAS: no .DS_Store/AppleDouble junk in /volume1/docker

- **host:** `nas` · **severity:** `warn` · **guards task:** `fix-45` · **enabled:** True
- **expects:** `^0$`

```bash
find /volume1/docker -maxdepth 3 \( -name '._*' -o -name '.DS_Store' \) -type f 2>/dev/null | wc -l
```

## `nas-syslog-geo-filter-present`

NAS: synologand geo-lookup flood filter present in /usr/local syslog-ng (SL1)

- **host:** `nas` · **severity:** `warn` · **guards task:** `fix-69` · **enabled:** True
- **expects:** `GEO_FILTER_OK$`

```bash
d=/usr/local/etc/syslog-ng/patterndb.d; f=0; [ -f "$d/synologand-geo.conf" ] && f=$((f+1)); [ -f "$d/include/not2msg/synologand_geo" ] && f=$((f+1)); echo "geo_filter_files=$f/2"; [ "$f" -eq 2 ] && echo GEO_FILTER_OK || echo GEO_FILTER_MISSING
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
