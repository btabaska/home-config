#!/usr/bin/env python3
"""Minimal stdlib WebSocket client for the Home Assistant WS API.

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
"""
import base64
import json
import os
import socket
import ssl
import struct
import sys


def _recv_exact(sock, buf, n):
    """Return (payload_bytes, remaining_buf), reading from sock as needed."""
    while len(buf) < n:
        chunk = sock.recv(65536)
        if not chunk:
            raise ConnectionError("socket closed mid-frame")
        buf += chunk
    return buf[:n], buf[n:]


def _read_frame(sock, buf):
    """Read one (unmasked, server->client) text/binary frame. Returns (text, buf)."""
    hdr, buf = _recv_exact(sock, buf, 2)
    b0, b1 = hdr[0], hdr[1]
    opcode = b0 & 0x0F
    masked = b1 & 0x80
    length = b1 & 0x7F
    if length == 126:
        ext, buf = _recv_exact(sock, buf, 2)
        length = struct.unpack(">H", ext)[0]
    elif length == 127:
        ext, buf = _recv_exact(sock, buf, 8)
        length = struct.unpack(">Q", ext)[0]
    mask = b""
    if masked:
        mask, buf = _recv_exact(sock, buf, 4)
    payload, buf = _recv_exact(sock, buf, length)
    if masked:
        payload = bytes(payload[i] ^ mask[i % 4] for i in range(len(payload)))
    if opcode == 0x8:  # close
        raise ConnectionError("server sent close frame")
    return payload.decode("utf-8", "replace"), buf


def _send_text(sock, text):
    data = text.encode()
    # client->server frames MUST be masked (RFC 6455). mask=0 is spec-legal.
    header = bytearray([0x81])  # FIN + text
    n = len(data)
    if n < 126:
        header.append(0x80 | n)
    elif n < 65536:
        header.append(0x80 | 126)
        header += struct.pack(">H", n)
    else:
        header.append(0x80 | 127)
        header += struct.pack(">Q", n)
    header += b"\x00\x00\x00\x00"  # zero mask key
    sock.sendall(bytes(header) + data)


def main():
    args = sys.argv[1:]
    host = "192.168.10.50:8123"
    scheme = "ws"
    cmds = []
    i = 0
    while i < len(args):
        if args[i] == "--host":
            host = args[i + 1]; i += 2
        elif args[i] == "--tls":
            scheme = "wss"; i += 1
        else:
            cmds.append(args[i]); i += 1
    token = os.environ.get("HA_TOKEN")
    if not token:
        print('{"error":"HA_TOKEN unset"}'); return 2
    if not cmds:
        print('{"error":"no commands"}'); return 2

    hostname, _, port = host.partition(":")
    port = int(port or (443 if scheme == "wss" else 8123))
    raw = socket.create_connection((hostname, port), timeout=20)
    sock = ssl.create_default_context().wrap_socket(raw, server_hostname=hostname) \
        if scheme == "wss" else raw
    key = base64.b64encode(os.urandom(16)).decode()
    req = (f"GET /api/websocket HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\n"
           f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
           f"Sec-WebSocket-Version: 13\r\n\r\n")
    sock.sendall(req.encode())

    # read HTTP response headers; PRESERVE any frame bytes after \r\n\r\n
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(65536)
        if not chunk:
            print('{"error":"no upgrade response"}'); return 2
        buf += chunk
    head, _, buf = buf.partition(b"\r\n\r\n")
    if b"101" not in head.split(b"\r\n", 1)[0]:
        print(json.dumps({"error": "upgrade failed",
                          "status": head.split(b"\r\n", 1)[0].decode("replace")}))
        return 2

    # auth handshake
    msg, buf = _read_frame(sock, buf)
    if json.loads(msg).get("type") != "auth_required":
        print(json.dumps({"error": "expected auth_required", "got": msg[:200]})); return 2
    _send_text(sock, json.dumps({"type": "auth", "access_token": token}))
    msg, buf = _read_frame(sock, buf)
    if json.loads(msg).get("type") != "auth_ok":
        print('{"error":"auth failed"}'); return 2

    ok = True
    for n, c in enumerate(cmds, start=1):
        obj = json.loads(c)
        obj["id"] = n
        _send_text(sock, json.dumps(obj))
        # read until we get the matching result id (skip events/pongs)
        while True:
            msg, buf = _read_frame(sock, buf)
            m = json.loads(msg)
            if m.get("id") == n and m.get("type") == "result":
                break
        if not m.get("success", False):
            ok = False
        print(json.dumps({"cmd": obj.get("type"), "success": m.get("success"),
                          "result": m.get("result"), "error": m.get("error")}))
    try:
        sock.close()
    except Exception:
        pass
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
