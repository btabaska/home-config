# Checks — rig-host-stability

`foss-setup/verification/checks.d/rig-host-stability.yaml` — 6 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `rig-poweroff-inhibit`

rig ignores accidental poweroff (logind power-key=ignore + polkit desktop-shutdown deny)

- **host:** `rig` · **severity:** `warn` · **guards task:** `fix-64` · **enabled:** True
- **expects:** `^INHIBIT_OK`

```bash
hpk=$(busctl get-property org.freedesktop.login1 /org/freedesktop/login1 org.freedesktop.login1.Manager HandlePowerKey 2>/dev/null | awk '{print $2}' | tr -d '"'); pkcheck --action-id org.freedesktop.login1.power-off-multiple-sessions --process $$ >/dev/null 2>&1 && pol=allowed || pol=denied; if [ "$hpk" = ignore ] && [ "$pol" = denied ]; then echo "INHIBIT_OK hpk=$hpk poweroff=$pol"; else echo "INHIBIT_WEAK hpk=$hpk poweroff=$pol"; fi
```

## `rig-clock-sane`

rig clock within 120s of mini + RTC in UTC + NTP synced (SM33 skew guard)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-64` · **enabled:** True
- **expects:** `^CLOCK_OK`

```bash
R=$(ssh -o BatchMode=yes -o ConnectTimeout=10 rig 'echo $(date -u +%s) $(timedatectl show -p LocalRTC --value) $(timedatectl show -p NTPSynchronized --value)' 2>/dev/null); RT=$(echo "$R" | awk '{print $1}'); LRTC=$(echo "$R" | awk '{print $2}'); NTP=$(echo "$R" | awk '{print $3}'); MT=$(date -u +%s); D=$((MT-${RT:-0})); D=${D#-}; if [ -n "$RT" ] && [ "$D" -lt 120 ] && [ "$LRTC" = no ] && [ "$NTP" = yes ]; then echo "CLOCK_OK offset=${D}s rtc=$LRTC ntp=$NTP"; else echo "CLOCK_BAD offset=${D}s rtc=$LRTC ntp=$NTP rt=$RT"; fi
```

## `rig-no-crashloop-unit`

no rig unit is crash-looping (>20 systemd restarts/10min) — SM14 class

- **host:** `rig` · **severity:** `warn` · **guards task:** `fix-64` · **enabled:** True
- **expects:** `^NO_CRASHLOOP`

```bash
n=$(journalctl --since '-10 min' 2>/dev/null | grep -c 'Scheduled restart job, restart counter is at'); top=$(journalctl --since '-10 min' 2>/dev/null | grep 'Scheduled restart job, restart counter is at' | grep -oE '[[:graph:]]+: Scheduled' | sed 's/: Scheduled//' | sort | uniq -c | sort -rn | head -1 | tr -s ' '); if [ "${n:-0}" -le 20 ]; then echo "NO_CRASHLOOP restarts10m=${n:-0}"; else echo "CRASHLOOP restarts10m=$n top=$top"; fi
```

## `rig-ml-window-catchup-clean`

immich-ml-window@on is not left failed (SL10 daytime-catch-up guard)

- **host:** `rig` · **severity:** `warn` · **guards task:** `fix-64` · **enabled:** True
- **expects:** `^ML_ON_CLEAN`

```bash
r=$(systemctl is-failed immich-ml-window@on.service 2>/dev/null || true); if [ "$r" = failed ]; then echo "ML_ON_FAILED"; else echo "ML_ON_CLEAN state=$r"; fi
```

## `rig-crash-storm-quiet`

no rig binary segfaults >3x/24h (SM13/SM25/SL9 crash-recurrence escalation)

- **host:** `rig` · **severity:** `warn` · **guards task:** `fix-64` · **enabled:** True
- **expects:** `^NO_CRASH_STORM`

```bash
top=$(coredumpctl list --since '-24h' --no-pager 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i ~ /^\//) print $i}' | sed 's#.*/##' | sort | uniq -c | sort -rn | head -1 | tr -s ' '); n=$(echo "$top" | awk '{print $1+0}'); if [ "${n:-0}" -le 3 ]; then echo "NO_CRASH_STORM max24h=${n:-0} (${top:-none})"; else echo "CRASH_STORM $top"; fi
```

## `rig-mdns-fw-quiet`

rig mDNS conflict-free + cachyos.local resolves + UFW noise silenced (SM15/SL12)

- **host:** `rig` · **severity:** `warn` · **guards task:** `fix-64` · **enabled:** True
- **expects:** `^QUIET`

```bash
ac=$(journalctl -u avahi-daemon --since '-5 min' 2>/dev/null | grep -c 'Host name conflict'); res=$(avahi-resolve -4 -n cachyos.local 2>/dev/null | grep -c '192.168.10.12'); noisy=$(journalctl -k --since '-2 min' 2>/dev/null | grep 'UFW BLOCK' | grep -cE 'DPT=21027|SRC=192.168.10.177'); if [ "${ac:-99}" -le 5 ] && [ "${res:-0}" -ge 1 ] && [ "${noisy:-99}" -eq 0 ]; then echo "QUIET conflicts5m=$ac fwnoise2m=$noisy resolves=$res"; else echo "NOISY conflicts5m=$ac fwnoise2m=$noisy resolves=$res"; fi
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
