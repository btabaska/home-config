#!/usr/bin/env bash
#
# wake-rig-via-mini.sh
# Wake the rig by running wake-rig.sh on the Mac mini (always on Trusted VLAN).
# Use this from the MacBook, phone (Termius), seedbox, or anywhere off-LAN.
#
# Requires wake-rig.sh + rig-wol.env on mini (game-08 deploy step).
#
# Usage:
#   ./scripts/gaming/wake-rig-via-mini.sh
#
set -euo pipefail

exec ssh mini 'bash ~/wake-rig.sh'
