# mDNS / Multicast Checklist (UniFi)

mDNS (`*.local` service discovery: AirPlay, Chromecast/Google Cast, HomeKit, Matter,
AirPrint, Sonos, Moonlight/Sunshine) is **link-local** — it does not cross VLANs on its
own. The UniFi Gateway **mDNS Proxy** rebroadcasts it between VLANs.

## The one rule that matters for gaming

- **Keep Sunshine (host) and Moonlight (clients) on the SAME network (Trusted).**
  Same subnet → mDNS just works, no proxy, no router hop, lowest latency. This is the
  whole reason gaming/streaming is NOT its own VLAN.

## When you DO need the mDNS proxy (cross-VLAN)

Example: phone on **Trusted** needs to cast to / control a Chromecast, AirPlay
speaker, HomeKit hub, or Sonos on **IoT**.

- [ ] **Enable Gateway mDNS Proxy on BOTH VLANs** (the source *and* the destination).
      Enabling only one side is the most common failure. (Settings → Networks → select
      the VLAN → toggle mDNS / mDNS Proxy.)
- [ ] Mode:
  - **Auto** = rebroadcast common services across all VLANs (simplest).
  - **Custom** = pick exact services (AirPlay, Google Cast, HomeKit, Matter, printers)
    and the VLAN scope — tighter, recommended once it works.
  - **Off** = no rebroadcast.
- [ ] Add the matching **firewall policy** for the actual unicast control traffic
      (the proxy handles *discovery* only — control still needs an allow rule).
      See `firewall-policy-order.md` rule #4.
- [ ] Custom service strings use the form `_service._protocol.local`
      (e.g. `_airplay._tcp.local`). You can add new ones to the list.
- [ ] Do **not** enable mDNS proxy on mgmt / Work / Guest VLANs (no benefit, more noise).
- [ ] Mind the per-gateway limit on how many networks can have mDNS enabled (UDM/UDW-class
      gateways allow many; only enable where needed to keep forwarded traffic down).

## IGMP snooping

- [ ] **Turn IGMP Snooping OFF** (Settings → Networks → the VLAN, or switch settings).
      UniFi's IGMP-snooping implementation is **aggressive and drops the discovery
      packets that Apple TVs / HomePods / Matter devices depend on** — the single most
      common cause of "casting/HomeKit stopped working after segmentation." IGMP snooping
      does NOT move multicast across VLANs (that's the mDNS proxy's job); it only limits
      multicast flooding *within* a VLAN. On a home-scale network that flooding is
      negligible, so disabling it is the right tradeoff for reliable discovery.
- [ ] Only re-enable it on a specific VLAN if you have **many** chattering multicast
      devices *and* you've confirmed discovery still works with it on.

## Multicast filtering (WiFi)

- APs forward all multicast from wired→wireless clients unless **Multicast Filtering**
  is enabled in WiFi settings. If wireless cast/AirPlay is flaky, check this toggle.

## Verify

- [ ] On a Trusted phone, open the cast/AirPlay picker → the IoT device appears.
- [ ] Casting/playback actually starts (confirms the firewall control rule, not just
      discovery).
- [ ] Moonlight on a Trusted client auto-discovers the Sunshine host (same subnet).

## Authoritative docs

- UniFi Gateway mDNS Proxy — https://help.ui.com/hc/en-us/articles/12648701398807-UniFi-Gateway-Multicast-DNS-mDNS-Proxy
- Sonos across VLANs (mDNS proxy + scoped rules, practitioner write-up) — https://existentia.net/blog/sonos-across-vlans-udm-pro/
