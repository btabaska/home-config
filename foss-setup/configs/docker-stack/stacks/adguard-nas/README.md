# AdGuard Home — NAS secondary DNS

DHCP DNS **#2** (`192.168.10.4`). See [dns-resilience-plan.md](../../../network/dns-resilience-plan.md).

**Do not** point upstream at mini Unbound — the secondary must work when the mini is offline.

After deploy, mirror DNS rewrites from mini (`*.tabaska.us → 192.168.10.2`) and optionally
import the same blocklists.
