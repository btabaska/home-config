# Rig host stability — 24/7 mandate, power protocol, clock, crash hygiene

The rig (CachyOS `192.168.10.12`) runs the AI stack, game servers and Suwayomi
under a **24/7 mandate** (suspend is masked). The 2026-08-02 fleet sweep found a
cluster of stability defects (`fix-64`, findings SH4 / SM12 / SM53 / SM33 / SM13 /
SM14 / SM15 / SM25 / SL9 / SL10 / SL12). This page is the operator runbook for the
guards that were put in place and how to work with (or override) them.

Host config lives under `foss-setup/configs/host/rig/` and is **documentation-only**
— nothing re-applies it, so every change must land live **and** in the repo.

## Powering the rig off — operator protocol

**Do not power the rig off casually.** It is a 24/7 host; a poweroff takes down
the AI stack, game servers (friend-facing), the Suwayomi→Komga manga feed, the
journaling coach and the syncthing node until someone notices and powers it back
on. The 2026-07-31 incident was exactly this: a desktop **"Shut Down"** click left
the rig dark for **~27 hours**.

The accidental paths are now technically inhibited (see below), but the human rule
stands:

1. **Announce first.** A deliberate rig poweroff must be announced/gated (household
   heads-up), because friends' game servers and remote AI coding go down with it.
2. **Use the explicit CLI path.** Power off only via a root shell:
   ```
   sudo systemctl poweroff       # or: sudo shutdown -h now
   ```
   This is the *only* supported shutdown path. It bypasses logind/polkit (root
   talks to systemd directly), so the inhibits below do not block it.
3. **Prefer a reboot over a poweroff** when you can — a reboot self-recovers on the
   next boot; a poweroff needs a human (or Wake-on-LAN, see `wake-the-rig.md`) to
   bring it back.

### What is inhibited (and what still works)

| Path | Before | Now |
|---|---|---|
| Physical power-key **short press** | poweroff | **ignored** (`logind` `HandlePowerKey=ignore`) |
| Physical power-key **long hold (~4s)** | — | still powers off (deliberate hardware escape) |
| Desktop **"Shut Down" / "Log Out → Shut Down"** menu, `loginctl poweroff`, Ctrl-Alt-Del | poweroff | **denied** (polkit rule) |
| `sudo systemctl poweroff` / `sudo shutdown` (root CLI) | works | **still works** (planned shutdown) |
| Reboot (any path) | works | still works (self-recovers) |

Sources: `configs/host/rig/logind/10-ignore-power-key.conf` (→
`/etc/systemd/logind.conf.d/`) and
`configs/host/rig/polkit/10-inhibit-desktop-poweroff.rules` (→
`/etc/polkit-1/rules.d/`). Regression-monitored by the `rig-poweroff-inhibit` check.
Detection that the host went dark anyway: the `rig-*` HTTP checks + the off-mini
dead-man (see `alerting.md`) + fast-tier WoL self-heal (`wake-the-rig.md`).

## Clock / RTC skew (SM33)

The rig **dual-boots Windows** (`efibootmgr` shows a Windows Boot Manager entry).
Windows writes the hardware RTC in **local time** by default; Linux expects it in
**UTC**. After a Windows session the rig booted with the clock **4h behind**, which
falsified the journal timeline and made every persistent timer fire against a bogus
wall time until NTP stepped the clock.

Guards in place:

- **RTC is UTC** on the Linux side (`timedatectl set-local-rtc 0`; verify
  `timedatectl show -p LocalRTC` → `no`). Do **not** run `set-local-rtc 1`.
- **Timers wait for real time.** `systemd-time-wait-sync.service` is enabled, so
  `time-sync.target` only completes once NTP has actually synchronised. The
  time-sensitive rig units (`immich-ml-window@.service`, `playit-udp-guard.service`)
  are ordered `After=time-sync.target`, so a skewed-clock boot no longer runs them
  at a false time.
