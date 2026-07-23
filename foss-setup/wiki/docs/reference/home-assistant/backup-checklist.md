# HA backup checklist

> Backup + encryption-key discipline for HA Green — what's deployed live, and the procedure to reproduce or restore it.
_Source: `foss-setup/configs/homeassistant/backup-checklist.md` · migrated + validated 2026-07-14._

Backups are worthless if you can't decrypt them. HA backups are **encrypted** by
default; restoring an encrypted backup requires the **backup encryption key** (the
"emergency kit"). **Nabu Casa does NOT store your key and cannot recover it.** If the
key is lost and you've lost access to the instance, the backup is permanently
unreadable. So: store the key in your password manager, day one.

Authoritative upstream docs:

- Backups & restore: https://www.home-assistant.io/common-tasks/general/#backups
- Backup emergency kit: https://www.home-assistant.io/more-info/backup-emergency-kit/
- Backup integration: https://www.home-assistant.io/integrations/backup/
- Encryption modernization (SecureTar v3, 2026.4): https://www.home-assistant.io/blog/2026/03/26/modernizing-encryption-of-home-assistant-backups/

---

## Live state (validated 2026-07-14)

Backups on HA Green (`192.168.10.50`, running core **2026.6.4** — above 2026.4, so
the stronger **SecureTar v3** format is in use) are **deployed and running**, not
aspirational. Verified live via the HA WebSocket backup API and by listing the
archive on the NAS:

| Setting | Live value |
|---|---|
| Automatic backups | **Configured**, daily at **04:45** |
| Backup agents | `hassio.local` (on-appliance eMMC) **and** `hassio.nas_backups` (off-eMMC) |
| Encryption | **On** — key in vault `hosts.ha.backup_password` (also Proton Pass) |
| Contents | Full: config + database + all add-ons |
| Retention | **3** copies per agent |
| Off-eMMC target | Supervisor CIFS mount `nas_backups` → `//192.168.10.4/backups` |
| Last confirmed | `Automatic_backup_2026.6.4_2026-07-14_04.45_*.tar` landed encrypted on the NAS |

The off-eMMC path uses a **dedicated least-privilege Synology SMB user `ha-backup`**
(creds in the gitignored vault). A crit dead-man check `ha-backup-offsite-fresh`
enforces that the newest `.tar` in `/volume1/backups` on the NAS is < 48h old — an
empty/stale NAS location fails loudly rather than passing vacuously.

!!! warning "The key is the backup"
    The archives are useless without `hosts.ha.backup_password`. It must live
    OUTSIDE HA (vault + Proton Pass) — a key sitting only on HA is no help if HA dies.

---

## One-time setup (procedure of record)

- [ ] Update HA to the latest version first (2026.4+ uses the stronger **SecureTar v3**
      backup format; the live instance is 2026.6.4).
- [ ] Settings → System → **Backups** → **Set up backups**.
- [ ] During setup, **download the backup emergency kit** (contains the encryption key).
- [ ] **Save the encryption key in your password manager** (e.g. an entry named
      "Home Assistant backup encryption key"). Also keep a copy of the emergency kit
      file in the password manager's secure file storage or another offline vault.
      **Store it OUTSIDE the HA system.**
- [ ] Choose what to back up (full = HAOS + add-ons + config + database) and a schedule
      (live: daily, keep 3).

## Send backups to the NAS (off-box)

The live deployment does this via a **Supervisor CIFS mount** targeting the NAS SMB
share, with a dedicated least-priv SMB user — a copy lives on the NAS, not just on HA:

- [ ] Add an off-box backup location. Options:
      - Configure a **network storage / backup agent** targeting a NAS SMB/NFS share
        (this is the deployed approach: mount `nas_backups` → `//192.168.10.4/backups`,
        giving backup agent `hassio.nas_backups`), OR
      - install the **Samba Backup** add-on.
      - Network storage UI: Settings → System → Storage → **Add network storage**, then
        select it as a backup location.
- [ ] Verify a backup file actually lands on the NAS share after the first run
      (verified: encrypted `.tar` present in `/volume1/backups`).

## Where the encryption key goes (summary)

| Item | Location |
|------|----------|
| Encryption key (string) | **Password manager** + vault `hosts.ha.backup_password` |
| Emergency kit file | Password manager secure file / encrypted vault, off-box |
| Backup `.tar` archives | **NAS** share (+ HA local eMMC copy) |
| 2nd copy of key | Optional: printed, in a safe |

## If you rotate the key

- [ ] You can regenerate via Settings → System → Backups → **Change encryption key**.
- [ ] **Old backups still need the OLD key.** Keep every key you've used, labeled with
      dates, in the password manager. A new key does NOT decrypt older archives.

## Verify the restore path (do this once, before you need it)

- [ ] Note your owner login credentials (also irrecoverable if lost).
- [ ] Test-restore: on a spare VM / fresh HAOS, during onboarding choose **Restore from
      backup**, supply the backup file + the encryption key from the kit, confirm it
      restores. Don't refresh the page mid-restore.
- [ ] Green/Yellow restore docs:
      - Green: https://support.nabucasa.com/hc/articles/25160431579165
      - Onboarding restore: https://www.home-assistant.io/getting-started/onboarding/

## Recurring

- [ ] Confirm scheduled backups are running (Backups page shows recent dates; live
      next run 04:45 daily).
- [ ] Periodically confirm copies are reaching the NAS (the `ha-backup-offsite-fresh`
      dead-man check does this automatically: crit if no NAS `.tar` < 48h old).
- [ ] After major changes (new integrations, Nest/Midea tokens), take a manual backup —
      AND separately back up `/config/.storage/midea_ac_lan/*.json` (see
      `foss-setup/configs/homeassistant/midea-local-setup.md`) once Midea is added,
      since those tokens are irreplaceable. (Midea is currently HACS-blocked and not
      yet integrated.)

---
[← Home Assistant reference](index.md)
