#!/usr/bin/env python3
"""RakNet unconnected ping — what a Bedrock client sends to list a server.

Covers the playit UDP path (bedrock.tabaska.us:1111), which shares the
wedged-claim failure mode found on TCP 2026-07-09: agent says "connected,
tunnels loaded" while no data flows. Only a real protocol ping sees it.

Usage: mc-bedrock-ping.py <host> <port>
Prints the pong MOTD fields on success, exits 1 on failure.
Deployed to mini:/opt/verification/bin/ for the verification sweep
(check playit-bedrock-public in checks.d/rig.yaml).
"""
import random
import socket
import struct
import sys

MAGIC = bytes.fromhex("00ffff00fefefefefdfdfdfd12345678")


def main():
    host, port = sys.argv[1], int(sys.argv[2])
    ping = (b"\x01" + struct.pack(">Q", 0) + MAGIC
            + struct.pack(">Q", random.getrandbits(63)))
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(8)
        s.sendto(ping, (host, port))
        data, _ = s.recvfrom(4096)
    if not data or data[0] != 0x1C:
        raise ValueError(f"unexpected reply id {data[:1].hex()}")
    # payload: id(1) + time(8) + guid(8) + magic(16) + strlen(2) + MOTD string
    motd = data[35:].decode(errors="replace")
    fields = motd.split(";")
    print({"motd": fields[1] if len(fields) > 1 else motd[:40],
           "version": fields[3] if len(fields) > 3 else "?"})


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
