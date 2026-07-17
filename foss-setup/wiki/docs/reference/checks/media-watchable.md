# Checks — media-watchable

`foss-setup/verification/checks.d/media-watchable.yaml` — 4 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `media-arr-file-quality`

arr: no hasFile item points at a sample/iso/rar/stub (green==watchable)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-27` · **enabled:** True
- **expects:** `^WATCHABLE_OK`

```bash
python3 /opt/verification/bin/arr-file-quality.py
```

## `media-gossip-girl-in-plex`

regression: Gossip Girl present in Plex with its full episode count (H11)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-27` · **enabled:** True
- **expects:** `^gg_episodes=(1[0-9]{2}|[2-9][0-9]{2})$`

```bash
curl -sm 15 "$PLEX_URL/library/sections/2/all?title=Gossip%20Girl&X-Plex-Token=$PLEX_TOKEN" | python3 -c "import sys,re;x=sys.stdin.read();m=re.search(r'leafCount=\"(\d+)\"',x);print('gg_episodes='+(m.group(1) if m else '0'))"
```

## `media-extraction-backlog`

arr: <=8 wanted movies stranded as un-extracted rar (M60 backlog)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-27` · **enabled:** True
- **expects:** `^RARBACKLOG_OK`

```bash
python3 /opt/verification/bin/arr-rar-backlog.py
```

## `unpackerr-whisparr-block`

unpackerr: whisparr block present (M27 — else rar'd adult grabs stall silent)

- **host:** `nas` · **severity:** `warn` · **guards task:** `fix-27` · **enabled:** True
- **expects:** `^1$`

```bash
grep -c '^\[\[whisparr\]\]' /volume1/docker/media-automation/unpackerr/unpackerr.conf
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
