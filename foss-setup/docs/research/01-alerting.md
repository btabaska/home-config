# Alerting stack audit (agent complete) — HEADLINE OF THE NIGHT
CORE: ntfy subscribers=0 all day — every alert published to date reached NO ONE. Live proof: tonight's mini docker restart (22:18) alerted nobody.
Phone-ping fix chain (in order, all S/M):
 1. HIGH: all vhosts serve Caddy internal-CA certs (CLOUDFLARE_API_TOKEN empty) — iPhone refuses TLS. Fix = Cloudflare DNS-01 (fixes ALL 40 vhosts; token pending user) — alt: install CA profile per device (clunky).
 2. HIGH: NTFY_UPSTREAM_BASE_URL missing — iOS push needs https://ntfy.sh relay (only message IDs go upstream). One env line.
 3. MED: NTFY_BASE_URL mismatch (set to tailscale :8080, should be https://ntfy.tabaska.us).
 4. Blank page = EXPECTED (deny-all + per-browser localStorage subs). Document + create read-only "phone" user (admin pw in /opt/stacks/ntfy/.admin-password, NOT in vault — add it).
 5. Then: iOS app + subscribe: verification, backups, diun (+uptime, healthchecks when wired).
DIUN: topic never exercised; publishes to https vhost whose cert Go rejects → will fail when it fires. Fix: join edge network, http://ntfy:80. ALSO watches mini only — NAS containers unwatched → second Diun on NAS (M).
UPTIME KUMA: notification table EMPTY (detects, tells no one) + only 11 NAS monitors, 34/45 catalog services unmonitored (all mini svcs incl vaultwarden/adguard/caddy). Fix: ntfy channel default-on + catalog-driven bootstrap (M).
HEALTHCHECKS: 0 checks 0 integrations — no dead-man coverage for timers (the "job never ran" failure class). Wire restic/exports/HyperBackup/rclone pings + ntfy (M).
BESZEL: hub monitors only the MacBook(!); mini agent runs but unregistered; no NAS/rig; 0 alerts. Register mini+NAS, down+disk alerts (M).
NAS health script: DSM task cron '0,15,30,45 0 * * *' = only 00:00-00:45 daily (schedule bug!) + health.env missing so its ntfy never fires (S).
OVERLAP: 4 tools = 4 distinct roles (updates/up-down/dead-man/metrics) — keep all, converge on ntfy transport; gaps are wiring not redundancy.
