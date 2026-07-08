#!/usr/bin/env bash
# Recovery-only rig wake (rig is 24/7; for after a power outage / accidental
# shutdown). Sends a WoL magic packet to the rig NIC on the LAN broadcast.
set -euo pipefail
/usr/bin/wakeonlan -i 192.168.10.255 ""50:eb:f6:b5:82:c6"" 2>&1 | head -1
logger -t wake-rig "recovery WoL sent to "50:eb:f6:b5:82:c6""
