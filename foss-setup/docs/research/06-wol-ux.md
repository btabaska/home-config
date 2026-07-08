> **ADDENDUM 2026-07-08:** rig is now 24/7 — wake-UX/suspend recommendations herein are superseded (WoL kept as recovery).

# Rig WoL UX research (agent complete)
SUNSHINE Q ANSWERED: Moonlight ALREADY wakes the rig natively on LAN — "Wake PC" in every client (iOS/tvOS/SteamDeck/desktop), no config beyond pairing once. Over tailscale WoL can't traverse (Tailscale official) — needs a LAN-side waker.
RECOMMENDED END STATE:
 - Remote/phone tap: ntfy topic `wake-rig` + systemd unit on mini (`ntfy subscribe --exec ~/wake-rig.sh`) — zero new infra, iOS Shortcut one-tap, works LAN+tailnet; Moonlight v7's upcoming HTTP-wake will point at the same endpoint.
 - home.tabaska.us: homepage will NEVER get a native WoL button (maintainers rejected — read-only policy; customapi fires on page load = would wake on every dashboard open). Phase 1: "Wake rig" link tile → ntfy publish URL. Phase 2 ("click ai.tabaska.us and it just wakes"): caddy-wol module — and KEY CORRECTION: our Caddy is ALREADY a custom xcaddy build (cloudflare dns) so adding --with dulli/caddy-wol is one line; handle_errors wake_on_lan + lb_try_duration 120s = page loads slowly while rig boots. MUST verify broadcast egress from the edge bridge first (container-WoL pitfall).
 - UpSnap = alternative full power-dashboard (also the game-server friend-wake pick); OliveTin only if a general ops-buttons panel is wanted.
POWER MODEL: current S5 full-boot ~30s reliable/proven — keep. When game-09 (idle suspend, S3 ~5s) lands: MUST bundle NVreg_PreserveVideoMemoryAllocations=1 + resume hook restarting sunshine, else NVENC dies after resume (known Sunshine/NVIDIA issue). iOS Moonlight: check Local Network permission (known silent-fail).
