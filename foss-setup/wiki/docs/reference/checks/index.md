# Verification checks

Every acceptance/regression check the fleet runs — **94 checks across 12 domains**, generated from `verification/checks.d/` by `scripts/docs/gen-checks-pages.py`. These probe OUTCOMES (does the user-visible result work), not just liveness. See the [Verification runbook](../../runbooks/verification.md) and [Acceptance-testing framework](../../runbooks/acceptance-testing.md).

| Domain | Checks | crit | warn |
|---|---|---|---|
| [alerting](alerting.md) | 11 | 3 | 8 |
| [backups](backups.md) | 5 | 3 | 2 |
| [dns](dns.md) | 5 | 4 | 1 |
| [docker-fleet](docker-fleet.md) | 9 | 0 | 9 |
| [git-hygiene](git-hygiene.md) | 3 | 0 | 3 |
| [ha](ha.md) | 5 | 2 | 3 |
| [media](media.md) | 13 | 6 | 7 |
| [mini-services](mini-services.md) | 18 | 6 | 12 |
| [nas-services](nas-services.md) | 9 | 3 | 6 |
| [network](network.md) | 1 | 0 | 1 |
| [rig](rig.md) | 7 | 0 | 7 |
| [system](system.md) | 8 | 4 | 4 |

_Total: 94 checks._
