# Checks — bug-intake

`foss-setup/verification/checks.d/bug-intake.yaml` — 7 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

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

## `bug-intake-ntfy-notify-branch`

bug-report ntfy notify leg: n8n's NTFY_TOKEN authenticates + retains write to 'bugs'

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-67` · **enabled:** True
- **expects:** `^ntfy_bugs_notify=ok `

```bash
U=$(docker exec n8n sh -c 'wget -qO- --header="Authorization: Bearer $NTFY_TOKEN" http://ntfy:80/v1/account 2>/dev/null' | grep -c buguser); A=$(docker exec ntfy ntfy access buguser 2>/dev/null | grep -c 'write-only access to topic bugs'); if [ "$U" -ge 1 ] && [ "$A" -ge 1 ]; then echo "ntfy_bugs_notify=ok token=valid acl=write"; else echo "ntfy_bugs_notify=FAIL token_hits=$U acl_hits=$A"; fi
```

## `bug-intake-no-probe-residue`

no stale synthetic bug-report probe issue lingering in home/household-bugs (SL25)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-67` · **enabled:** True
- **expects:** `^PROBE_RESIDUE=0$`

```bash
curl -s -m 10 -H "Authorization: token $FORGEJO_PROBE_TOKEN" "$FORGEJO_API_URL/repos/home/household-bugs/issues?state=open&type=issues&limit=50" | python3 -c "import sys,json; d=json.load(sys.stdin); r=[i['number'] for i in d if 'n8n-bugreport-probe' in (i.get('title') or '')]; print('PROBE_RESIDUE=%d%s'%(len(r),(' '+str(r)) if r else ''))"
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
