# Checks — bug-intake

`foss-setup/verification/checks.d/bug-intake.yaml` — 5 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `bug-intake-form-armed`

bug.tabaska.us form is served + workflow active (/form/<id> renders fields)

- **host:** `mini` · **severity:** `crit` · **guards task:** `bug-01` · **enabled:** True
- **expects:** `What happened`

```bash
curl -s -m 8 http://localhost:5678/form/8f2c1a4b-6d3e-4a90-b1c2-a1b2c3d4e5f6
```

## `bug-intake-homepage-tile`

the 'Report a Problem' household tile is present on Homepage

- **host:** `mini` · **severity:** `warn` · **guards task:** `bug-01` · **enabled:** True
- **expects:** `Report a Problem`

```bash
curl -s -m 8 http://localhost:3010/api/services
```

## `bug-intake-e2e`

synthetic submit -> labeled Forgejo issue in home/household-bugs (then deleted)

- **host:** `mini` · **severity:** `crit` · **guards task:** `bug-01` · **enabled:** True
- **expects:** `BUGREPORT_OK`

```bash
python3 /opt/verification/bin/bugreport-e2e.py
```

## `bug-triage-evidence-armed`

bug-triage-evidence read-only collector is healthy (docker socket + probes)

- **host:** `mini` · **severity:** `warn` · **guards task:** `bug-02` · **enabled:** True
- **expects:** `healthy`

```bash
docker inspect --format '{{.State.Health.Status}}' bug-triage-evidence
```

## `bug-triage-e2e`

synthetic report -> auto-triage comment appears on the Forgejo issue (degrade-aware)

- **host:** `mini` · **severity:** `warn` · **guards task:** `bug-02` · **enabled:** True
- **expects:** `^BUGTRIAGE_(OK|SKIP_MODEL_UNAVAILABLE)`

```bash
python3 /opt/verification/bin/bugtriage-e2e.py
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
