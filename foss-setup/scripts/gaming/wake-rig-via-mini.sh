#!/usr/bin/env bash
# Rig is 24/7 since 2026-07 — this is RECOVERY tooling (power outage / accidental shutdown), not workflow.
#
# wake-rig-via-mini.sh
# Recover a downed rig by running wake-rig.sh on the Mac mini (always on Trusted
# VLAN). Use this from the MacBook, phone (Termius), seedbox, or anywhere off-LAN.
#
# Requires wake-rig.sh + rig-wol.env on mini (game-08 deploy step).
#
# Usage:
#   ./scripts/gaming/wake-rig-via-mini.sh
#
set -euo pipefail

exec ssh mini 'bash ~/wake-rig.sh'
