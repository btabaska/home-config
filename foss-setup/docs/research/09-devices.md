# Device-tuned stack (agent complete) — per-category recs
Email: Proton app (iPhone/iPad, only option) + Apple Mail+Bridge (Mac) + Thunderbird+Bridge from Arch extra (CachyOS). Accept Proton Calendar silo (no CalDAV ever).
Browser: keep Safari+Kagi ext / Zen; optional Orion trial on Mac+iOS (Kagi-native); Orion Linux beta not ready; Helium interesting-not-yet; no cross-OS sync — accept.
2FA: Ente Auth primary (audited, local-mode option, all devices) + YubiKey (Yubico Auth) for 5-10 crown jewels; Authy has NO export — manual re-enrollment afternoon, then delete; never TOTP-in-Vaultwarden.
Messaging: no jailbreak exists; iMessage never opening (EU ruled non-gatekeeper); iOS 26.5 shipped E2EE RCS anyway; iMessage-on-Linux all need an always-on MAC (mini is Ubuntu) → keep iMessage + add Signal as secondary. Skip Beeper/BlueBubbles.
Maps: Apple Maps (daily/traffic) + CoMaps (offline/travel; where OM community energy went after governance mess).
File sync: Syncthing v2 hub on NAS (Container Manager, NOT stale SPK) + mini second node + Tailscale addressing (no relays) + versioning on NAS; iOS = Synctrain (Möbius stale); iOS is sync-on-open by platform design.
AirDrop-gap: LocalSend everywhere (caveat: release-starved 17mo but works) + optional PairDrop self-hosted for guests; keep AirDrop Apple↔Apple.
Web share: picoshare behind Caddy (minimal, boring, perfect) — Sharry only if receive-aliases matter; copyparty if you accept patch-cadence churn.
Notes: KEEP Obsidian Sync (the Plex-over-Jellyfin call, correctly made) + add Quartz 4 publishing via Forgejo Actions → Caddy static (digital garden on own domain).
Books: TheStoryGraph (indie, CSV export, no API yet) + CWA progress sync; BookLore repo-deletion drama → community fork Grimmory = watch 12mo.
iPod 512GB: ROCKBOX (4.0 Apr 2025, real Classic support, mks5lboot) — stock is dead end at 512GB (iTunesDB 64MB RAM ceiling ~50-60k tracks, dead Linux tooling); becomes FAT32 rsync target for FLAC pipeline; beware 512b-sector format trap; ~30% battery hit reported.
Kobo: STOCK Nickel + NickelMenu + CWA kobo-sync endpoint (store-masquerade, auto-kepub) = set-and-forget winner; KOReader only if typography bites; mind TLS-proxy header/token footguns.
3DS: hShop + Pretendo (live, open-source NN replacement) + RomM as library of record; Steam Deck pulls from RomM TODAY via decky-romm-sync; RomM 5.0-beta adds save-sync engine (!).
Cross-cutting: Apple friction structural in exactly 3 places (iOS bg sync, Proton-Apple calendar, iMessage-Linux). Priority by payoff: Authy→Ente, Syncthing hub, CWA kobo-sync, picoshare, Rockbox, RomM, Quartz.
