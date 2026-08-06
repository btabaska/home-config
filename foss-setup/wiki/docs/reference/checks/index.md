# Verification checks

Every acceptance/regression check the fleet runs — **373 checks across 42 domains**, generated from `verification/checks.d/` by `scripts/docs/gen-checks-pages.py`. These probe OUTCOMES (does the user-visible result work), not just liveness. See the [Verification runbook](../../runbooks/verification.md) and [Acceptance-testing framework](../../runbooks/acceptance-testing.md).

| Domain | Checks | crit | warn |
|---|---|---|---|
| [alerting](alerting.md) | 15 | 3 | 12 |
| [backups](backups.md) | 13 | 5 | 8 |
| [bug-intake](bug-intake.md) | 7 | 2 | 5 |
| [dns](dns.md) | 6 | 4 | 2 |
| [docker-fleet](docker-fleet.md) | 9 | 0 | 9 |
| [edge](edge.md) | 6 | 1 | 5 |
| [game-saves](game-saves.md) | 2 | 0 | 2 |
| [gaming](gaming.md) | 8 | 3 | 5 |
| [git-hygiene](git-hygiene.md) | 16 | 0 | 16 |
| [ha](ha.md) | 12 | 2 | 10 |
| [host-hygiene](host-hygiene.md) | 10 | 0 | 10 |
| [ipod-abs-sync](ipod-abs-sync.md) | 1 | 0 | 1 |
| [journaling](journaling.md) | 12 | 3 | 9 |
| [lan-exposure](lan-exposure.md) | 4 | 0 | 4 |
| [local-ai](local-ai.md) | 10 | 0 | 10 |
| [media](media.md) | 21 | 7 | 14 |
| [media-aux](media-aux.md) | 6 | 1 | 5 |
| [media-indexers](media-indexers.md) | 4 | 0 | 4 |
| [media-library-correctness](media-library-correctness.md) | 9 | 2 | 7 |
| [media-subtitles](media-subtitles.md) | 2 | 0 | 2 |
| [media-watchable](media-watchable.md) | 4 | 0 | 4 |
| [meme-review](meme-review.md) | 3 | 2 | 1 |
| [mini-services](mini-services.md) | 28 | 9 | 19 |
| [monitoring-coverage](monitoring-coverage.md) | 9 | 1 | 8 |
| [nas-host](nas-host.md) | 8 | 1 | 7 |
| [nas-io-storm](nas-io-storm.md) | 2 | 0 | 2 |
| [nas-services](nas-services.md) | 24 | 3 | 21 |
| [network](network.md) | 1 | 0 | 1 |
| [notes](notes.md) | 1 | 0 | 1 |
| [power-journal](power-journal.md) | 3 | 0 | 3 |
| [reading](reading.md) | 30 | 0 | 30 |
| [retro-emulation](retro-emulation.md) | 1 | 0 | 1 |
| [rig](rig.md) | 32 | 2 | 30 |
| [rig-host-stability](rig-host-stability.md) | 6 | 0 | 6 |
| [rig-immich-ml](rig-immich-ml.md) | 5 | 1 | 4 |
| [secrets](secrets.md) | 6 | 3 | 3 |
| [seedbox](seedbox.md) | 13 | 5 | 8 |
| [soularr-backlog](soularr-backlog.md) | 2 | 0 | 2 |
| [sync](sync.md) | 3 | 0 | 3 |
| [system](system.md) | 10 | 5 | 5 |
| [verification-env-integrity](verification-env-integrity.md) | 2 | 2 | 0 |
| [verification-self](verification-self.md) | 7 | 0 | 7 |

_Total: 373 checks._
