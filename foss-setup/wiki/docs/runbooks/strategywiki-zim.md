# StrategyWiki ZIM (mwoffliner) — lai-15

Runbook for the `strategywiki-zim-present` verification check and the **StrategyWiki
ZIM** (lai-15, local-ai buildout): scrape [StrategyWiki](https://strategywiki.org)
(CC BY-SA 4.0, MediaWiki 1.41, ~51k articles, no ZIM exists on the Kiwix library) with
**mwoffliner** on the mini and land it in the NAS Kiwix library beside the other offline
ZIMs. Library operation itself: [Kiwix runbook](kiwix.md); AI-side access:
[openzim-mcp runbook](openzim-mcp.md); sibling private build: [gamefaqs-zim](gamefaqs-zim.md).

## STATUS — BLOCKED by Cloudflare (2026-08-06)

**We cannot build this ZIM ourselves right now.** StrategyWiki sits behind **Cloudflare
bot management that fingerprints and 403s mwoffliner's Node/undici HTTP client.** This is
not a rate-limit and not fixable with `--speed` — mwoffliner never gets past its first
API reachability request.

Evidence gathered on the mini (2026-08-06), against
`https://strategywiki.org/w/api.php?action=query&format=json&formatversion=2&maxlag=5`:

| Client | Result |
|---|---|
| `curl` on the mini host — any/empty/browser/mwoffliner User-Agent | **200** |
| `curl` **inside a container** (same docker egress as mwoffliner) | **200** |
| **Node `fetch`** inside the `openzim/mwoffliner` image, bare | **403** (6/6) |
| **Node `fetch`** inside the image, full browser headers | **403** (6/6) |
| Node `fetch` to a **non-Cloudflare** MediaWiki (`minecraft.wiki`) | **200** (control — the client works) |

So it is **not** IP-, UA-, or header-based — Cloudflare is blocking the **TLS/HTTP2
fingerprint** of the Node stack. curl passes; mwoffliner's entire HTTP layer is Node, so
it is a hard block. mwoffliner errors at startup with
`Mediawiki API is not reachable … Request failed with status code 403`.

This is the same expected-block class the fleet already documents for
GameFAQs (Cloudflare Turnstile) and PCGW (Cloudflare-challenged). The pipeline below is
**fully scaffolded and self-detects the block** so that the moment StrategyWiki drops the
Node-fingerprint block (or an official ZIM appears), one command finishes the job.

### Human follow-up (the real path to a StrategyWiki ZIM)

**File the openZIM zim-request** so the openZIM team builds + hosts it officially:
<https://github.com/openzim/zim-requests/issues> — request `strategywiki.org`
(CC BY-SA 4.0, MediaWiki 1.41 open API, ~51k articles, nopic ~1.5GB est). openZIM's own
scraping infrastructure handles wikis behind Cloudflare that our Node client cannot, and
a hosted ZIM is then downloadable via the fleet's normal Kiwix download queue (add its
`.zim` URL to `zim-download-queue.sh`). This is the sanctioned outward-facing action and
is **left to a human on purpose** (it is a public issue on our behalf). Do **not**
attempt to defeat Cloudflare's fingerprinting with a TLS-re-originating proxy — that is
active anti-bot circumvention, brittle, and outside the "polite low-speed scrape" scope.

## Pipeline (mini → NAS → nightly refresh)

All scripts are committed under `foss-setup/scripts/ai/`; the ZIM/data are never in git.
The scrape runs on the **mini** (passwordless docker; the NAS has no docker socket, and
mwoffliner needs Node24+Redis which the official image bundles). The heavy work stays off
the NAS while the ~115G Wikipedia download works the NAS sequential queue.

- **`build-strategywiki-zim.sh`** (mini `/opt/mwoffliner/lai-15/`): the detached,
  nohup-able build. Preflights the Node-client reachability (writes `status=BLOCKED:…`
  and exits cleanly if Cloudflare still blocks), else runs mwoffliner, then hands off to
  the completion handler. Writes a machine-readable `status` file and logs to `build.log`.
- **`strategywiki-zim-handler.sh`** (mini, same dir): after a successful scrape,
  `zimcheck -i -c` (integrity + checksum, via the same `kiwix-tools:3.8.2` image+digest
  the NAS refresh pins), then streams the ZIM to the NAS over `ssh 'cat >'` (SFTP/scp are
  disabled on the NAS) into `/volume1/zim/.incoming/`, md5-verifies, and atomically `mv`s
  it to `/volume1/zim/` as `strategywiki_en_all_nopic_<YYYY-MM>.zim`.
- **Nightly DSM "kiwix library refresh" (05:15)** rebuilds `library.xml` and bounces
  kiwix-serve, wiring the new ZIM into `kiwix.tabaska.us` / NAS `:8092` (and the rig
  openzim-mcp RO mount picks it up). Force it live sooner:
  `printf '%s\n' "$PW" | ssh nas 'sudo -S sh /volume1/docker/kiwix/kiwix-library-refresh.sh'`.

`status` values (read by the verification check): `BUILDING` → `VALIDATING` → `PUSHING` →
`PUSHED_AWAITING_REFRESH:<file>`; or `BLOCKED:<reason>` / `FAILED:<reason>`.

## mwoffliner invocation + rationale

