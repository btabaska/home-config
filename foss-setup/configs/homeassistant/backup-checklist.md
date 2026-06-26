# Home Assistant Backups + Encryption Key — Checklist

Backups are worthless if you can't decrypt them. HA backups are **encrypted** by
default; restoring an encrypted backup requires the **backup encryption key** (the
"emergency kit"). **Nabu Casa does NOT store your key and cannot recover it.** If the
key is lost and you've lost access to the instance, the backup is permanently
unreadable. So: store the key in your password manager, day one.

Authoritative docs:
- Backups & restore: https://www.home-assistant.io/common-tasks/general/#backups
- Backup emergency kit: https://www.home-assistant.io/more-info/backup-emergency-kit/
- Backup integration: https://www.home-assistant.io/integrations/backup/
- Encryption modernization (SecureTar v3, 2026.4): https://www.home-assistant.io/blog/2026/03/26/modernizing-encryption-of-home-assistant-backups/

---

## One-time setup

- [ ] Update HA to the latest version first (2026.4+ uses the stronger **SecureTar v3**
      backup format).
- [ ] Settings → System → **Backups** → **Set up backups**.
- [ ] During setup, **download the backup emergency kit** (contains the encryption key).
- [ ] **Save the encryption key in your password manager** (e.g. an entry named
      "Home Assistant backup encryption key"). Also keep a copy of the emergency kit
      file in the password manager's secure file storage or another offline vault.
      **Store it OUTSIDE the HA system** — a key sitting only on HA is no help if HA dies.
- [ ] Choose what to back up (full = HAOS + add-ons + config + database) and a schedule
      (e.g. daily, keep 7).

## Send backups to the NAS (off-box)

- [ ] Add an off-box backup location so a copy lives on the NAS, not just on HA:
      - Easiest: install the **Samba Backup** add-on, OR configure a network storage /
        backup agent that targets a NAS SMB/NFS share.
      - Network storage: Settings → System → Storage → **Add network storage**, then
        select it as a backup location.
- [ ] Verify a backup file actually lands on the NAS share after the first run.

## Where the encryption key goes (summary)

| Item | Location |
|------|----------|
| Encryption key (string) | **Password manager** entry |
| Emergency kit file | Password manager secure file / encrypted vault, off-box |
| Backup `.tar` archives | **NAS** share (+ HA local copy) |
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

- [ ] Confirm scheduled backups are running (Backups page shows recent dates).
- [ ] Periodically confirm copies are reaching the NAS.
- [ ] After major changes (new integrations, Nest/Midea tokens), take a manual backup —
      AND separately back up `/config/.storage/midea_ac_lan/*.json` (see
      midea-local-setup.md), since those tokens are irreplaceable.
