#!/usr/bin/env bash
# Run AFTER a display exists on the rig (HDMI dummy plug plugged in, or a real
# monitor). Enables + starts Apollo and confirms it found a display + encoder.
set -e
systemctl --user enable --now apollo.service
sleep 12
systemctl --user is-active apollo.service
journalctl --user -u apollo.service --no-pager | grep -iE "nvenc|encoder \[|display" | tail -4