Image is **digest-pinned**: `ghcr.io/openzim/mwoffliner:1.17.5@sha256:5dd08aedd15e2d08dc7ae22b51db097b378c2ce26643c666a363d1ca4dd9e57b`
(latest stable, 2026-08). The image's entrypoint **starts its own redis and injects
`--redis`** — do NOT run a separate redis or pass `--redis` (that errors "Parameter
'--redis' can only be used once").

```sh
docker run --name mw-lai15 --cpus=2 -v /opt/mwoffliner/lai-15/out:/out \
  ghcr.io/openzim/mwoffliner:1.17.5@sha256:5dd08… mwoffliner \
  --mwUrl=https://strategywiki.org/ \
  --adminEmail=btabaska@gmail.com \
  --outputDirectory=/out \
  --format=nopic \
  --speed=0.5 \
  --customZimTags='strategywiki;games;guides' \
  --verbose
```

- **`--speed=0.5`** — polite: half the default parallel-request rate. StrategyWiki is a
  small volunteer-run wiki and this is an async background job — there is no reason to
  hammer it.
- **`--format=nopic`** — text + tables only, no images/video/audio. Strategy guides are
  predominantly prose and tables; screenshots bloat a ZIM 3–5× for marginal reference
  value. Keeps it small (~1.5GB est) and matches the fleet's `wiktionary_en_all_nopic`
  choice. The **fulltext index is KEPT** (we do *not* pass `--withoutZimFullTextIndex`),
  so kiwix `/search` and openzim-mcp work.
- **`--mwUrl` base is enough** — mwoffliner auto-detects the API path (`/w/api.php`) and
  article path (`/wiki/`) from siteinfo; both were confirmed against StrategyWiki's API.
- **`--cpus=2`** so the 49-container, RAM-tight mini is not starved; low speed keeps
  mwoffliner's memory bounded.

## Rebuild / relaunch path

If StrategyWiki ever drops the Node-fingerprint block (retest with the preflight — see
below), just relaunch the detached build; everything downstream is automatic:

```bash
# quick re-test of the block (200 = unblocked, build will proceed):
ssh mini "docker run --rm --entrypoint node \
  ghcr.io/openzim/mwoffliner:1.17.5 -e \
  \"fetch('https://strategywiki.org/w/api.php?action=query&meta=siteinfo&format=json&formatversion=2&maxlag=5').then(r=>console.log(r.status)).catch(()=>console.log('ERR'))\""

# launch (multi-hour, low speed) — the preflight re-checks and self-blocks if still 403:
ssh mini 'cd /opt/mwoffliner/lai-15 && nohup ./build-strategywiki-zim.sh > build.log 2>&1 &'
ssh mini 'tail -f /opt/mwoffliner/lai-15/build.log'   # watch progress
```

The mini `/opt/mwoffliner/lai-15/*.sh` are deploy copies of the repo scripts
(`foss-setup/scripts/ai/build-strategywiki-zim.sh` + `strategywiki-zim-handler.sh`) —
re-push them if the repo versions change.

## The consumer / pipeline check

`strategywiki-zim-present` (in `verification/checks.d/local-ai.yaml`, helper
`/opt/verification/bin/strategywiki-zim.py`, from the mini) is **one probe, two
auto-selected modes**:

1. **CONTENT** — once a `strategywiki_*` book is in the NAS catalog
   (`192.168.10.4:8092`): a real Xapian fulltext search for a known game title
   ("Super Mario Bros", fallback "The Legend of Zelda") + first-article fetch with the
   term in the body. The book base is resolved live from the catalog, so no filename is
   hardcoded.
2. **PIPELINE** — before it lands: reports the mini `status` file. Green while the build
   is healthy (`BUILDING` guarded by mwoffliner-container-alive **or** `build.log`
   freshness < 45 min; `VALIDATING`/`PUSHING`/`PUSHED_AWAITING_REFRESH`) **or** in the
   known **`BLOCKED`** state (green — the Cloudflare block is expected/deferred, not a
   regression; the OK line surfaces the openZIM zim-request follow-up). RED only for a
   genuine `FAILED` or a stalled build.

```bash
# audit-safe, just this check (there is no --check flag; isolate via a temp checks-dir):
ssh mini 'TMPD=$(mktemp -d); python3 -c "import yaml;d=yaml.safe_load(open(\"/opt/verification/checks.d/local-ai.yaml\"));yaml.safe_dump({\"checks\":[c for c in d[\"checks\"] if c[\"id\"]==\"strategywiki-zim-present\"]},open(\"$TMPD/only.yaml\",\"w\"))"; VERIFICATION_STATE_DIR=$(mktemp -d) /opt/verification/bin/run-checks.sh --no-notify --checks-dir "$TMPD"; rm -rf "$TMPD"'
```

## Common failures

| Symptom | Cause / fix |
|---|---|
| `mode=blocked BLOCKED:cloudflare_node_tls_fingerprint_403` | **Current expected state.** Cloudflare still fingerprint-blocks mwoffliner's Node client. Nothing to fix locally; file/await the openZIM zim-request. Re-test with the preflight one-liner above. |
| mwoffliner exits `Parameter '--redis' can only be used once` | You passed `--redis` and/or ran a separate redis — the image bundles redis and injects the flag. Use the single-container invocation above. |
| mwoffliner exits `Mediawiki API is not reachable … 403` | The Cloudflare block (see Status). `--speed` won't help — it fails on request #1. |
| `mode=failed FAILED:zimcheck` | The produced ZIM failed integrity/checksum — rebuild; don't push a corrupt ZIM. |
| `mode=failed FAILED:nas_push` / `md5_mismatch` | ssh stream to the NAS failed or corrupted — the handler removes the partial from `.incoming/`; re-run the handler. |
| `mode=building STALLED` | mwoffliner container gone + `build.log` stale while `status=BUILDING` — the wrapper died mid-scrape; check `build.log`, relaunch. |
| Book on NAS but check still `mode=pipeline` | No hot-add — run the kiwix library refresh (see Kiwix runbook); confirm the file is in `/volume1/zim`, not `.incoming/`. |
