#!/usr/bin/env python3
"""Real Minecraft Java status ping (handshake + status, protocol 1.7+).

Why not a bare TCP probe: the playit edge intermittently refuses/ignores
no-data connects (verified 2026-07-09: a Kuma TCP monitor on 69.9.181.17
flapped while real client pings succeeded every time). This speaks the actual
protocol a Java client uses, so green means friends can really reach it.

Usage: mc-status-ping.py <host> <port> [handshake-hostname]
  handshake-hostname defaults to <host>; pass minecraft.tabaska.us when
  probing the playit edge by IP so hostname-based routing still matches.
Prints the status JSON (truncated) on success, exits 1 on any failure.
Deployed to mini:/opt/verification/bin/ for the verification sweep
(check playit-java-public in checks.d/rig.yaml).
"""
import json
import socket
import struct
import sys


def write_varint(n):
    out = b""
    while True:
        b = n & 0x7F
        n >>= 7
        out += struct.pack("B", b | (0x80 if n else 0))
        if not n:
            return out


def read_varint(sock):
    n = shift = 0
    while True:
        b = sock.recv(1)
        if not b:
            raise EOFError("connection closed mid-varint")
        n |= (b[0] & 0x7F) << shift
        if not b[0] & 0x80:
            return n
        shift += 7


def main():
    host = sys.argv[1]
    port = int(sys.argv[2])
    handshake_host = sys.argv[3] if len(sys.argv) > 3 else host

    with socket.create_connection((host, port), timeout=8) as s:
        s.settimeout(8)
        name = handshake_host.encode()
        handshake = (write_varint(0)            # packet id 0x00
                     + write_varint(767)        # protocol version (any modern)
                     + write_varint(len(name)) + name
                     + struct.pack(">H", port)
                     + write_varint(1))         # next state: status
        s.sendall(write_varint(len(handshake)) + handshake)
        s.sendall(write_varint(1) + write_varint(0))  # status request

        read_varint(s)                          # response packet length
        if read_varint(s) != 0:
            raise ValueError("unexpected packet id")
        strlen = read_varint(s)
        buf = b""
        while len(buf) < strlen:
            chunk = s.recv(strlen - len(buf))
            if not chunk:
                raise EOFError("connection closed mid-status")
            buf += chunk

    status = json.loads(buf)
    print(json.dumps({"version": status.get("version", {}).get("name"),
                      "players": status.get("players", {}).get("online")}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
