# terraria (TShock) — mini always-on light co-op server

game-01. The Mac mini (8GB) hosts exactly **one** lightweight always-on game
server; this is it. TShock Terraria dedicated server, small world, `mem_limit:
1g`.

- **Join (LAN/tailnet):** `<mini-ip>:7777` (TCP), Multiplayer → Join via IP.
  No password today — the LAN + tailnet are private. game-04 (Tailscale friend
  exposure) MUST set `Settings.ServerPassword` before any external reach.
- **World:** `analogue.wld` (small, normal), auto-created on first boot by
  `bootstrap.sh` from `WORLD_FILENAME` + `-autocreate 1`.
- **REST API:** enabled, bound to `127.0.0.1:7878` only — used by the
  verification probe `GET /v2/server/status`. Not a public surface.

## Runtime state (gitignored)

`world/`, `logs/`, `tshock-config/` hold the save, logs, and the live
`config.json` (TShock rewrites it every boot). Seed a fresh host from
`config.json.example`:

```sh
mkdir -p world logs tshock-config
cp config.json.example tshock-config/config.json
docker compose up -d
```

## Verify (consumer end)

```sh
curl -s 127.0.0.1:7878/v2/server/status | jq '{world, playercount, maxplayers}'
```

`status: 200` with a non-empty `world` and `maxplayers > 0` = the server loaded
its world and is accepting joins. Monitored by `terraria-server-joinable`
(verification sweep on the mini).
