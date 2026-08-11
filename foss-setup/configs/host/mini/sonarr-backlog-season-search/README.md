# sonarr-backlog-season-search — throttled backlog clearer (mini host unit)

Replaces `sonarr-backlog-sweep` (2026-08-10, torn down 2026-08-11 — archived at
`mini:/opt/archives/sonarr-backlog-sweep-teardown-20260811.tar.gz`). The old
sweeper fired per-episode `EpisodeSearch` batches (~150 indexer queries/hour),
which exhausted IPTorrents' 600-queries/24h budget — over-budget searches
return **0 results** through Prowlarr, so the backlog looked unsearchable — and
its queue janitor ran during the 2026-08-11 NAS SQLite lock storm.

The replacement leans on the 2026-08-11 lesson: **old shows complete via
season packs**. Each run picks the single highest-yield season (most missing
monitored episodes, aired >7 days, not attempted in 14 days), fires ONE
`SeasonSearch`, and exits. Timer = every 2 hours → max 12 season searches/day.
Skips when a search is already running or the queue has >15 warning items.

Not ansible-managed — installed by hand, this directory is the doc-only mirror
(see `configs/host/mini/README` convention):

```
sudo install -m 755 sonarr-backlog-season-search.py /usr/local/sbin/
sudo install -m 644 sonarr-backlog-season-search.{service,timer} /etc/systemd/system/
# /etc/default/sonarr-backlog-season-search from the .env.example (root:root 600),
# key from vault arr_api_keys.sonarr
sudo systemctl daemon-reload && sudo systemctl enable --now sonarr-backlog-season-search.timer
```

State (`/var/lib/sonarr-backlog-season-search/state.json`) records
season→last-search epoch; delete it to reset the 14-day cooldowns. Failures
page via `OnFailure=ntfy-notify@`. Related guard: verification check
`iptorrents-idsearch-returns-results` (media-indexers.yaml) catches the
budget-exhausted/0-results failure mode this cadence is designed to avoid.
