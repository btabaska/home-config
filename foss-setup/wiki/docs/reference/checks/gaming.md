# Checks — gaming

`foss-setup/verification/checks.d/gaming.yaml` — 5 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

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

## `game-playit-udp-register-errors`

playit agent logged no UDP-claim register errors in 24h (M30 class)

- **host:** `rig` · **severity:** `warn` · **guards task:** `fix-34` · **enabled:** True
- **expects:** `^REGISTER-OK`

```bash
n=$(docker logs --since 24h playit 2>&1 | grep -ac 'unexpected response from register'); if [ "${n:-0}" -eq 0 ]; then echo REGISTER-OK; else echo "REGISTER-ERRORS:${n}"; fi
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
