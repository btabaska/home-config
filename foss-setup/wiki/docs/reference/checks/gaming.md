# Checks — gaming

`foss-setup/verification/checks.d/gaming.yaml` — 11 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `game-amp-backup-fresh`

MinecraftCross01 hourly AMP backup ran within 4h and wasn't refused (H10)

- **host:** `rig` · **severity:** `warn` · **guards task:** `fix-34` · **enabled:** True
- **expects:** `^BACKUP-OK`

```bash
B=/opt/stacks/amp/config/.ampdata/instances/MinecraftCross01/Backups; D="/opt/stacks/amp/config/.ampdata/instances/MinecraftCross01/AMP_Logs"; z=$(ls -t "$B"/*.zip 2>/dev/null | head -1); if [ -z "$z" ]; then echo NO-BACKUPS; else age=$(( $(date +%s) - $(stat -c %Y "$z") )); L="$D/$(ls -t "$D" | head -1)"; last=$(grep -aE 'Creating Backup|Backup not taken' "$L" | tail -1); case "$last" in *"Backup not taken"*) echo "BACKUP-REFUSED age=${age}s";; *) if [ "$age" -lt 14400 ]; then echo "BACKUP-OK age=${age}s"; else echo "BACKUP-STALE age=${age}s"; fi;; esac; fi
```

## `game-amp-backup-policy`

no AMP instance has Backup ReplacePolicy=DoNothing (H10 root cause)

- **host:** `rig` · **severity:** `crit` · **guards task:** `fix-34` · **enabled:** True
- **expects:** `^POLICY-OK`

```bash
bad=$(grep -l '^Limits.ReplacePolicy=DoNothing' /opt/stacks/amp/config/.ampdata/instances/*/LocalFileBackupPlugin.kvp 2>/dev/null | xargs -r -n1 dirname | xargs -r -n1 basename | tr '\n' ' '); if [ -z "$bad" ]; then echo POLICY-OK; else echo "POLICY-DONOTHING: $bad"; fi
```

## `restic-bloat-rig`

rig restic latest snapshot free of AMP backup-zip bloat (M29)

- **host:** `rig` · **severity:** `warn` · **guards task:** `fix-34` · **enabled:** True
- **expects:** `^BLOAT-OK`

```bash
sudo -n /usr/local/bin/restic-snapshot-hygiene
```

## `game-playit-bedrock-udp`

Bedrock answers a RakNet ping via playit UDP tunnel bedrock.tabaska.us:1111 (M30)

- **host:** `mini` · **severity:** `crit` · **guards task:** `fix-34` · **enabled:** True
- **expects:** `^PONG`

```bash
python3 - <<'PY'
import socket, struct, sys
MAGIC = bytes.fromhex("00ffff00fefefefefdfdfdfd12345678")
pkt = b"\x01" + struct.pack(">Q", 0) + MAGIC + struct.pack(">Q", 0x3412)
for _ in range(2):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(8)
    try:
        s.sendto(pkt, ("bedrock.tabaska.us", 1111))
        d, a = s.recvfrom(4096)
        if d[:1] == b"\x1c":
            print("PONG from", a[0])
            sys.exit(0)
    except OSError:
        pass
    finally:
        s.close()
print("NO-PONG")
sys.exit(1)
PY
```

## `game-bedrockconnect-serverlist`

BedrockConnect serverlist answers a RakNet ping on mini:19132 (console-join path, SM45)

- **host:** `mini` · **severity:** `warn` · **guards task:** `game-04` · **enabled:** True
- **expects:** `^BEDROCKCONNECT_OK$`

```bash
python3 /opt/verification/bin/mc-bedrock-ping.py 127.0.0.1 19132 | grep -q 'Join To Open Server List' && echo BEDROCKCONNECT_OK || echo BEDROCKCONNECT_FAIL
```

## `game-playit-udp-register-errors`

playit agent logged no UDP-claim register errors in 24h (M30 class)

- **host:** `rig` · **severity:** `warn` · **guards task:** `fix-34` · **enabled:** True
- **expects:** `^REGISTER-OK`

```bash
n=$(docker logs --since 24h playit 2>&1 | grep -ac 'unexpected response from register'); if [ "${n:-0}" -eq 0 ]; then echo REGISTER-OK; else echo "REGISTER-ERRORS:${n}"; fi
```

