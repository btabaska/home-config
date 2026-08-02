# navidrome-scan — mount-gated Navidrome scan trigger (fix-49)

Resolves **fix-49 / SC1** (2026-08-02 fleet sweep). On 2026-08-01 Navidrome's
built-in hourly QUICK scan observed the read-only CIFS music root
(`/mnt/nas/music`, a `soft` mount) as momentarily **empty** and flagged all
3495 tracks `missing=1` — a 30-hour whole-library grey-out — while the container
stayed `healthy` and `https://music.tabaska.us/ping` returned 200. Quick scans
can never clear a `missing` flag, so it did not self-heal.

## The fix

1. **Root cause of the skip** (separate, in `scripts/nas/`): the music-root
   `.ndignore` held the bare line `#recycle`, a gitignore **comment** → zero
   patterns → an *empty* `.ndignore` → Navidrome skips that whole folder. At the
   library root that greys out everything. Corrected to the escaped literal
   `\#recycle` in both `ensure-navidrome-music-ignore.sh` and
   `empty-recycle-30d.sh` (and on the live NAS file).
2. **Mount-gate the scanner** (this directory): Navidrome's built-in periodic
   scanner is **disabled** (`ND_SCANNER_SCHEDULE: "0"` in the compose). Scanning
   is driven instead by `navidrome-scan.timer` (every 15 min) →
   `navidrome-scan-gate.sh`, which:
   - **refuses to scan** unless the CIFS root is actually populated
     (`>= MIN_ROOT_ENTRIES`, default 10; the library has ~46 top-level dirs) —
     so a transient empty read can no longer reach the scanner (`GATE_SKIP`);
   - triggers a normal **quick** scan when healthy (Subsonic `startScan`, run
     inside the Navidrome server process = single sqlite writer — never a second
     `navidrome scan` process, which would contend with the live DB);
   - triggers a **full** scan to *self-heal* if it ever finds the library
     already mass-flagged missing (`missing*2 >= total`) while the mount is
     healthy — recovery that used to require a human, now automatic within 15m.

## Provenance / deploy (NOT ansible-managed)

Like `lidarr-reconcile`, `tv-cleanup`, `net-selfheal`, and `static-ip`, these are
**host** units on the mini deployed by hand (the ansible roles are base/docker/
tailscale/backup/state only). This directory is the canonical source; keep it and
the live host in sync.

| repo file | live path | owner / mode |
|-----------|-----------|--------------|
| `navidrome-scan-gate.sh`   | `/usr/local/sbin/navidrome-scan-gate.sh`        | `root:root 0755` |
| `navidrome-scan.service`   | `/etc/systemd/system/navidrome-scan.service`    | `root:root 0644` |
| `navidrome-scan.timer`     | `/etc/systemd/system/navidrome-scan.timer`      | `root:root 0644` |
| `navidrome-scan.env.example` → filled | `/etc/navidrome-scan.env`            | `root:root 0600` |

```sh
sudo install -m0755 navidrome-scan-gate.sh /usr/local/sbin/
sudo install -m0644 navidrome-scan.{service,timer} /etc/systemd/system/
# fill NAVIDROME_USER/TOKEN/SALT from the vault (see navidrome-scan.env.example), then:
sudo install -m0600 -o root -g root <filled-env> /etc/navidrome-scan.env
sudo systemctl daemon-reload
sudo systemctl enable --now navidrome-scan.timer
```

The admin Subsonic token is the same pair the Homepage widget uses
(vault `navidrome.username`, `homepage_widgets.navidrome_token`,
`homepage_widgets.navidrome_salt`).

## Monitoring

- `navidrome-library-present` (checks.d/media-library-correctness.yaml, **crit**) —
  the exact regression pager: any mass-flag (`missing` > 20% of the library)
  pages. This check already *caught* the 2026-08-01 outage but sat at `warn`, so
  it never paged; bumped to crit.
- `navidrome-scan-integrity` (**crit**) — the class probe: the `.ndignore`
  carries a real (non-comment/non-blank) pattern, the library is non-empty and
  not mass-missing, and the library-root folder row is present + not missing.
- `navidrome-scan-fresh` (**warn**) — dead-man for this timer: Navidrome's
  `last_scan_at` must stay `< 45m` (timer fires every 15m). Catches a silently
  stopped gate (new music would otherwise stop appearing).
- `OnFailure=ntfy-notify@%n.service` — alerts on a hard gate failure.

A `GATE_SKIP empty-or-short` line in `journalctl -u navidrome-scan.service` means
the CIFS root read empty — that is a **mount/NAS** problem to fix at the mount
layer; do **not** "fix" it by re-enabling Navidrome's built-in scanner (that is
what caused SC1).
