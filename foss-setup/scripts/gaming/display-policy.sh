#!/usr/bin/env bash
# Single-display policy. HDMI-A-1 = dummy plug (headless fallback). If a REAL
# monitor is connected on any other output, switch to it and drop the dummy in
# ONE atomic kscreen-doctor call; else keep the dummy as the sole display.
export XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0
DUMMY=HDMI-A-1
LOG=~/.local/state/display-policy.log; mkdir -p ~/.local/state
exec 9>~/.local/state/display-policy.lock; flock -n 9 || exit 0
ts=$(date -Is)
# strip ANSI, then a connector is "real & present" if its status line is exactly
# "connected" (not "disconnected") and its name isn't the dummy.
mapfile -t real < <(kscreen-doctor -o 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' \
  | awk '/^Output:/{n=$3} /^[[:space:]]+connected$/{print n}' \
  | grep -vx "$DUMMY" | sed '/^$/d' | sort -u)
if [ "${#real[@]}" -gt 0 ]; then
  args=(); for o in "${real[@]}"; do args+=("output.$o.enable"); done
  args+=("output.$DUMMY.disable")
  if kscreen-doctor "${args[@]}" >>"$LOG" 2>&1; then
    echo "$ts -> real=[${real[*]}] enabled, $DUMMY disabled" >>"$LOG"
  else
    echo "$ts -> FAILED switch to real=[${real[*]}]; unchanged" >>"$LOG"
  fi
else
  kscreen-doctor output.$DUMMY.enable >>"$LOG" 2>&1 || true
  echo "$ts -> no real monitor; $DUMMY sole display" >>"$LOG"
fi
