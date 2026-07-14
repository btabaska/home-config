# `haws.py`

> Minimal stdlib WebSocket client for the Home Assistant WS API.

**Path:** `foss-setup/scripts/ha/haws.py` · **Category:** [Home Assistant](index.md) · **Type:** Python

## What it does

```text
Minimal stdlib WebSocket client for the Home Assistant WS API.

HA drives several subsystems ONLY over ws://<host>/api/websocket — notably the
backup system (`backup/info`, `backup/config/info`, `backup/agents/info`,
`backup/config/update`, `backup/generate`) and the entity/device/area registries.
The operator Mac has no `websocket`/`websockets` pip package, so this speaks the
protocol with stdlib `socket` only. See memory [[ha-control-plane]].

Gotcha (learned the hard way): after the HTTP 101 upgrade, any bytes the server
already sent *after* the `\r\n\r\n` header terminator are the first WS frame(s) —
you must keep them, or you lose HA's `auth_required` and hang. This buffers them.

Usage:
  HA_TOKEN=... haws.py --host 192.168.10.50:8123 CMD_JSON [CMD_JSON ...]
Each CMD_JSON is a WS command object WITHOUT the id (id is auto-assigned), e.g.
  haws.py '{"type":"backup/info"}' '{"type":"backup/config/info"}'
Prints one line of JSON per command: {"cmd":..., "result":...} (or error).
Exit 0 iff every command returned success. Never echoes the token.
```

## See also

- [Home Assistant scripts](index.md) · [All scripts](../index.md)
