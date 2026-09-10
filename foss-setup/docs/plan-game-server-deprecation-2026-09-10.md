# Plan — retire all homelab game servers (backup first)

**Date:** 2026-09-10 · **Status:** Phase 0 DONE (2026-09-10) — awaiting Phase 1 window · **Task ledger:** `retire-gaming-01…` in `docs/tasks.json`

**Phase 0 completion record:** archives `palworld-final-20260910.tar.gz` (rig), `amp-minecraftcross01-final-20260910.tar.gz` (rig), `terraria-final-20260910.tar.gz` + `bedrock-connect-final-20260910.tar.gz` (mini `/opt/stacks/backups/`) — all listing-verified, restore spot-checked, SHA-256 in `progress.json`; rig archives mirrored to NAS `/volume1/homes/btabaska/game-server-archives/` (checksums verified equal) and to B2 restic snapshot `e3b27d50`. Mini restic covers all of `/opt/stacks` (nightly). Palworld was stopped only for the tar and restarted.

## Why

No player has connected to any game server in weeks:

| Server | Host | Last player connection | Evidence |
|---|---|---|---|
| Palworld "Robits Farm" | rig | **coderay, 2026-08-23 21:48 ET** | container game log |
| Minecraft (AMP `MinecraftCross01`) | rig | none in any surviving AMP log (back to Aug 4) | AMP_Logs grep |
| Terraria (TShock `AnalogueCoop`) | mini | none in logs (only startup welcome, Jul 28) | stack logs |
| BedrockConnect (console serverlist proxy) | mini | no players — pure proxy | container logs |

Meanwhile the stack keeps paying a permanent cost:

| Stack | Host | Disk | RAM (live) | CPU (live) | Public exposure |
|---|---|---|---|---|---|
| palworld | rig | 7.7 GB | ~1.8 GB | ~1.5 cores | `palworld.tabaska.us:1105` (playit UDP) + REST :8212 |
| amp (Minecraft, 2 instances) | rig | 7.7 GB (world is 46 MB; rest is 24 hourly backup zips) | ~1.0 GB | idle | `bedrock.tabaska.us:1111` (playit UDP), LAN :19132 |
| playit (tunnel agent) | rig | small | ~8 MB | idle | owns the two UDP claims above + java tunnel |
| terraria | mini | 15 MB (world 3 MB) | ~240 MB (1 GB cap) | light | LAN/tailnet only :7777 |
| bedrock-connect | mini | 16 KB | ~31 MB | idle | LAN :19132 |

**~15 GB disk + ~3 GB RAM reclaimed on rig**, ~270 MB RAM on mini, and two public UDP tunnels removed from the internet (attack-surface win).

Everything below follows the standing rules: live + repo change together, coverage tripwire updated on retire, disruptive steps in the 4–7 AM ET window, nothing deleted before the final archive is verified.

---

## Phase 0 — Final backups (reversible; nothing deleted)

