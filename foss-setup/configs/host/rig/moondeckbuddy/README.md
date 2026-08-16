# MoonDeckBuddy (rig host companion for the Steam Deck MoonDeck plugin)

Mirror of the two `~/.config/systemd/user/` units on the rig (doc-only, not
ansible-managed). Re-enabled 2026-08-16 on operator request, superseding the
fix-64/SM14 retirement.

- **Binary:** `~/Applications/MoonDeckBuddy-1.9.2-x86_64.AppImage`
  ([FrogTheFrog/moondeck-buddy](https://github.com/FrogTheFrog/moondeck-buddy)).
  Keep the filename **hashless** — the fix-64 crash-loop happened because a
  hash-suffixed AppImage was replaced and the unit's `ExecStart=` kept pointing
  at the old name.
- **`moondeckbuddy.service`** — runs Buddy headless (`NO_GUI=true` default),
  `WantedBy=default.target`.
- **`moondeckbuddy-gui-session.service`** — inside the Plasma session flips
  `MOONDECKBUDDY_NO_GUI=false` and `try-restart`s Buddy so it gets a tray icon;
  the tray dialog is where MoonDeck pairing PINs are confirmed. Reverts to
  headless when the session ends.
- **API:** TLS on `:59999`; UFW allows `192.168.10.0/24` (tailnet arrives via
  tailscaled's `ts-input` accept). Deck-side plugin: MoonDeck (Decky) with
  Moonlight flatpak.
- **Apollo tie-in:** `~/.config/sunshine/apps.json` must carry a
  **MoonDeckStream** app whose `cmd` is
  `<AppImage> --exec MoonDeckStream` — MoonDeck launches this app to stream.
  Buddy config: `~/.config/moondeckbuddy/settings.json` (port 59999).
- **Monitoring:** `game-moondeck-buddy` in `verification/checks.d/gaming.yaml`
  (TLS 404 probe from the mini); crash-loop class by `rig-no-crashloop-unit`.
