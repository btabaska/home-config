# Checks — dns

`foss-setup/verification/checks.d/dns.yaml` — 5 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `dns-mini-internal`

AdGuard (mini) resolves internal name home.tabaska.us

- **host:** `mini` · **severity:** `crit` · **guards task:** `dns-01` · **enabled:** True
- **expects:** `^192\.168\.10\.[0-9]+$`

```bash
dig +short +time=3 +tries=1 @192.168.10.2 home.tabaska.us
```

## `dns-mini-external`

AdGuard (mini) resolves external name example.com

- **host:** `mini` · **severity:** `crit` · **guards task:** `dns-01` · **enabled:** True
- **expects:** `^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+`

```bash
dig +short +time=3 +tries=1 @192.168.10.2 example.com
```

## `dns-mini-unbound-upstream`

unbound upstream on mini answers directly (127.0.0.1:5335)

- **host:** `mini` · **severity:** `warn` · **guards task:** `dns-01` · **enabled:** True
- **expects:** `^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+`

```bash
dig +short +time=3 +tries=1 @127.0.0.1 -p 5335 example.com
```

## `dns-nas-internal`

Secondary resolver (NAS 192.168.10.4) resolves home.tabaska.us

- **host:** `mini` · **severity:** `crit` · **guards task:** `dns-02` · **enabled:** True
- **expects:** `^192\.168\.10\.[0-9]+$`

```bash
dig +short +time=3 +tries=1 @192.168.10.4 home.tabaska.us
```

## `dns-nas-external`

Secondary resolver (NAS 192.168.10.4) resolves example.com

- **host:** `mini` · **severity:** `crit` · **guards task:** `dns-02` · **enabled:** True
- **expects:** `^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+`

```bash
for i in 1 2 3; do dig +short +time=3 +tries=1 @192.168.10.4 example.com && break; sleep 2; done
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
