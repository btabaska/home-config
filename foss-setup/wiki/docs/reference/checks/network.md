# Checks — network

`foss-setup/verification/checks.d/network.yaml` — 1 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `net-trusted-to-iot-reachable`

Trusted->IoT control path open (Hue bridge 192.168.20.100:80 reachable)

- **host:** `mini` · **severity:** `warn` · **guards task:** `net-05` · **enabled:** True
- **expects:** `^tok=ok$`

```bash
timeout 4 bash -c 'echo > /dev/tcp/192.168.20.100/80' 2>/dev/null && echo tok=ok || echo tok=BAD
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
