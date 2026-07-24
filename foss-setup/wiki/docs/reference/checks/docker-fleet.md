# Checks — docker-fleet

`foss-setup/verification/checks.d/docker-fleet.yaml` — 9 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `containers-manifest-mini`

mini: running containers match coverage manifest

- **host:** `mini` · **severity:** `warn` · **guards task:** `verify-06` · **enabled:** True
- **expects:** `COVERAGE_OK`

```bash
docker ps --format '{{.Names}}' | grep -v -- '-run-' | LC_ALL=C sort | diff /opt/verification/coverage/mini.containers - && echo COVERAGE_OK
```

## `containers-health-mini`

mini: no unhealthy or restart-looping containers

- **host:** `mini` · **severity:** `warn` · **guards task:** `verify-06` · **enabled:** True
- **expects:** `HEALTH_OK`

```bash
bad=$(docker ps -a --filter health=unhealthy --format '{{.Names}}'; docker ps -a --filter status=restarting --format '{{.Names}}'); if [ -z "$bad" ]; then echo HEALTH_OK; else echo "BAD: $bad"; fi
```

## `containers-manifest-nas`

nas: running containers match coverage manifest

- **host:** `mini` · **severity:** `warn` · **guards task:** `verify-06` · **enabled:** True
- **expects:** `COVERAGE_OK`

```bash
printf '%s\n' "$NAS_SUDO_PASSWORD" | ssh -o BatchMode=yes -o ConnectTimeout=10 nas "sudo -S -p '' /usr/local/bin/docker ps --format '{{.Names}}'" 2>/dev/null | grep -v -- '-run-' | LC_ALL=C sort | diff /opt/verification/coverage/nas.containers - && echo COVERAGE_OK
```

## `containers-health-nas`

nas: no unhealthy or restart-looping containers

- **host:** `mini` · **severity:** `warn` · **guards task:** `verify-06` · **enabled:** True
- **expects:** `HEALTH_OK`

```bash
bad=$(printf '%s\n%s\n' "$NAS_SUDO_PASSWORD" "$NAS_SUDO_PASSWORD" | ssh -o BatchMode=yes -o ConnectTimeout=10 nas "sudo -S -p '' /usr/local/bin/docker ps -a --filter health=unhealthy --format '{{.Names}}'; sudo -S -p '' /usr/local/bin/docker ps -a --filter status=restarting --format '{{.Names}}'" 2>/dev/null); if [ -z "$bad" ]; then echo HEALTH_OK; else echo "BAD: $bad"; fi
```

## `containers-manifest-rig`

rig: running containers match coverage manifest

- **host:** `mini` · **severity:** `warn` · **guards task:** `verify-06` · **enabled:** True
- **expects:** `COVERAGE_OK`

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 rig "docker ps --format '{{.Names}}'" | grep -vE -- '(-run-|^immich_machine_learning$)' | LC_ALL=C sort | diff /opt/verification/coverage/rig.containers - && echo COVERAGE_OK
```

## `containers-health-rig`

rig: no unhealthy or restart-looping containers

- **host:** `rig` · **severity:** `warn` · **guards task:** `verify-06` · **enabled:** True
- **expects:** `HEALTH_OK`

```bash
bad=$({ docker ps -a --filter health=unhealthy --format '{{.Names}}'; docker ps -a --filter status=restarting --format '{{.Names}}'; } | grep -vx immich_machine_learning || true); if [ -z "$bad" ]; then echo HEALTH_OK; else echo "BAD: $bad"; fi
```

## `soularr-not-crashlooping`

nas: soularr job completes cycles (no Fatal error in recent logs)

- **host:** `mini` · **severity:** `warn` · **guards task:** `verify-06` · **enabled:** True
- **expects:** `^fatal_errors=0$`

```bash
n=$(printf '%s\n' "$NAS_SUDO_PASSWORD" | ssh -o BatchMode=yes -o ConnectTimeout=10 nas "sudo -S -p '' /usr/local/bin/docker logs soularr --since 2h 2>&1" 2>/dev/null | grep -c 'Fatal error'); echo "fatal_errors=$n"
```

## `systemd-failed-mini`

mini: no failed systemd units

- **host:** `mini` · **severity:** `warn` · **guards task:** `verify-06` · **enabled:** True
- **expects:** `NO_FAILED_UNITS`

```bash
systemctl --failed --no-legend | grep . || echo NO_FAILED_UNITS
```

## `systemd-failed-rig`

rig: no failed systemd units

- **host:** `rig` · **severity:** `warn` · **guards task:** `verify-06` · **enabled:** True
- **expects:** `NO_FAILED_UNITS`

```bash
systemctl --failed --no-legend | grep . || echo NO_FAILED_UNITS
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
