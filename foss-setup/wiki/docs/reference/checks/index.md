# Verification checks

Every acceptance/regression check the fleet runs — **304 checks across 35 domains**, generated from `verification/checks.d/` by `scripts/docs/gen-checks-pages.py`. These probe OUTCOMES (does the user-visible result work), not just liveness. See the [Verification runbook](../../runbooks/verification.md) and [Acceptance-testing framework](../../runbooks/acceptance-testing.md).

| Domain | Checks | crit | warn |
|---|---|---|---|
| [alerting](alerting.md) | 11 | 3 | 8 |
| [backups](backups.md) | 13 | 5 | 8 |
| [bug-intake](bug-intake.md) | 5 | 2 | 3 |
| [dns](dns.md) | 6 | 4 | 2 |
| [docker-fleet](docker-fleet.md) | 9 | 0 | 9 |
| [edge](edge.md) | 6 | 1 | 5 |
| [game-saves](game-saves.md) | 2 | 0 | 2 |
| [gaming](gaming.md) | 7 | 3 | 4 |
| [git-hygiene](git-hygiene.md) | 13 | 0 | 13 |
| [ha](ha.md) | 11 | 2 | 9 |
| [host-hygiene](host-hygiene.md) | 7 | 0 | 7 |
| [ipod-abs-sync](ipod-abs-sync.md) | 1 | 0 | 1 |
| [journaling](journaling.md) | 11 | 3 | 8 |
| [media](media.md) | 19 | 7 | 12 |
| [media-aux](media-aux.md) | 6 | 1 | 5 |
| [media-indexers](media-indexers.md) | 2 | 0 | 2 |
| [media-library-correctness](media-library-correctness.md) | 9 | 2 | 7 |
| [media-subtitles](media-subtitles.md) | 1 | 0 | 1 |
| [media-watchable](media-watchable.md) | 4 | 0 | 4 |
| [meme-review](meme-review.md) | 3 | 2 | 1 |
| [mini-services](mini-services.md) | 27 | 9 | 18 |
| [monitoring-coverage](monitoring-coverage.md) | 8 | 1 | 7 |
| [nas-host](nas-host.md) | 7 | 1 | 6 |
| [nas-services](nas-services.md) | 19 | 3 | 16 |
| [network](network.md) | 1 | 0 | 1 |
| [power-journal](power-journal.md) | 3 | 0 | 3 |
| [reading](reading.md) | 27 | 0 | 27 |
| [retro-emulation](retro-emulation.md) | 1 | 0 | 1 |
| [rig](rig.md) | 32 | 2 | 30 |
| [rig-immich-ml](rig-immich-ml.md) | 5 | 1 | 4 |
| [secrets](secrets.md) | 4 | 3 | 1 |
| [seedbox](seedbox.md) | 8 | 4 | 4 |
| [sync](sync.md) | 2 | 0 | 2 |
| [system](system.md) | 9 | 4 | 5 |
| [verification-self](verification-self.md) | 5 | 0 | 5 |

_Total: 304 checks._
