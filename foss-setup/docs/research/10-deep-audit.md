# Deep per-service audit — second pass (2026-07-08, 5 read-only agents)

Covers the ~20 services the first-night sweep didn't individually inspect. Fixes marked ✅ were applied this same night (all reversible, all verified); everything else is options-only.

## Fixed during this pass ✅
- **musicseerr**: Lidarr API key was rotten (468×401s, circuit breaker stuck OPEN, every sync dead) → replaced from vault, all Lidarr calls 200 now. Cleared leftover default `jellyfin_url`.
- **wallabag**: `./data`+`./images` owned 1000 but php-fpm runs as 65534 → permission errors on every page view, site-credentials encryption silently broken → chowned.
- **paperless-ngx**: admin account was live with the literal default password `change_this_admin_password` (no user has ever logged in) → rotated to generated password (vault: `paperless.admin_password`), bootstrap envs scrubbed, login verified.
- **navidrome**: DB backups were disabled (`ND_BACKUP_SCHEDULE` now nightly 02:00, keep 7) and telemetry to insights.navidrome.org every 30min (now off).
- **backup gaps**: mealie.db + vaultwarden db.sqlite3 were never dumped (restic snapshotted live files) → `dump_sqlite` added to pre-backup-db-dumps.sh (python online-backup API), both dumps verified.
- **vaultwarden**: raw ADMIN_TOKEN → argon2id PHC at rest; login with original token verified. (Compose .env footgun documented: single-quoted single-$ is the only working form.)
- **sbom-nightly (mini)**: deployed script was stale (pre-SCAN_EXCLUDES) → OOM every night, Dependency-Track empty. Current script + quoted excludes deployed; run passing the old OOM point. One image upload returned HTTP 415 (metube `:latest` — version string; minor, watch).
- **seedbox**: 6 config files with secrets were o+r (single-layer defense: 700 home) → chmod 600.
- **NAS rclone watchdog**: double container-restart after every remount (mount script + watchdog both called it), no flock (hung probe could stack instances), empty listing counted as healthy (that's the stall symptom), no timeout on the find tree-walk → all four fixed in repo + deployed, live cycle green.
- **recyclarr**: `restart: unless-stopped` on a one-shot (stray `up` would loop it) → `no`; cron log moved off /tmp.
- **verification**: 9 new checks (alerting.yaml) guard the whole remediation: ntfy health+relay, both Diuns, Healthchecks populated + none-down, DSM immich task present in crontab (DSM wipe guard), DSM health task all-day, YouTube mounts rw. Sweep: 52 checks.

## Needs your decision (ranked)
1. **Stash has NO authentication** — any LAN/tailnet device or container has full GraphQL (browse/delete/plugin exec); jwt secret world-readable via Synology ACL. Fix S: set credentials in Settings→Security, or Caddy basic_auth on the vhost. (Also: `parallel_tasks: 1` could be 2 on DS920+.)
2. **Rig is in textbook partial-upgrade state** — last full `-Syu` 2026-06-15, `-Sy` + selective installs since, **441 updates pending** on a rolling distro. Needs a maintenance window (kernel/driver reboot). M.
3. **Sunshine can't actually stream** — UFW blocks 47984/tcp, 48010/tcp, 47998-48000/udp; no clients paired; web creds unset. Moonlight natively wakes the rig once paired (WoL research). S once you green-light game streaming.
4. **litellm hygiene**: literal `CHANGE-ME` postgres password; `LITELLM_SALT_KEY` byte-identical to open-webui's secret; image `main-latest` unpinned; and nothing routes through it (open-webui → ollama direct). Fix cheapest NOW before keys/spend accumulate. S.
5. **Rig firewall**: 11434 (ollama, unauthenticated API) and 3000 open to Anywhere (tailscale traffic observed); stale 3030 rule. Tighten to LAN+tailnet. S.
6. **Plex**: 1.41.5 vs 1.43.2 available; transcoder core dump Jul 7 13:09 (only transcode session that day); TranscoderTempDirectory on system volume; relay fallback enabled (would silently cap 2Mbps). Update DSM package + point transcode temp at /tmp. S.
7. **tdarr never deployed** (no container ever created; blocked on missing NAS media mount — `MEDIA_FOLDER=/mnt/nas/media` doesn't exist). Deploy (mount allmedia rw + configure) or delete the stack. Decision.
8. **maintainerr inert** — zero integrations (no Plex/Tautulli/Seerr connection), can't even create rules. Configure (M) or remove.
9. **AdGuard NAS**: answers only on .4 (eth1) — **.3 (eth0) times out**; verify DHCP hands out .4. Wizard :3000 still published. Mini instance: no fallback upstream if unbound dies (NAS secondary is the only net), ratelimit 20/s could silently drop bursts from Plex/NAS, LAN clients show as bare IPs (no private PTR resolvers).
10. **Unbound options**: ECS subnet module degrades serve-expired (add `module-config: "validator iterator"`), so-rcvbuf sysctl, `cache-min-ttl: 300` vs CDN failover, no stats surface (remote-control off).
11. **gpu-power-tune doesn't survive suspend/resume** — cap reverts to 450W; matters before game-09 idle-suspend lands. Also KDE ignores the logind idle-suspend config entirely (box stays on), and `plasmashell` sits at ~41% CPU (widget repaint loop?).
12. **Rig containers predate log caps** (LogConfig empty) — recreate at maintenance window. **Ollama disk**: ~40GB duplicate models reclaimable. **ansible-pull rig** skips backup role ("restic secret not seeded") while the live unit works — seed it so convergence owns backup config.
13. **Deluge**: 272 torrents, no ratio/age cleanup — 743G/2.8T quota grows monotonically. RPC/web on 0.0.0.0 (auth'd, shared box) — tunnel-only is cheap. **slskd**: stale log file (logs went to journald after restart); web UI 0.0.0.0:5030 on a shared box. **Remote path mappings keyed to seedbox IP** — an IP change silently stalls imports.
14. **Wiki build is manual** (operator MacBook push) — move to Forgejo Action/ansible; add built-from-commit marker. **Homepage**: 4 empty widget env slots; AdGuard admin password plaintext in .env; Sunshine tile errors while rig sleeps (expected noise — mark ping-only).
15. **Adoption gaps** (not tech): paperless 0 documents, mealie 0 recipes, navidrome 79 tracks. **Opportunity**: Miniflux→Wallabag native "save to" integration (S). Seerr/maintainerr/recyclarr minor version bumps (Diun now notifies).

## Healthy (no action)
tautulli (outage-window noise only) · seerr (queue-timeout warts during NAS outage) · recyclarr syncs green — TRaSH fully implemented per first-night audit · miniflux (52 feeds, 0 erroring) · mealie · dockge · homepage · wiki (build current) · navidrome · unbound (validating, anchors current) · deluge+slskd operationally · rclone mount + landing chain verified to the arr-DB level · quota 26% · restic/ansible/verification timers green on both hosts.
