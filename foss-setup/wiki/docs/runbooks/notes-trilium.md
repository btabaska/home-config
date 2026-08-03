# Trilium (self-hosted notes / knowledge base)

Runbook for the `trilium-web-serves-app` verification check and general operation of the
**Trilium (TriliumNext)** trial — a self-hosted Obsidian-replacement candidate (read-27).
Service page: [trilium](../services/trilium.md).

- **Host:** Mac mini (`192.168.10.2`), Docker, stack `/opt/stacks/trilium` (project `trilium`)
- **URL:** <https://trilium.tabaska.us> (edge-only — no host port; Caddy is the sole listener)
- **Compose:** live `/opt/stacks/trilium/compose.yaml`; repo mirror `foss-setup/configs/docker-stack/stacks/trilium/`
- **Image:** `triliumnext/trilium:v0.104.1` (pinned — **never** `:latest`; minor bumps migrate the SQLite schema)
- **Data:** everything in the single bind mount `./data` → `/home/node/trilium-data` (SQLite `document.db`, `config.ini`, sessions, auto-backups)
- **Auth:** single-user; the login is created in the first-run setup wizard (also encrypts "protected notes") — no secret in env
- **Secrets:** none

## Why Logseq was dropped

The trial originally asked for Logseq *and* Trilium. Logseq was investigated and **dropped**:
its browser/web builds store the graph client-side (File System Access API / browser OPFS),
so there is no shared server-side graph, no login, and the classic web image is ~1 year frozen.
The real self-hosted Logseq path is the **desktop app + Syncthing** on the plain-markdown graph
folder — not a dashboard tile. Trilium, by contrast, is a genuine self-hosted web app.

## First-run setup

Trilium ships uninitialised — on a fresh deploy the app serves a setup page and logs
`DB not initialized, please visit setup page`. Open <https://trilium.tabaska.us>, run the
wizard (choose "start with a fresh document"), and set a username + password. State then
persists in `./data` across restarts.

## Importing an Obsidian vault

Trilium imports a **one-time snapshot**, not a live vault:

1. In Obsidian, right-click the vault → *Show in system explorer*, then **zip the vault folder**
   (Trilium auto-detects an Obsidian vault by its `.obsidian` dir).
2. In Trilium, right-click a note in the tree → **Import into note** → choose the **Obsidian**
   importer → upload the zip.

Preserved: folder hierarchy, attachments, wikilinks → reference links, callouts → admonitions,
inline/block math, code blocks, and frontmatter → promoted attributes (`tags`/`aliases` → labels).
Lossy: comments stripped, Canvas/Bases not imported, and creation dates are set equal to
modification dates. Re-importing later **duplicates** notes rather than merging — import once.

## The consumer check

`trilium-web-serves-app` (in `verification/checks.d/notes.yaml`) is a consumer-end probe, not
liveness: it walks the real path a user hits — DNS (`*.tabaska.us` wildcard) → Caddy TLS
(DNS-01 cert) → the `trilium:8080` upstream with a trusted reverse proxy → the app serving its
shell. It requires HTTP 200 **and** the body to carry the `Trilium` marker (true for both the
setup and login pages). Container liveness + the coverage manifest are covered separately by
`containers-manifest-mini` / `containers-health-mini` in `docker-fleet.yaml`.

Run it in isolation from the mini (audit-safe):

```
ssh mini 'mkdir -p /tmp/nc && cp /opt/verification/checks.d/notes.yaml /tmp/nc/ && \
  VERIFICATION_STATE_DIR=/tmp/ns python3 /opt/verification/bin/checks_runner.py \
  --checks-dir /tmp/nc --no-notify --json; rm -rf /tmp/nc /tmp/ns'
```

## Troubleshooting

- **Crash-loop: `Fatal error during Trilium server startup: TypeError: invalid IP address: true`.**
  This build passes the `trustedReverseProxy` config value straight to Express `trust proxy`,
  which parses a *string* as an IP/CIDR list — so the literal `true` is rejected. The stack sets
  `TRILIUM_NETWORK_TRUSTEDREVERSEPROXY=uniquelocal` (an Express preset trusting private ranges,
  which covers Caddy's IP on the docker `edge` bridge). Use `uniquelocal` or an explicit IP/CIDR,
  never `true`.
- **`DB not initialized, please visit setup page`.** Expected on a fresh deploy — complete the
  first-run wizard (see above).
- **502 through Caddy.** Confirm the container is up and healthy:
  `ssh mini 'cd /opt/stacks/trilium && docker compose ps'`. Trilium ships its own healthcheck
  (`docker_healthcheck.cjs`); a first-boot `starting` → `healthy` transition takes ~30s.
- **Upgrading.** Bump the tag in `compose.yaml` (both repo + live), read the release notes, then
  `docker compose pull && docker compose up -d`. Keep the data dir on the mini's local disk (never
  NFS/CIFS) to avoid SQLite WAL/shm issues.

## Reverting the whole trial

Every byte of Trilium state lives in `/opt/stacks/trilium/data`, and no other service is touched.
Use the one-command teardown (dry-run by default):

```
foss-setup/scripts/notes-trial/teardown-trilium.sh            # dry-run: prints the plan
foss-setup/scripts/notes-trial/teardown-trilium.sh --apply    # tear down live (keeps notes)
foss-setup/scripts/notes-trial/teardown-trilium.sh --apply --purge-data   # also delete notes (after a backup tarball)
```

It removes the container, the Caddy vhost, the Homepage tile, the coverage-manifest line, the
verification check, and the Uptime-Kuma monitor. Then revert the repo side with
`git revert` of the `notes-trial:` commit on both repos and run
`foss-setup/scripts/docs/publish-deploy.sh` + `foss-setup/scripts/docs/build-wiki.sh`
(the script prints the exact commands).