- **The durable fix is on the Windows side** — set Windows to keep the RTC in UTC.
  As an Administrator in Windows, either run:
  ```
  reg add "HKLM\SYSTEM\CurrentControlSet\Control\TimeZoneInformation" /v RealTimeIsUniversal /t REG_DWORD /d 1 /f
  ```
  or apply the equivalent registry key, then reboot. Until that is set, a skew can
  recur after any Windows session; the `rig-clock-sane` check (cross-checks rig's
  UTC clock against the mini's) will page if the offset exceeds 120s.

## moondeckbuddy crash-loop (SM14)

The `moondeckbuddy.service` **user** unit exec'd a MoonDeck AppImage that no longer
exists (`/home/btabaska/Applications/MoonDeckBuddy-1.9.2-…AppImage`), exiting 127
and auto-restarting every ~10s — **76,451 restarts** by 07-25, flooding the journal.
It is now **disabled + stopped**:

```
systemctl --user disable --now moondeckbuddy.service
```

**To restore MoonDeck** (Steam Deck game-streaming companion) if wanted: reinstall
the MoonDeckBuddy AppImage to `~/Applications/`, update the `ExecStart=` path in
`~/.config/systemd/user/moondeckbuddy.service` to the new filename, then
`systemctl --user enable --now moondeckbuddy.service`. The crash-loop class is
monitored by `rig-no-crashloop-unit`.

## Container / engine crashes (SM13, SM25, SL9)

Single-occurrence crashes that auto-recovered, kept as a **passive watch**:

- **lumiverse** — a `containerd-shim` SIGSEGV killed it once (exit 137); docker's
  `unless-stopped` policy restarted it in ~1s.
- **Palworld** — the game engine segfaulted twice in 4 days; `unless-stopped`
  recovered it both times (players are dropped at crash time).

Both containers already run `restart: unless-stopped`, so recovery is automatic. The
`rig-crash-storm-quiet` check escalates if any single binary crashes **>3 times in
24h** (the recurrence threshold the sweep asked for — below the RestartCount>3
restart-loop alarm). A repeat `containerd-shim` segfault should trigger a
containerd/runc version + memory review.

## Log-noise hygiene (SM15 avahi, SL12 ufw)

- **avahi** mDNS is restricted to the physical LAN (`allow-interfaces=enp10s0`) so
  docker veth churn no longer triggers a hostname-conflict storm — see
  `configs/host/rig/avahi/README.md`.
- **UFW** silently drops known-benign discovery noise (Syncthing IPv6 multicast
  `21027`, the Samsung TV at `192.168.10.177`) before the logging chain — see
  `configs/host/rig/ufw/README.md`.

Both are monitored by `rig-mdns-fw-quiet` (avahi conflicts == 0, UFW block rate low).

## Reboot pattern (SM12)

Three reboots in the 7 days before the sweep were root-caused: 07-25 (an
unexplained abrupt end — the only true crash, watched via `rig-crash-storm-quiet`),
07-29 (a clean operator recovery reboot after an llama-server segfault storm), and
07-31 (the plasma-shutdown poweroff — now inhibited). None were update-driven.

## Verification checks (this cluster)

| Check | Guards | Signal |
|---|---|---|
| `rig-poweroff-inhibit` | SH4 / SM53 | logind ignore + polkit deny present; rig reachable |
| `rig-clock-sane` | SM33 | rig UTC within 120s of mini; RTC=UTC; NTP synced |
| `rig-no-crashloop-unit` | SM14 + class | no unit restart-storming (>20 restarts/10min) |
| `rig-ml-window-catchup-clean` | SL10 | `immich-ml-window@on` not left failed |
| `rig-crash-storm-quiet` | SM13 / SM25 / SL9 | no binary segfaults >3×/24h |
| `rig-mdns-fw-quiet` | SM15 / SL12 | avahi conflicts 0, UFW block rate low |
| `rig-btrfs-integrity` | fix-83 | `btrfs device stats /` all-zero (data-corruption tripwire) |

The existing `rig-immich-ml-window` check separately asserts the ML container is
**off by day** (VRAM contention guard, task nas-32).

## btrfs data-checksum corruption (fix-83, 2026-08-23)

The 2026-08-23 sweep (UC4) found rig's root+/home btrfs
(`/dev/nvme2n1p2`, single device, **no mirror**) logging **incrementing**
`corruption_errs`: `corrupt 1` at mount 2026-08-03, `2` on 2026-08-20 (root 257
ino 85429), `3` on 2026-08-23 15:49 (root 256 ino 1626645), and **`5` within the
same audit** — two more csum failures logged after the first scan. Clocks were
cross-checked (rig↔mini within 1s, NTP synced) so the timestamps are real, not
RTC skew. This is the leading edge of the taxonomy-#1 read-only cascade that took
the fleet down in fix-20 (btrfs `corrupt leaf` → forced RO → DB segfaults) — the
FS is still `rw`, so it is the *precursor*, not yet a cascade.

**Root cause is in-flight corruption, not the disk.** The NVMe's own SMART is
clean (Media/Data-Integrity errors 0, 1% wear, no critical warning), so the NAND
is fine — the bad data entered *before* it was written (DRAM / memory-controller /
PCIe / write-path). rig runs **non-ECC** consumer RAM (no `edac` node), and the
corruption correlates with heavy memory pressure from the AI stack. On a
single-device btrfs a csum failure is **unrecoverable** (only `mirror 1` exists),
so each hit is permanent data loss for that block and the counter only climbs.

**What the sweep did (autonomous):**

- Added `rig-btrfs-integrity` (crit) — the counter had **no** monitoring, which is
  why it grew 1→5 unseen. It reads the authoritative kernel counter and fails on
  any non-zero value. It is **RED now** (corruption=5) — correct: the corruption
  is real and unhealed.
- Ran a full `btrfs scrub /` to identify whether the corrupt blocks are still
  referenced (result recorded in the fix-83 commit).

**Operator handoff — the physical/root-cause leg (cannot be done headless):**

1. **memtest86** across a full boot (headless-unreachable — its results only show
   on the console; `memtester` from userspace can only test unallocated RAM and
   won't cover the in-use regions where the AI stack lives). Boot rig into
   memtest86, run ≥2 full passes. If it flags a DIMM, swap it; strongly consider
   **ECC-capable RAM** given this host's write-integrity role.
2. After the RAM is proven good, restore any still-corrupt files from the rig
   restic backup (scrub output names them; on single-device they cannot self-heal)
   and reset the baseline: `sudo btrfs device stats -z /`. `rig-btrfs-integrity`
   goes green and re-fires only on genuinely new corruption.
3. Durable option to weigh: a second NVMe as a btrfs `raid1` data/metadata mirror
   so future csum failures are auto-corrected instead of permanent.
