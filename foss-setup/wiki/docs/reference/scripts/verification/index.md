# verification scripts

`foss-setup/scripts/verification/` — 9 script(s).

| Script | Role |
|---|---|
| [`catalog-vhost-parity.py`](catalog-vhost-parity-py.md) | catalog-vhost-parity.py (fix-68 / SM49) — class check for catalog-vs-live drift. |
| [`checksd-runbook-lint.py`](checksd-runbook-lint-py.md) | checksd-runbook-lint — every checks.d `runbook:` must resolve to a real wiki page. |
| [`deploy.sh`](deploy-sh.md) | Deploy the verification suite to mini:/opt/verification — reproducibly, from git. |
| [`reopen-report.py`](reopen-report-py.md) | reopen-report.py (fix-61 / SM47) — the REAL consumer of the reopen bridge. |
| [`repo-secret-scan.py`](repo-secret-scan-py.md) | repo-secret-scan — refuse to ship a committed secret (fix-84). |
| [`stack-mirror-check.sh`](stack-mirror-check-sh.md) | repo↔live drift guard for the mini compose fleet |
| [`tracker-count-check.py`](tracker-count-check-py.md) | fix-43 (L77/L78) tracker-arithmetic regression guard. |
| [`tracker-integrity.py`](tracker-integrity-py.md) | data-level consistency check for the task tracker. |
| [`unit-drift-check.sh`](unit-drift-check-sh.md) | fix-43 (L86 class): hand-copied systemd unit files must |

[← All scripts](../index.md)
