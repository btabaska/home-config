# Verification checks

Every acceptance/regression check the fleet runs — **226 checks across 25 domains**, generated from `verification/checks.d/` by `scripts/docs/gen-checks-pages.py`. These probe OUTCOMES (does the user-visible result work), not just liveness. See the [Verification runbook](../../runbooks/verification.md) and [Acceptance-testing framework](../../runbooks/acceptance-testing.md).

| Domain | Checks | crit | warn |
|---|---|---|---|
| [alerting](alerting.md) | 11 | 3 | 8 |
| [backups](backups.md) | 13 | 5 | 8 |
| [dns](dns.md) | 5 | 4 | 1 |
| [docker-fleet](docker-fleet.md) | 9 | 0 | 9 |
| [edge](edge.md) | 5 | 1 | 4 |
| [gaming](gaming.md) | 5 | 2 | 3 |
| [git-hygiene](git-hygiene.md) | 9 | 0 | 9 |
| [ha](ha.md) | 10 | 2 | 8 |
| [host-hygiene](host-hygiene.md) | 7 | 0 | 7 |
| [media](media.md) | 18 | 7 | 11 |
| [media-aux](media-aux.md) | 6 | 1 | 5 |
| [media-library-correctness](media-library-correctness.md) | 4 | 0 | 4 |
| [media-watchable](media-watchable.md) | 4 | 0 | 4 |
| [mini-services](mini-services.md) | 27 | 10 | 17 |
| [monitoring-coverage](monitoring-coverage.md) | 6 | 1 | 5 |
| [nas-host](nas-host.md) | 5 | 1 | 4 |
| [nas-services](nas-services.md) | 17 | 3 | 14 |
| [network](network.md) | 1 | 0 | 1 |
| [power-journal](power-journal.md) | 3 | 0 | 3 |
| [reading](reading.md) | 8 | 0 | 8 |
| [rig](rig.md) | 31 | 2 | 29 |
| [secrets](secrets.md) | 4 | 3 | 1 |
| [seedbox](seedbox.md) | 6 | 4 | 2 |
| [system](system.md) | 8 | 4 | 4 |
| [verification-self](verification-self.md) | 4 | 0 | 4 |

_Total: 226 checks._
