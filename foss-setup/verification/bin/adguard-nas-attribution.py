#!/usr/bin/env python3
"""
adguard-nas-attribution.py — fix-40 (M28) regression check, consumer end.

M28: AdGuard-NAS served 52k queries/24h but attributed ALL of them to the
docker bridge gateway (172.23.0.1) because port 53 was published from a bridge
network. Per-client stats, client rules and querylog forensics were impossible
— the monitoring data existed but was garbage. Fixed 2026-07-19 by moving the
container to network_mode: host.

Consumer invariant probed here: a DNS query sent from a real LAN client must
appear in the querylog WITH that client's real IP. We dig a canary name
(verify-attrib.tabaska.us, answered locally by the *.tabaska.us rewrite — never
leaks upstream) from this host, then read the querylog via the API and assert
the newest canary entry's client is a LAN IP, not a docker-bridge NAT address.

Fails LOUDLY if DNS or the API is unreachable. One line:
  ATTRIB_OK  client=192.168.10.x
  ATTRIB_BAD client=172.23.0.1   (bridge NAT is back — M28 regressed)
  ATTRIB_ERR <reason>

Env: ADGUARD_NAS_URL (default http://192.168.10.4:3000),
     ADGUARD_NAS_USER, ADGUARD_NAS_PASS (vault adguard_nas.*).
"""
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

CANARY = "verify-attrib.tabaska.us"
DNS_IP = "192.168.10.4"
URL = os.environ.get("ADGUARD_NAS_URL", "http://192.168.10.4:3000").rstrip("/")
USER = os.environ.get("ADGUARD_NAS_USER", "")
PASS = os.environ.get("ADGUARD_NAS_PASS", "")


def api(path):
    tok = base64.b64encode(f"{USER}:{PASS}".encode()).decode()
    req = urllib.request.Request(URL + path, headers={"Authorization": "Basic " + tok})
    return json.load(urllib.request.urlopen(req, timeout=15))


def main():
    if not USER or not PASS:
        print("ATTRIB_ERR ADGUARD_NAS_USER/ADGUARD_NAS_PASS not set in /etc/verification/env")
        return
    # 1) act as the consumer: resolve the canary against the NAS resolver
    dig = subprocess.run(
        ["dig", "+short", "+time=3", "+tries=2", f"@{DNS_IP}", CANARY],
        capture_output=True, text=True, timeout=20,
    )
    answer = dig.stdout.strip().splitlines()[-1] if dig.stdout.strip() else ""
    if not re.match(r"^192\.168\.10\.\d+$", answer):
        print(f"ATTRIB_ERR canary query failed (answer={answer!r} rc={dig.returncode})")
        return
    time.sleep(2)  # querylog write is async; newest entry needs a beat to land
    # 2) read the observability end: who does AdGuard think asked?
    try:
        log = api(f"/control/querylog?search={CANARY}&limit=5")
    except Exception as e:  # noqa: BLE001 — one-line diagnostic by design
        print(f"ATTRIB_ERR querylog API: {e}")
        return
    entries = log.get("data", [])
    if not entries:
        print("ATTRIB_ERR canary resolved but not found in querylog")
        return
    client = entries[0].get("client", "")
    if re.match(r"^192\.168\.\d+\.\d+$", client):
        print(f"ATTRIB_OK client={client}")
    else:
        print(f"ATTRIB_BAD client={client}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"ATTRIB_ERR {e}")
        sys.exit(0)
