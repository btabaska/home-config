# NAS syslog-ng — custom message filters (doc-only mirror)

Synology DSM's syslog-ng config lives under `/etc/syslog-ng/` (system-owned,
regenerated on DSM updates). The DSM-safe extension point is the **persistent**
`/usr/local/etc/syslog-ng/patterndb.d/` tree, which the main config pulls in via:

```
@include "/usr/local/etc/syslog-ng/patterndb.d/"                        # filter definitions
```

and, inside the `f_messages` filter (message.conf), via:

```
@include "/usr/local/etc/syslog-ng/patterndb.d/include/not2msg/"        # "exclude from /var/log/messages" rules
```

Synology's own packages (ContainerManager, HyperBackup, …) register their filters
here; these files follow the exact same pattern and survive DSM updates because
`/usr/local` is not wiped on upgrade.

## fix-69 / SL1 — synologand geo-lookup flood

`synologand` logs `abnormal_login.cpp:112 Failed to get the info whose ip address
is [100.x.x.x]` on **every** tailnet (CGNAT `100.64.0.0/10`) login — the source
IP simply has no geo record. Benign per-event, but it flooded 7–8k lines into
each `/var/log/messages` and drowned real DSM signal (fleet-sweep 2026-08-02 SL1).

Two files stop it (matching only that benign message — real `AbnormalAccess`
security alerts, routed to `/var/lib/diskutil/abnormal_access.log`, are untouched):

| repo file | live path (root:root 0644) |
|-----------|----------------------------|
| `synologand-geo.conf` | `/usr/local/etc/syslog-ng/patterndb.d/synologand-geo.conf` |
| `include/not2msg/synologand_geo` | `/usr/local/etc/syslog-ng/patterndb.d/include/not2msg/synologand_geo` |

### Deploy / re-apply (e.g. after a DSM major upgrade wipes them)

SFTP/scp is disabled on the NAS, so stage via `cat >` then `sudo install`:

```sh
# stage (no sudo)
ssh nas 'cat > /tmp/synologand-geo.conf'          < synologand-geo.conf
ssh nas 'cat > /tmp/synologand_geo'               < include/not2msg/synologand_geo
# install + validate + reload (sudo needs the vault password piped)
printf '%s\n' "$PW" | ssh nas 'sudo -S bash -c "
  D=/usr/local/etc/syslog-ng/patterndb.d
  install -m0644 -oroot -groot /tmp/synologand-geo.conf \$D/synologand-geo.conf
  install -m0644 -oroot -groot /tmp/synologand_geo      \$D/include/not2msg/synologand_geo
  rm -f /tmp/synologand-geo.conf /tmp/synologand_geo
  syslog-ng --syntax-only && syslog-ng-ctl reload"'
```

Verify: after reload, no new `abnormal_login` line lands in `/var/log/messages`
even across fresh tailnet logins (`grep -c abnormal_login /var/log/messages`
stops climbing). Guarded by check **`nas-syslog-geo-filter-present`** (task fix-69,
nas-host.yaml) — both files must exist.
