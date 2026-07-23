# Verification checks

Every acceptance/regression check the fleet runs — **271 checks across 28 domains**, generated from `verification/checks.d/` by `scripts/docs/gen-checks-pages.py`. These probe OUTCOMES (does the user-visible result work), not just liveness. See the [Verification runbook](../../runbooks/verification.md) and [Acceptance-testing framework](../../runbooks/acceptance-testing.md).

| Domain | Checks | crit | warn |
|---|---|---|---|
| [alerting](alerting.md) | 11 | 3 | 8 |
| [backups](backups.md) | 13 | 5 | 8 |
| [dns](dns.md) | 6 | 4 | 2 |
| [docker-fleet](docker-fleet.md) | 9 | 0 | 9 |
| [edge](edge.md) | 5 | 1 | 4 |
| [gaming](gaming.md) | 5 | 2 | 3 |
| [git-hygiene](git-hygiene.md) | 10 | 0 | 10 |
| [ha](ha.md) | 10 | 2 | 8 |
| [host-hygiene](host-hygiene.md) | 7 | 0 | 7 |
| [journaling](journaling.md) | 11 | 3 | 8 |
| [media](media.md) | 18 | 7 | 11 |
| [media-aux](media-aux.md) | 6 | 1 | 5 |
| [media-library-correctness](media-library-correctness.md) | 7 | 0 | 7 |
| [media-watchable](media-watchable.md) | 4 | 0 | 4 |
| [mini-services](mini-services.md) | 27 | 9 | 18 |
| [monitoring-coverage](monitoring-coverage.md) | 8 | 1 | 7 |
| [nas-host](nas-host.md) | 7 | 1 | 6 |
| [nas-services](nas-services.md) | 19 | 3 | 16 |
| [network](network.md) | 1 | 0 | 1 |
| [power-journal](power-journal.md) | 3 | 0 | 3 |
| [reading](reading.md) | 21 | 0 | 21 |
| [rig](rig.md) | 31 | 2 | 29 |
| [rig-immich-ml](rig-immich-ml.md) | 4 | 2 | 2 |
| [secrets](secrets.md) | 4 | 3 | 1 |
| [seedbox](seedbox.md) | 8 | 4 | 4 |
| [sync](sync.md) | 2 | 0 | 2 |
| [system](system.md) | 9 | 4 | 5 |
| [verification-self](verification-self.md) | 5 | 0 | 5 |

_Total: 271 checks._