## `terraria-join-handshake`

Terraria game port 7777 completes the join handshake (game-01)

- **host:** `mini` · **severity:** `crit` · **guards task:** `game-01` · **enabled:** True
- **expects:** `^JOINABLE`

```bash
python3 - <<'PY'
import socket, struct, sys
def wstr(s):
    b = s.encode(); n = len(b); o = b""
    while True:
        x = n & 0x7F; n >>= 7; o += bytes([x | (0x80 if n else 0)])
        if not n: break
    return o + b
payload = b"\x01" + wstr("Terraria279")
frame = struct.pack("<H", len(payload) + 2) + payload
try:
    s = socket.create_connection(("127.0.0.1", 7777), timeout=8)
    s.settimeout(8); s.sendall(frame)
    hdr = b""
    while len(hdr) < 3:
        c = s.recv(3 - len(hdr))
        if not c: break
        hdr += c
    s.close()
    if len(hdr) >= 3 and hdr[2] in (2, 3, 37):
        print("JOINABLE msgType=%d" % hdr[2]); sys.exit(0)
    print("NO-HANDSHAKE hdr=%s" % hdr.hex()); sys.exit(1)
except Exception as e:
    print("FAIL %s: %s" % (type(e).__name__, e)); sys.exit(1)
PY
```

## `terraria-world-loaded`

Terraria has world AnalogueCoop loaded with open slots (game-01)

- **host:** `mini` · **severity:** `warn` · **guards task:** `game-01` · **enabled:** True
- **expects:** `^WORLD-LOADED`

```bash
s=$(curl -s -m 8 http://127.0.0.1:7878/v2/server/status)
echo "$s" | grep -q '"status": *"200"' || { echo REST-DOWN; exit 1; }
w=$(echo "$s" | grep -o '"maxplayers": *[0-9]\+' | grep -o '[0-9]\+')
world=$(echo "$s" | sed -n 's/.*"world": *"\([^"]*\)".*/\1/p')
if [ -n "$world" ] && [ "${w:-0}" -gt 0 ]; then
  echo "WORLD-LOADED world=$world slots=$w"
else
  echo NOT-READY
fi
```

## `game-apollo-serverinfo`

Apollo answers GameStream /serverinfo on rig:47989 (Moonlight client path, game-05)

- **host:** `mini` · **severity:** `crit` · **guards task:** `game-05` · **enabled:** True
- **expects:** `^APOLLO-OK`

```bash
out=$(curl -s --max-time 10 http://192.168.10.12:47989/serverinfo 2>&1); case "$out" in *'status_code="200"'*) st=$(echo "$out" | sed -n 's/.*<state>\([^<]*\)<.*/\1/p'); echo "APOLLO-OK state=${st:-unknown}";; *) printf 'APOLLO-BAD %.120s\n' "${out:-empty-response}";; esac
```

## `game-apollo-session-display`

rig streaming preconditions: dummy plug + autologin session + apollo unit (game-11)

- **host:** `rig` · **severity:** `warn` · **guards task:** `game-11` · **enabled:** True
- **expects:** `^plug=connected session=yes autologin_user=1 apollo=active$`

```bash
plug=$(cat /sys/class/drm/card*-HDMI-A-1/status 2>/dev/null | head -1); sess=$([ -S /run/user/1000/wayland-0 ] && echo yes || echo no); auto=$(grep -c '^User=' /etc/plasmalogin.conf 2>/dev/null | head -1); apollo=$(XDG_RUNTIME_DIR=/run/user/1000 systemctl --user is-active apollo.service 2>/dev/null); echo "plug=${plug:-absent} session=$sess autologin_user=${auto:-0} apollo=${apollo:-unknown}"
```

## `game-moondeck-buddy`

MoonDeckBuddy API answers TLS on rig:59999 (deck MoonDeck path, game-06)

- **host:** `mini` · **severity:** `warn` · **guards task:** `game-06` · **enabled:** True
- **expects:** `^BUDDY-OK$`

```bash
c=$(curl -sk -o /dev/null -w '%{http_code}' --max-time 8 https://192.168.10.12:59999/); if [ "$c" = "404" ]; then echo BUDDY-OK; else echo "BUDDY-BAD code=${c:-none}"; fi
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
