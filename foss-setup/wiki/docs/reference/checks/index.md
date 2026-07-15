# Verification checks

Every acceptance/regression check the fleet runs — **110 checks across 12 domains**, generated from `verification/checks.d/` by `scripts/docs/gen-checks-pages.py`. These probe OUTCOMES (does the user-visible result work), not just liveness. See the [Verification runbook](../../runbooks/verification.md) and [Acceptance-testing framework](../../runbooks/acceptance-testing.md).

| Domain | Checks | crit | warn |
|---|---|---|---|
| [alerting](alerting.md) | 11 | 3 | 8 |
| [backups](backups.md) | 5 | 3 | 2 |
| [dns](dns.md) | 5 | 4 | 1 |
| [docker-fleet](docker-fleet.md) | 9 | 0 | 9 |
| [git-hygiene](git-hygiene.md) | 4 | 0 | 4 |
| [ha](ha.md) | 6 | 2 | 4 |
| [media](media.md) | 14 | 6 | 8 |
| [mini-services](mini-services.md) | 20 | 6 | 14 |
| [nas-services](nas-services.md) | 15 | 3 | 12 |
| [network](network.md) | 1 | 0 | 1 |
| [rig](rig.md) | 12 | 0 | 12 |
| [system](system.md) | 8 | 4 | 4 |

_Total: 110 checks._
