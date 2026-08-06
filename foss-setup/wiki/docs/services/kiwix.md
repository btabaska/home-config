# kiwix

Kiwix — offline ZIM knowledge library (lai-12, local-ai buildout)

| | |
|---|---|
| **Host** | [nas](../hosts/nas.md) |
| **URL** | https://kiwix.tabaska.us |
| **Source** | `foss-setup/configs/nas/kiwix/docker-compose.yml` |
| **Notes** | Offline ZIM knowledge library (lai-12, local-ai buildout) — kiwix-serve 3.8.2 (tag@digest pinned) on the NAS serving the curated ~150GB set (devdocs picks, iFixit, sysadmin StackExchange, wiktionary en, game wikis, Wikipedia en maxi) from /volume1/zim. Host :8092 -> container :8080 (NAS :8080 is Scrutiny). library.xml rebuilt by kiwix-manage via DSM task 18 nightly 05:15 ONLY when the ZIM set changed (kiwix-serve cannot hot-add ZIMs); downloads land atomically via the sequential queue script. Feeds openzim-mcp (lai-13). Consumer check kiwix-search-consumer. |
| **Upstream docs** | <https://kiwix.tabaska.us> · <https://kiwix.org> · <https://github.com/kiwix/kiwix-tools> |

## About

Kiwix is the fleet's offline knowledge library (lai-12, local-ai buildout) — `kiwix-serve` on the NAS serving the curated ~150GB ZIM set out of `/volume1/zim` (10T+ free at build): ~20 `devdocs_en_*` per-docset picks matching the fleet's stack (docker, python, bash, postgres, nginx, ansible, ...), iFixit, the sysadmin StackExchange set (serverfault, superuser, unix, askubuntu, raspberrypi), Wiktionary en, game wikis (Minecraft, Terraria, Bulbagarden, Stardew, Dwarf Fortress) and — largest by far — Wikipedia en maxi (~115G). NO wikiHow: it was pulled from the Kiwix library in Jan 2025, permanently. The stack lives at `/volume1/docker/kiwix/` (repo mirror `foss-setup/configs/nas/kiwix/`): `ghcr.io/kiwix/kiwix-serve:3.8.2` (tag@digest pinned, non-root `1026:100`), host `:8092` -> container `:8080` (NAS `:8080` is Scrutiny, `:8090` was taken), browsers via the mini Caddy at https://kiwix.tabaska.us. The load-bearing quirk: **kiwix-serve cannot hot-add ZIM files.** The container serves `--library /library/library.xml` (+`--monitorLibrary`), and `kiwix-library-refresh.sh` (root, DSM Task Scheduler job 18, nightly 05:15 — a `.task` file, NEVER raw crontab on DSM) rebuilds that XML with `kiwix-manage` from the `ghcr.io/kiwix/kiwix-tools` sibling image and restarts the container ONLY when the set of `*.zim` files actually changed. Downloads arrive via `zim-download-queue.sh` — strictly SEQUENTIAL (one `wget -c` at a time, `nice -19`; NAS-parallel I/O causes fleet-wide observer effects), resumable, into `/volume1/zim/.incoming/` with an atomic `mv` on completion so the library never indexes a partial file. ZIMs carry their own Xapian full-text index — that is why the AI stack integrates via openzim-mcp (lai-13) rather than re-embedding 100GB into Open WebUI Knowledge. Consumer check: `kiwix-search-consumer` (search + article fetch, not liveness).

## Containers

| Service | Image (pinned) | Ports |
|---|---|---|
| `kiwix` | `ghcr.io/kiwix/kiwix-serve:3.8.2@sha256:57baa553c46cd30770905df15a9a687258aa5471c30c8edaefe278f1784e1aa8` | `8092:8080` |

## Volumes

| Service | Volume |
|---|---|
| `kiwix` | `/volume1/zim:/data:ro` |
| `kiwix` | `/volume1/docker/kiwix/library:/library:ro` |

## Troubleshooting

- **A ZIM finished downloading but its book never appears in the web UI (library count stuck).** — kiwix-serve cannot hot-add ZIMs — the book list comes from `/volume1/docker/kiwix/library/library.xml`. Run the refresh as root: `sudo sh /volume1/docker/kiwix/kiwix-library-refresh.sh` (it no-ops unless the `*.zim` set changed — check `/volume1/docker/kiwix/logs/library-refresh.log`). If the nightly never fires, confirm DSM task 18 exists (`ls /usr/syno/etc/synoschedule.d/root/18.task`) and reinstall with `foss-setup/scripts/nas/install-kiwix-refresh-task.sh`. Also confirm the file really lives in `/volume1/zim/` — anything still in `.incoming/` is an unfinished download and is deliberately invisible.
- **Search returns nothing (or a book 404s) while the main page lists it fine.** — Either the ZIM landed corrupt (interrupted download that got moved by hand — the queue script's atomic mv exists precisely so this cannot happen; re-download it) or library.xml points at a file that was renamed/deleted under it. Rebuild: `rm /volume1/docker/kiwix/library/.zims.state && sudo sh /volume1/docker/kiwix/kiwix-library-refresh.sh` (forces a full kiwix-manage re-index + container restart). `docker logs kiwix` prints per-book load errors on start.
- **The big downloads (Wikipedia maxi) stalled or the queue died mid-file.** — The queue is resumable by design: re-run `nohup sh /volume1/docker/kiwix/zim-download-queue.sh >/dev/null 2>&1 &` as btabaska — completed files are skipped, partials in `.incoming/` continue via `wget -c`. Progress: `tail /volume1/docker/kiwix/logs/zim-download.log`. It refuses to start a new file under 200G free on /volume1 (space guard). Keep it ONE queue at a time — parallel NAS downloads are the observer-effect hazard the sequential rule exists for.
- **https://kiwix.tabaska.us is down but `curl http://192.168.10.4:8092` works.** — Edge-side, not Kiwix: the mini Caddy vhost (`kiwix.{$DOMAIN}` -> `{$NAS_IP}:8092` in `/opt/stacks/caddy/caddy/Caddyfile`) — validate + reload with `docker exec caddy caddy validate --config /etc/caddy/Caddyfile && docker exec caddy caddy reload --config /etc/caddy/Caddyfile`. See the reverse-proxy runbook.

## Operations

```bash
# NAS stack — manage via DSM Container Manager (project: kiwix)
# or over SSH (sudo required): cd /volume1/docker/kiwix && sudo docker compose ps
```

Update procedure: [Runbooks → Update images](../runbooks/update-images.md). Full add/change loop: [Runbooks → Add a service](../runbooks/add-a-service.md).

*Generated by `scripts/docs/gen-wiki-services.py` — do not edit by hand; edit the compose file and regenerate.*
