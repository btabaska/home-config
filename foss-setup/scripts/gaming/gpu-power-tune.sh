#!/usr/bin/env bash
#
# gpu-power-tune.sh  --  RTX 3090 Ti idle/load power tuning on CachyOS (Linux)
#
# WHY: A 3090 Ti can sit at a high idle clock and burn ~100-130W doing nothing,
# and pulls ~450W under load. This script:
#   1. Enables persistence mode so the driver stays loaded and our settings
#      don't reset when the last client exits (clocks/offsets otherwise reset).
#   2. Applies a conservative POWER LIMIT (watts) to cap peak draw + heat/noise
#      with minimal FPS loss.
#   3. (Optional) Locks the GPU clock range. On Linux, NVIDIA exposes NO direct
#      voltage control. The community "indirect undervolt" trick = lock the max
#      clock + apply a positive clock OFFSET so the card hits the same clock at
#      a lower voltage. The offset step needs Coolbits/pynvml and is documented
#      in the runbook below rather than auto-applied (it's per-card and risky).
#
# SAFETY:
#   - Power limit is clamped to the card's reported Min..Max range. We never set
#     below Min (would be rejected) or above Max.
#   - Clock locking is OFF by default (LOCK_CLOCKS=0). Enable only after testing.
#   - Undervolt offsets can CRASH the GPU/driver if too aggressive. Start small
#     (e.g. +100 MHz), test under load, increase gradually. See runbook.
#
# Docs:
#   - nvidia-smi reference (-pm, -pl, -lgc): https://docs.nvidia.com/deploy/nvidia-smi/index.html
#   - Power limits & undervolting on Linux:   https://hbfreed.com/2026/03/12/power-limits-undervolting.html
#   - nvuv (indirect undervolt tool):         https://github.com/doums/nvuv
#   - NVIDIA undervolt discussion:            https://github.com/NVIDIA/open-gpu-kernel-modules/discussions/236
#
# Usage:
#   sudo ./gpu-power-tune.sh                 # persistence + default power limit
#   sudo GPU_POWER_LIMIT=300 ./gpu-power-tune.sh
#   sudo LOCK_CLOCKS=1 LOCK_GC_MIN=210 LOCK_GC_MAX=1800 ./gpu-power-tune.sh
#
# Idempotent: re-running just re-applies the same state. set -euo pipefail.

set -euo pipefail

# ---- tunables (override via env) ------------------------------------------
GPU_ID="${GPU_ID:-0}"
# Conservative target for a 3090 Ti (~450W stock). 300W keeps ~95% perf, much
# cooler/quieter. Adjust to taste; will be clamped to the card's Min..Max.
GPU_POWER_LIMIT="${GPU_POWER_LIMIT:-300}"
LOCK_CLOCKS="${LOCK_CLOCKS:-0}"          # set 1 to enable clock locking
LOCK_GC_MIN="${LOCK_GC_MIN:-210}"        # MHz
LOCK_GC_MAX="${LOCK_GC_MAX:-1800}"       # MHz (cap boost to avoid high-V bins)

log() { printf '[gpu] %s\n' "$*"; }
die() { printf '[gpu] ERROR: %s\n' "$*" >&2; exit 1; }

[[ ${EUID} -eq 0 ]] || die "Run as root (sudo $0)."
command -v nvidia-smi >/dev/null 2>&1 || die "nvidia-smi not found. Install the NVIDIA driver."

# ---- 1. persistence mode --------------------------------------------------
# Prefer the nvidia-persistenced daemon if present (the modern, recommended way);
# otherwise fall back to the immediate flag. Both are root-only and reset on reboot.
if systemctl list-unit-files 2>/dev/null | grep -q '^nvidia-persistenced'; then
  log "Enabling nvidia-persistenced.service (persistent across sessions)."
  systemctl enable --now nvidia-persistenced.service || true
else
  log "Setting persistence mode via nvidia-smi -pm 1 (resets on reboot)."
  nvidia-smi -i "${GPU_ID}" -pm 1 || true
fi

# ---- 2. power limit (clamped) ---------------------------------------------
read -r MIN_PL MAX_PL < <(
  nvidia-smi -i "${GPU_ID}" -q -d POWER \
    | awk -F': ' '
        /Min Power Limit/ {gsub(/[^0-9.]/,"",$2); min=$2}
        /Max Power Limit/ {gsub(/[^0-9.]/,"",$2); max=$2}
        END {printf "%d %d\n", min+0, max+0}'   # \n required: read returns 1 at EOF without it, killing the script under set -e (game-10 boot failure)
)
# Some driver builds omit Min/Max in -q -d POWER; fall back to current limit.
if [[ "${MIN_PL}" -eq 0 && "${MAX_PL}" -eq 0 ]]; then
  MAX_PL="$(nvidia-smi -i "${GPU_ID}" --query-gpu=power.max_limit --format=csv,noheader,nounits | tr -d ' ')"
  MIN_PL=100
  log "Power range not reported; using fallback Min=${MIN_PL}W Max=${MAX_PL}W."
fi
log "Card power-limit range: ${MIN_PL}W .. ${MAX_PL}W. Requested: ${GPU_POWER_LIMIT}W."

target="${GPU_POWER_LIMIT}"
if (( target < MIN_PL )); then target="${MIN_PL}"; log "Clamped up to Min ${MIN_PL}W."; fi
if (( target > MAX_PL )); then target="${MAX_PL}"; log "Clamped down to Max ${MAX_PL}W."; fi

log "Applying power limit: ${target}W"
nvidia-smi -i "${GPU_ID}" -pl "${target}"

# ---- 3. optional clock lock (the safe half of "undervolting") -------------
if [[ "${LOCK_CLOCKS}" == "1" ]]; then
  log "Locking GPU clocks to ${LOCK_GC_MIN}-${LOCK_GC_MAX} MHz (-lgc)."
  log "This caps boost into lower-voltage bins. Pair with a + offset for true undervolt (see runbook)."
  nvidia-smi -i "${GPU_ID}" -lgc "${LOCK_GC_MIN},${LOCK_GC_MAX}"
else
  log "Clock locking disabled (LOCK_CLOCKS=0). Power limit only."
fi

log "Done. Current state:"
nvidia-smi -i "${GPU_ID}" --query-gpu=name,persistence_mode,power.limit,power.draw,clocks.gr \
  --format=csv,noheader || true

cat <<'EOF'

[gpu] ---------------------------------------------------------------------
[gpu] PERSIST ACROSS REBOOTS with a systemd unit. Save as
[gpu]   /etc/systemd/system/gpu-power-tune.service
[gpu] then:  systemctl daemon-reload && systemctl enable --now gpu-power-tune.service
[gpu]
[gpu]   [Unit]
[gpu]   Description=NVIDIA power limit + persistence (3090 Ti tune)
[gpu]   After=multi-user.target nvidia-persistenced.service
[gpu]   Wants=nvidia-persistenced.service
[gpu]
[gpu]   [Service]
[gpu]   Type=oneshot
[gpu]   Environment=GPU_POWER_LIMIT=300
[gpu]   ExecStart=/opt/scripts/gaming/gpu-power-tune.sh
[gpu]   RemainAfterExit=yes
[gpu]
[gpu]   [Install]
[gpu]   WantedBy=multi-user.target
[gpu] ---------------------------------------------------------------------
[gpu] TRUE UNDERVOLT (clock offset) is per-card + risky; see gpu undervolt notes /
[gpu] use nvuv (https://github.com/doums/nvuv). Start at +100 MHz, test, ramp up.
EOF
