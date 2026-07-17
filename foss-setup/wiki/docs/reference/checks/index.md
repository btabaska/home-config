# Verification checks

Every acceptance/regression check the fleet runs — **152 checks across 16 domains**, generated from `verification/checks.d/` by `scripts/docs/gen-checks-pages.py`. These probe OUTCOMES (does the user-visible result work), not just liveness. See the [Verification runbook](../../runbooks/verification.md) and [Acceptance-testing framework](../../runbooks/acceptance-testing.md).

| Domain | Checks | crit | warn |
|---|---|---|---|
| [alerting](alerting.md) | 11 | 3 | 8 |
| [backups](backups.md) | 9 | 4 | 5 |
| [dns](dns.md) | 5 | 4 | 1 |
| [docker-fleet](docker-fleet.md) | 9 | 0 | 9 |
| [edge](edge.md) | 5 | 1 | 4 |
| [git-hygiene](git-hygiene.md) | 4 | 0 | 4 |
| [ha](ha.md) | 6 | 2 | 4 |
| [media](media.md) | 18 | 7 | 11 |
| [media-watchable](media-watchable.md) | 4 | 0 | 4 |
| [mini-services](mini-services.md) | 26 | 10 | 16 |
| [nas-services](nas-services.md) | 15 | 3 | 12 |
| [network](network.md) | 1 | 0 | 1 |
| [rig](rig.md) | 21 | 2 | 19 |
| [secrets](secrets.md) | 4 | 3 | 1 |
| [seedbox](seedbox.md) | 6 | 4 | 2 |
| [system](system.md) | 8 | 4 | 4 |

_Total: 152 checks._