Existing off-site coverage (rig → B2 via nightly restic): `palworld/game/Pal/Saved`, `palworld/game/backups`, `amp/…/instances` (Backups zips excluded), `playit`. Mini restic coverage of `/opt/stacks/terraria` must be **confirmed first** (its env file location differs from rig's).

### Per-server final archive

1. **Palworld (rig)**
   - `sudo docker stop palworld` (stop so the save flushes consistently — last join Aug 23, nobody active).
   - `tar czf /opt/stacks/palworld/game/backups/palworld-final-20260910.tar.gz -C /opt/stacks/palworld/game/Pal Saved` (~110 MB world + config).
   - Existing 746 hourly `palworld-save-*.tar.gz` snapshots stay as-is (30-day pruning already bounds them).
2. **Minecraft (rig)**
   - Stop the AMP `MinecraftCross01` instance via the AMP API (no host restart; creds vault `cubecoders_amp.*`). Verify the `Main` instance is empty/leftover (181 MB, no world) — expected to be.
   - `tar czf /opt/stacks/palworld/../amp-final-20260910.tar.gz` of `instances/MinecraftCross01/Minecraft/world` (46 MB) + instance `.kvp` configs.
   - Keep the 24 local hourly zips for the grace period; they're already excluded from restic bloat.
3. **Terraria (mini)**
   - World already self-backs daily (`analogue.wld.bak/.bak2`) — loss window is a day even before archiving.
   - `tar czf /opt/stacks/backups/terraria-final-20260910.tar.gz -C /opt/stacks/terraria world tshock-config` (follows the existing `vaultwarden-retired-*.tar.gz` pattern in `/opt/stacks/backups/`).
   - **Verify mini restic `BACKUP_PATHS` includes `/opt/stacks/terraria`** (world + tshock-config); if missing, add it and let one nightly run complete before retire.
4. **BedrockConnect (mini)**
   - Stateless (serverlist proxy only). Archive the 16 KB config dir for completeness; no player data.
5. **Cross-checks (gate before Phase 1)**
   - `restic snapshots` on rig: confirm a snapshot of each final archive path from the same night.
   - `tar tzf` each archive + extract one file from each into a scratch dir (restore spot-check).
   - Copy the two rig archives to the NAS (second backup domain; NAS has no SFTP — `ssh nas 'cat > /volume1/…/archive'`).
   - Record SHA-256 of all four archives in `progress.json`.

## Phase 1 — Stop & isolate (30-day grace, 4–7 AM ET window)

1. **Stop containers** (keep on disk): `docker compose stop` for palworld + amp (rig), terraria + bedrock-connect (mini). Palworld's daily 4 AM auto-update stops with it — expected.
2. **Retire playit**: `docker stop playit`, disable `playit-udp-guard.timer` + unit, remove the `playit-udp-rig` healthchecks dead-man, release all UDP claims (palworld :1105, bedrock :1111, java) at playit.gg. `palworld.tabaska.us` and `bedrock.tabaska.us` go dark — announce that in whatever channel players use (friends join on tailnet/LAN for Terraria; note the public addresses disappear).
3. **Homepage**: remove the Palworld / Minecraft / Terraria tiles from the live `services.yaml` **and** the repo mirror (`configs/docker-stack/stacks/homepage/config/services.yaml`), re-seed the container.
4. **Verification checks**: set `enabled: false` (not delete — history stays) for: `gaming.yaml` → `game-amp-backup-fresh`, `game-amp-backup-policy`, `restic-bloat-rig`, `game-playit-bedrock-udp`, `game-playit-udp-register-errors`, `game-bedrockconnect-serverlist`, `terraria-join-handshake`, `terraria-world-loaded`; `rig.yaml` → `palworld-rest-liveness`, `playit-java-public`, `playit-bedrock-public`. Keep the Apollo/MoonDeck checks (unrelated).
5. **Coverage tripwire** (mandate #2): update `verification/coverage/` manifests — mark the five stacks **retired** in `rig.containers`/`mini.containers`, remove game entries from `expected-listeners/mini.ports` (8211/8212/19132/7777/7878/19132-udp), so the sweep doesn't flag missing listeners.
6. **Docs / anti-drift**: mark rows retired in `configs/docker-stack/service-catalog.yaml` + `service-enrichment.yaml`, `configs/inventory/inventory.md`, `wiki/docs/network.md`; add `retire-gaming-01…` tasks to `docs/tasks.json`; regenerate `todo.md` + roadmap pages; regenerate wiki (`build-wiki.sh`); mark `wiki/docs/runbooks/game-backups.md` historical-with-restore-procedure.
7. **Commit + `publish-deploy.sh`** (gates: coverage manifest change requires the regenerated outputs in the same commit).
8. **Grace period (30 days):** stacks stay on disk. Anyone who wants to play can be reinstated from Phase 1 in minutes (`compose up -d`). If no objection by the window close → Phase 2.

## Phase 2 — Delete (next 4–7 AM ET window after grace)

1. Verify final archives still present on rig + NAS + B2 (`restic ls` / `restic check`), checksums match Phase 0.
2. `docker compose down` + `rm -rf` the five stacks: rig `/opt/stacks/palworld /opt/stacks/amp /opt/stacks/playit`, mini `/opt/stacks/terraria /opt/stacks/bedrock-connect` (mini: `sudo` via passwordless sudo — available on mini).
3. Rig restic `BACKUP_PATHS`: drop the retired paths (`palworld/game/Pal/Saved`, `palworld/game/backups`, `amp/…/instances`, `playit`) and the AMP `Backups` exclusion line in `/etc/restic/excludes.txt` (source: `scripts/backup/excludes-rig.txt`) — B2 data ages out via forget/prune, no repo surgery.
4. Delete rig `playit-udp-guard` unit files from `configs/host/rig/`; delete `scripts/gaming/mc-status-ping.py` consumers (gamedig tiles already gone).
5. Re-run the verification suite green, update `progress.json` (close `retire-gaming-*`), regenerate tracker/wiki, commit, `publish-deploy.sh`.

## Rollback (any phase, ≤ minutes)

- **From Phase 1:** `compose up -d` the affected stack(s), re-enable checks, re-claim playit tunnels. World state = last save at stop time.
- **From Phase 2:** restore the final archives (`tar xzf` to the original paths), `compose up -d`, re-add restic paths. Restic B2 also carries every nightly snapshot taken before deletion.

## Decisions needed from operator

1. **Grace length** — 30 days assumed (matches the palworld snapshot retention); tell me your friends know where to complain.
2. **NAS archive copies** — keep forever, or 1-year TTL? (Default: keep the four final archives forever; they're ~160 MB total.)
3. **Palworld "Robits Farm" name** — retire `palworld.tabaska.us` DNS at the same time, or keep the record parked? (Default: remove the DNS record in Phase 2.)
