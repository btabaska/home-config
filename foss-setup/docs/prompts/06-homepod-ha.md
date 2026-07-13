# Handoff 06 — HomePod ↔ HA HomeKit hub (#4) · depends on 04 · NEEDS-USER

Prereqs: item 04 (network re-audit) done — you need the VLAN placement of the HomePods vs HA and the mDNS-proxy reality. Read memory [[ha-control-plane]] and the "Lights → HA → Apple Home" entry in `docs/handoff-rollout-state.md`. HA REST at `http://192.168.10.50:8123` (token vault `hosts.ha.api_token`). Loop applies; this one **needs on-device Apple Home checks the user must do**.

Symptom: "HomePod unable to communicate with home hub." Three candidates — work them in order:
1. **Bridge never paired.** The HA HomeKit bridge (`homekit` entry `HASS Bridge:21064`, 73 light accessories) was *added but pairing is the only step that commits*, and pairing happens on the user's iPhone. Verify via HA whether the bridge shows paired; if not, regenerate the pairing code (HA "HomeKit Pairing" notification) and give the user the scan/enter steps. **Watch the double-exposure trap:** the Hue bridge is HomeKit-native and may already be in Apple Home directly — recommend removing direct Hue from Apple Home before pairing the HA bridge, or the user gets duplicate lights.
2. **Apple-side hub health.** "Communicate with home hub" is an Apple error — a HomePod/Apple TV acting as the Home hub may be offline/dropping. This is on-device: have the user check Home app → Home Settings → Home Hubs & Bridges (all "Connected"?).
3. **Cross-VLAN mDNS.** If (from item 04) the HomePods and HA are on different VLANs, `_hap._tcp` discovery needs mDNS reflection enabled on both VLANs (do NOT reflect Matter). If same VLAN, this doesn't apply. Fix the reflection config if that's the gap.

Validate: the HA-exposed lights appear and respond in Apple Home / Siri (user confirms on-device). Harden: a check that HA advertises `_hap._tcp` and the bridge entry is `loaded`/paired (via HA API); or that the bridge accessory count matches expected. Negative-test if feasible.

Done-criteria: HomePods control HA-bridged devices (user-confirmed), root cause documented, any mDNS/firewall fix committed. Commit; check item 06 off; update the task board. If blocked on user on-device steps, note exactly what's pending in the queue item and report.
