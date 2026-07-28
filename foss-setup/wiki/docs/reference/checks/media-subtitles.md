# Checks — media-subtitles

`foss-setup/verification/checks.d/media-subtitles.yaml` — 1 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `bazarr-synced-from-arrs`

bazarr: synced from Radarr + both arr SignalR links LIVE (consumer end)

- **host:** `mini` · **severity:** `warn` · **guards task:** `media-12` · **enabled:** True
- **expects:** `^BAZARR_OK movies=[1-9][0-9]* series=[0-9]+ sonarr=LIVE radarr=LIVE$`

```bash
python3 -c "import os,json,urllib.request as u; h={'X-API-KEY':os.environ['BAZARR_API_KEY']}; g=lambda p: json.load(u.urlopen(u.Request('http://192.168.10.4:6767'+p,headers=h),timeout=20)); b=g('/api/badges'); m=g('/api/movies?length=1'); s=g('/api/series?length=1'); ok=(b.get('sonarr_signalr')=='LIVE' and b.get('radarr_signalr')=='LIVE' and m.get('total',0)>0); print('BAZARR_OK movies=%d series=%d sonarr=%s radarr=%s' % (m.get('total',0),s.get('total',0),b.get('sonarr_signalr'),b.get('radarr_signalr')) if ok else 'BAZARR_FAIL '+json.dumps(b))"
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
