#!/usr/bin/env bash
# game-over.sh — quit Battle.net / Proton game processes and hand the RTX 3090 Ti
# back to the AI lanes (q38 needs essentially the whole card; a 421 MiB launcher
# squatter is enough to kill its load — see 2026-09-14 incident).
#
# Live copy:  ~/.local/bin/game-over.sh on the rig
# Repo copy:  foss-setup/configs/host/rig/gaming/game-over.sh  (keep in sync)
#
# Strategy: any process carrying STEAM_COMPAT_DATA_PATH in its environment is a
# Proton game-session process (Battle.net, Wow.exe, wineserver, pressure-vessel,
# reaper — all of them). SIGTERM first, then SIGKILL stragglers. Steam itself is
# left running (its idle VRAM use is negligible).

set -u

vram_used() { nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1; }

# Game processes on the GPU = compute apps that look like wine/windows exes.
# llama-server / ComfyUI / other AI tenants are the DESIRED users — never count them.
game_gpu_procs() {
    nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader 2>/dev/null \
        | grep -iE '\.exe|wine' || true
}

proton_pids() {
    local p
    for p in $(pgrep -u "$USER" 2>/dev/null); do
        [ "$p" = "$$" ] && continue
        if { tr '\0' '\n' <"/proc/$p/environ" | grep -q '^STEAM_COMPAT_DATA_PATH='; } 2>/dev/null; then
            echo "$p"
        fi
    done
}

before=$(vram_used)
echo "== Game over: freeing the GPU for AI =="
echo "VRAM in use before: ${before:-?} MiB"

pids=$(proton_pids)
if [ -z "$pids" ]; then
    echo "No Proton game processes found."
else
    echo "Stopping $(echo "$pids" | wc -l) Proton/game processes (SIGTERM)..."
    # shellcheck disable=SC2086
    kill -TERM $pids 2>/dev/null
    for _ in $(seq 1 10); do
        sleep 1
        [ -z "$(proton_pids)" ] && break
    done
    leftovers=$(proton_pids)
    if [ -n "$leftovers" ]; then
        echo "Force-killing stragglers..."
        # shellcheck disable=SC2086
        kill -KILL $leftovers 2>/dev/null
        sleep 2
    fi
fi

# Belt-and-braces: named Blizzard/wine bits that occasionally detach from the env.
pkill -KILL -u "$USER" -x wineserver 2>/dev/null
pkill -KILL -u "$USER" -f 'Battle[.]net' 2>/dev/null
pkill -KILL -u "$USER" -f 'Agent[.]exe' 2>/dev/null

# Success = no game/wine processes left on the GPU. A big llama-server/ComfyUI
# allocation is the GOAL state, not a failure — don't count AI tenants.
holdouts=""
for _ in $(seq 1 15); do
    holdouts=$(game_gpu_procs)
    [ -z "$holdouts" ] && break
    sleep 2
done

final=$(vram_used)
echo "VRAM in use after:  ${final:-?} MiB (AI processes may legitimately hold VRAM)"
if [ -z "$holdouts" ]; then
    msg="No game processes left on the GPU — AI lanes have the card (${final:-?} MiB in use)."
    echo "✅ $msg"
    command -v notify-send >/dev/null && notify-send -i steam "Game over" "$msg"
else
    msg="Game processes still on the GPU — check nvidia-smi."
    echo "⚠️  $msg"
    echo "$holdouts"
    command -v notify-send >/dev/null && notify-send -u critical -i dialog-warning "Game over" "$msg"
fi

read -r -t 30 -p "Press Enter to close..." _ 2>/dev/null || true
