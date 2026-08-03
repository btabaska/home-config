# Checks — retro-emulation

`foss-setup/verification/checks.d/retro-emulation.yaml` — 1 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `rig-esde-romm-library`

ES-DE on the rig sees the RomM NAS ROM library + has all launch cores (retro-05)

- **host:** `rig` · **severity:** `warn` · **guards task:** `retro-05` · **enabled:** True
- **expects:** `^ESDE-ROMM-OK`

```bash
command -v es-de >/dev/null 2>&1 || { echo NO-ESDE; exit 1; }; ls /home/btabaska/ROMs/nes/ >/dev/null 2>&1 || { echo NAS-LIBRARY-UNREACHABLE; exit 1; }; for core in mesen snes9x mgba gambatte mupen64plus_next dolphin; do [ -e "/usr/lib/libretro/${core}_libretro.so" ] || { echo "MISSING-CORE:${core}"; exit 1; }; done; n=0; empty=""; for s in gb gba n64 nes snes gc wii wiiu; do c=$(ls "/home/btabaska/ROMs/$s" 2>/dev/null | grep -vi eaDir | wc -l); [ "$c" -eq 0 ] && empty="$empty $s"; n=$((n+c)); done; if [ -n "$empty" ]; then echo "PLATFORM-EMPTY:$empty roms=$n"; exit 1; fi; if [ "$n" -ge 8000 ]; then echo "ESDE-ROMM-OK roms=$n"; else echo "LIBRARY-THIN roms=$n"; exit 1; fi
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
