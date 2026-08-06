# Kiwix (offline ZIM knowledge library)

Runbook for the `kiwix-search-consumer` verification check and general operation of
**Kiwix** — the fleet's offline knowledge library (lai-12, local-ai buildout).
Service page: [kiwix](../services/kiwix.md).

- **Host:** NAS (Synology DS920+, `192.168.10.4`), Docker, stack `/volume1/docker/kiwix`
- **URLs:** <https://kiwix.tabaska.us> (humans, via mini Caddy) · `http://192.168.10.4:8092` (LAN consumers — openzim-mcp lai-13, verification)
- **Compose:** live `/volume1/docker/kiwix/docker-compose.yml`; repo mirror `foss-setup/configs/nas/kiwix/`
- **Image:** `ghcr.io/kiwix/kiwix-serve:3.8.2` (tag@digest pinned; the refresh script pins the matching `kiwix-tools` image — keep both on the same release train)
- **Port:** host `:8092` → container `:8080` (NAS `:8080` is Scrutiny, `:8090` was taken)
- **Library:** ZIM files in `/volume1/zim` (on /volume1 — 10T+ free at build); `library.xml` in `/volume1/docker/kiwix/library/`
- **Secrets:** none — read-only public content, LAN/tailnet-only

## The load-bearing quirk: no hot-add

`kiwix-serve` **cannot pick up new ZIM files by itself.** The container serves
`--library /library/library.xml` (plus `--monitorLibrary`, which re-reads the XML when
it changes), and that XML is owned by `kiwix-library-refresh.sh`:

- **DSM Task Scheduler job 18** — "kiwix library refresh (lai-12)", nightly **05:15**
  as root. A `.task` file in `/usr/syno/etc/synoschedule.d/root/` (installer:
  `foss-setup/scripts/nas/install-kiwix-refresh-task.sh`) — **never** raw crontab
  lines on DSM, crond regenerates `/etc/crontab` from the `.task` files.
- It diffs the current `*.zim` set against `library/.zims.state`; when unchanged it
  exits silently. When changed it rebuilds `library.new.xml` with `kiwix-manage`
  (one `kiwix-tools` container run, uid 1026), atomically swaps it in, and restarts
  the `kiwix` container. Log: `/volume1/docker/kiwix/logs/library-refresh.log`.
- Manual run after dropping in a ZIM:
  `sudo sh /volume1/docker/kiwix/kiwix-library-refresh.sh`
- Force a full rebuild (paranoia / corrupt XML):
  `rm /volume1/docker/kiwix/library/.zims.state` then run it again.

## Downloads: the sequential queue

`zim-download-queue.sh` (as **btabaska**, no sudo) works through a pinned-filename
queue **one file at a time** (`nice -19 wget -c`) — the NAS observer-effect rule:
parallel heavy I/O on this box distorts the rest of the fleet. Details that matter:

- Fetches into `/volume1/zim/.incoming/`, atomic `mv` up on success — the refresh
  script can never index a partial file.
- Idempotent + resumable: completed files are skipped, partials continue (`wget -c`).
  After any interruption just re-run:
  `nohup sh /volume1/docker/kiwix/zim-download-queue.sh >/dev/null 2>&1 &`
- Space guard: refuses to start a file with `<200G` free on /volume1.
- Queue order: devdocs picks → iFixit → sysadmin StackExchange → Wiktionary →
  game wikis → **Wikipedia en maxi last** (~115G).
- Progress: `tail -f /volume1/docker/kiwix/logs/zim-download.log`
- Content updates later = edit the pinned filenames in the queue script (both repo
  and live copies), re-run it, let the nightly refresh wire the books in, then
  delete the superseded `.zim` files by hand.
- **No wikiHow** — pulled from the Kiwix library Jan 2025, permanently gone.

## The consumer check

`kiwix-search-consumer` (in `verification/checks.d/local-ai.yaml`) probes the
consumer path, not liveness, from the mini against `192.168.10.4:8092`:

1. **Library breadth** — the OPDS catalog (`/catalog/v2/entries?count=-1`) must list
   **≥ 10 books** (bare `kiwix-serve` with an empty/half-empty library is exactly the
   green-but-broken mode this catches).
2. **Search** — a real Xapian query (`/search?books.name=...&pattern=...`) against a
   book that is guaranteed present (devdocs docker, from the first queue tranche)
   must return result links.
3. **Fetch** — it follows the first result link and requires the search term in the
   article body — proving content serving, not just the index.

The check is deliberately robust to the library still growing: it only probes books
from the first (tiny) download tranche and a floor count, so Wikipedia/wiktionary
still trickling in keeps it green. Run it in isolation from the mini (audit-safe):

```bash
VERIFICATION_STATE_DIR=$(mktemp -d) /opt/verification/bin/run-checks.sh --no-notify --check kiwix-search-consumer
```

## Common failures

| Symptom | Cause / fix |
|---|---|
| Book downloaded but not listed | No hot-add — run the refresh script (see above); check the file is in `/volume1/zim`, not `.incoming/` |
| Search 404 / empty for one book | Corrupt or renamed ZIM under library.xml — force a full rebuild; `docker logs kiwix` prints per-book load errors |
| Queue stalled | Re-run the queue script (resumable); check the space guard didn't trip (log line "ABORT") |
| Caddy URL down, `:8092` fine | Mini edge issue — validate+reload Caddy (`kiwix.{$DOMAIN}` vhost); see the reverse-proxy runbook |
| Whole UI slow during big downloads | Expected while the 115G Wikipedia fetch runs (sequential + niced, but still real I/O); it clears when the queue finishes |

## Upgrade

Bump tag+digest in `docker-compose.yml` **and** the `TOOLS_IMG` pin inside
`kiwix-library-refresh.sh` (same release), mirror both to
`foss-setup/configs/nas/kiwix/`, then:

```bash
ssh -t nas 'cd /volume1/docker/kiwix && sudo /usr/local/bin/docker compose pull && sudo /usr/local/bin/docker compose up -d'
```
