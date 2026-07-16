# Runbook — rig root btrfs read-only / metadata corruption recovery

**Applies to:** `rig` (CachyOS, 192.168.10.12). **Class:** OS-disk metadata corruption on the
marginal OS NVMe. **First occurrence:** 2026-07-15 22:49 EDT (audit findings C1/C2/C3, task `fix-20`).

## What this looks like

The whole cascade is downstream of **one** condition: the root btrfs remounted **read-only**.
Symptoms, in the order they surface:

- `restic-backup.service`, `ansible-pull.service`, `logrotate.service`, `plocate-updatedb.service`
  all **fail** (they cannot write). `systemd-failed-rig` fires.
- `palworld` REST `:8212` goes dead and the container flips `unhealthy` (can't write saves).
- `litellm-db` (Postgres) **segfaults** (exit 139) on a failed WAL write; LiteLLM then returns
  `503 no_db_connection` to every **virtual-key** client — while master-key `/health/liveliness`
  and `rig-ai-e2e` keep returning **200**, so dashboards look green.
- `open-webui` serves reads (200) but every **write** fails; mini `wiki-rag-sync.service` fails 500.
- **The trap:** `docker ps` keeps reporting dead containers as `Up (healthy)` because the daemon
  can't persist state to the read-only disk. Trust `docker inspect`, never `docker ps`, during this.

## The tell that cuts through all of it

```
ssh rig 'findmnt -no OPTIONS / | cut -d, -f1'      # -> ro  means you are in this incident
ssh rig 'touch /home/btabaska/.probe && rm /home/btabaska/.probe && echo RW || echo RO'
```

This is exactly what the **`rig-root-fs-writable`** check (verification, fast tier, crit) probes —
a real write, not a liveness ping. `mini-root-fs-writable` is the same guard for the mini.

## Root cause

The OS NVMe — **WD SN570 2TB, `WDS200T3X0C-00SJG0`, serial `210318800752`, at PCIe `0000:74:00.0`** —
has a **marginal PCIe link** (long-standing known issue). A metadata write is corrupted **in flight**
(bad data written under a *valid* checksum, so `btrfs device stats` shows **0** corruption errors),
producing a stale/torn leaf:

```
BTRFS critical (device nvme…p2): corrupt leaf … invalid tree level, have 177620385792 expect [0,7]
btrfs check --readonly:  parent transid verify failed on <block> wanted 16495 found 16087
```

i.e. the parent points at generation 16495 but the leaf on disk still holds 16087 — a **lost write**.
btrfs sets the fs error state and refuses to remount rw (`remounting read-write after error is not
allowed`). It re-hits the bad leaf on every subsequent mount, so **a plain reboot does NOT fix it** —
the machine boots into **emergency mode** (root mounts `ro`).

## Recovery procedure

The root fs cannot be repaired while mounted, and root cannot be unmounted live — so the repair is
**offline, from a USB boot**. Order matters: salvage first (nothing after the last restic run is
backed up), heal the link, then repair.

### 1. Salvage the un-backed-up deltas (while the fs is still readable `ro`)

From another host, pull the data that restic does **not** cover (see the backup-scope note below).
SFTP/scp to the NAS is disabled and the rig may not have working outbound ssh keys under `ro`, so
stream over a raw TCP pipe:

```
# on mini: receive
tmux new -d -s salvage 'nc -lvnp 9998 > ~/rig-salvage/rig-salvage.tar.gz'
# on rig (root): send worlds/saves + docker volumes + /etc, skip re-downloadable game bulk
cd / && tar czf - --ignore-failed-read \
  --exclude='*.jar' --exclude='*/libraries' --exclude='*/versions' --exclude='*/steamapps' \
  opt/stacks/palworld/game/Pal/Saved opt/stacks/palworld/game/backups \
  opt/stacks/amp/config/.ampdata var/lib/docker/volumes/docker_litellm_pgdata \
  var/lib/docker/volumes/docker_open_webui_data etc | socat -u - TCP:192.168.10.2:9998
# verify on mini: gzip -t rig-salvage.tar.gz && tar tzf rig-salvage.tar.gz | wc -l
```

### 2. Reseat the marginal NVMe (heals the link before repair writes)

Power off (hold the power button — `systemctl` loops back to emergency mode). Reseat the WD 2TB
NVMe, ideally into a **different M.2 slot** to rule out the slot. This is the durable fix for the
*cause*; the btrfs repair only fixes the *damage*.

### 3. Offline btrfs repair from a Linux USB

Boot any Linux live USB with `btrfs-progs` (Arch/CachyOS). Select the fs **by UUID** — the `nvmeN`
number changes across reboots/reseats:

```
UUID=e4b84b06-355f-4d67-8d41-05a152472392    # the rig root btrfs (partition …p2)
umount /dev/disk/by-uuid/$UUID 2>/dev/null
btrfs check --readonly /dev/disk/by-uuid/$UUID | tee /tmp/pre.txt     # assess (expect the transid error)
btrfs check --repair   /dev/disk/by-uuid/$UUID | tee /tmp/repair.txt  # fix
btrfs check --readonly /dev/disk/by-uuid/$UUID | tee /tmp/post.txt    # MUST be clean
```

- **`post.txt` clean** → remove USB, boot into CachyOS (root now mounts **rw**), go to step 4.
- **`--repair` cannot fix it** → do **not** loop `--repair`. Restore from the last pre-corruption
  restic snapshot / reinstall (you have the step-1 salvage). See `backup-restore.md`.

### 4. Bring services back and re-verify (consumer-level, not liveness)

```
ssh rig 'findmnt -no OPTIONS / | cut -d, -f1'            # rw
ssh rig 'sudo systemctl start docker && docker compose --project-directory /opt/stacks/palworld up -d'
# litellm-db segfaulted mid-write — check Postgres came up clean; restore the volume from salvage if not
ssh rig 'docker inspect -f "{{.State.Running}} {{.State.ExitCode}}" litellm-db palworld'
ssh rig 'sudo systemctl start restic-backup.service'     # closes the backup gap (H23/H27)
```

Then confirm the fix-20 checks are green: `rig-root-fs-writable`, `rig-litellm-vkey-e2e`,
`systemd-failed-rig`, `containers-manifest-rig`, `palworld-rest-liveness`, `restic-snapshot-fresh-rig`.

## Prevention now in place

- **`rig-root-fs-writable`** + **`mini-root-fs-writable`** (fast tier, crit): real write probes —
  a silent read-only remount pages in ~10 min instead of the ~12h it took here.
- **`rig-litellm-vkey-e2e`**: exercises the DB-backed (virtual-key) auth path, so a dead litellm-db
  is caught even though master-key liveness stays 200.
- **Backup scope** (`scripts/backup/excludes-rig.txt`, rig `/etc/restic/env` `BACKUP_PATHS`): now
  covers the Palworld + AMP worlds **and** the `litellm-db` / `open-webui` docker volumes, so a
  disk loss no longer loses game/AI state. Re-downloadable game binaries stay excluded.

## Standing hardware item

The marginal PCIe link is the recurring cause. Reseat addresses it short-term; **replace the SN570
`210318800752`** if corruption recurs after a reseat. Tracked in memory `rig-nvme-pcie-link`.
