# GameFAQs text corpus (PRIVATE ZIM)

Runbook for the `gamefaqs-zim-search` verification check and the **private GameFAQs
text ZIM** (lai-14, local-ai buildout) — the ~2.2 GB Internet Archive full-text FAQ
corpus packaged as a libzim ZIM with real Xapian fulltext search, served from the NAS
Kiwix library alongside the other offline knowledge ZIMs. Library operation itself:
[Kiwix runbook](kiwix.md); AI-side access: [openzim-mcp runbook](openzim-mcp.md).

## PRIVACY — read this first

GameFAQs guides carry **per-author copyright**. This ZIM exists for **personal,
LAN-only reference** inside the homelab. **Never redistribute it, upload it, seed it,
or expose it on the public Internet.** The constraint is enforced/annotated in several
places on purpose:

- ZIM metadata: `Name=gamefaqs_en_private`, `Publisher=… DO NOT REDISTRIBUTE`,
  `Tags=…;private;no-redistribute`, `Description` repeats the never-redistribute rule.
- Every wrapped FAQ page prints the line *"PRIVATE archive copy — per-author
  copyright; never redistribute or expose publicly."* (the `gamefaqs-zim-search` check
  asserts this string is present in served article bodies — a wrong/public ZIM landing
  under this Name FAILs the check).
- **Serving posture is LAN/tailnet-only** (see below) — that is what makes hosting a
  private-copyright ZIM acceptable here.

**Do NOT crawl the live GameFAQs site.** The whole site (incl. `?print=1`) sits behind
Cloudflare Turnstile — automated fetches get a 403. The only sanctioned source is the
IA snapshot below.

## Serving posture (why LAN-only matters)

The Kiwix library is **LAN/tailnet only, nothing port-forwarded outward** — verified for
lai-14 before adding the private ZIM:

- `kiwix.tabaska.us` resolves to the mini's **LAN IP `192.168.10.2`** on the internal
  resolver and does **not** resolve on public DNS (`1.1.1.1`/`8.8.8.8` return nothing) —
  the `tabaska.us` zone is Cloudflare-delegated for DNS-01 certs only, no public A record.
- The mini Caddy vhost (`configs/docker-stack/stacks/caddy/caddy/Caddyfile`,
  "Kiwix" block) just reverse-proxies `{$NAS_IP}:8092` behind `local_tls`; there is no
  external listener and no router port-forward to it.
- kiwix-serve binds NAS host `:8092` on the LAN only.

Because serving is LAN-only, the private ZIM joins the **existing** `/volume1/zim`
library (no separate dir needed) — but it is clearly marked private via its metadata and
this runbook. If the Kiwix library is ever exposed to the Internet, this ZIM must be
pulled out of it first.

## Source & pipeline

- **Source:** Internet Archive item **`Gamespot_Gamefaqs_TXTs`**
  ("Gamespot TXT GameFAQs - Full Archive (3/23/20)", uploader prograc) — 9 solid `7z`
  archives (`gamefaqs.gamespot.com.txt.faqs.{1..9}.gen.7z`, ~2.2 GB) of plain-text FAQs,
  layout `<gen>/<platform>/<gameid-slug>/faqs/<gameid-slug>-faqs-<faqid>.txt`, plus
  `html_faqs.txt` (an appendix listing guides that only ever existed as HTML). Snapshot
  date **2020-03-23**. Post-2020 Playwright `?print=1` top-ups are **out of scope**
  (that is crawling — do not).
- **Builder:** `foss-setup/scripts/ai/build-gamefaqs-zim.py` (python-libzim, pinned
  `libzim==3.12.0`). Walks the extracted corpus, wraps each FAQ as minimal HTML
  (`<pre>` body + a real `<title>` = game slug + platform + faq id, so the title index /
  suggest work), builds the ZIM with `config_indexing(True,"eng")` (Xapian fulltext — the
  whole point), writes the private metadata + a generated 48×48 icon + an index page with
  per-platform counts and the HTML-only appendix.
- **Corpus/ZIM are DATA — never in git.** Only the builder + this runbook + the check are
  versioned.

## Rebuild path (on the rig — spare the NAS I/O)

```bash
# 1. scratch + pinned tooling
mkdir -p ~/scratch/lai-14-gamefaqs/{dl,extract,out}
uv venv --python 3.12 ~/scratch/lai-14-gamefaqs/venv
uv pip install --python ~/scratch/lai-14-gamefaqs/venv/bin/python libzim==3.12.0

# 2. download the 9 archives + html_faqs.txt, verify IA md5s
BASE=https://archive.org/download/Gamespot_Gamefaqs_TXTs/Gamespot_Gamefaqs_TXTs
cd ~/scratch/lai-14-gamefaqs/dl
for n in 1 2 3 4 5 6 7 8 9; do wget -c "$BASE/gamefaqs.gamespot.com.txt.faqs.$n.gen.7z"; done
wget -c "$BASE/html_faqs.txt"
# md5s (from archive.org/metadata/Gamespot_Gamefaqs_TXTs): 1=938dd07… … verify with md5sum -c

# 3. extract (~13 GB raw, 143k .txt files)
for n in 1 2 3 4 5 6 7 8 9; do 7z x -y -o./extract dl/gamefaqs.gamespot.com.txt.faqs.$n.gen.7z; done

# 4. build (full: ~12 min CPU, ~3.6 GB out; nice + nohup it)
D=~/scratch/lai-14-gamefaqs
nohup nice -n 15 $D/venv/bin/python foss-setup/scripts/ai/build-gamefaqs-zim.py \
  --src $D/extract --html-list $D/dl/html_faqs.txt --workers 12 \
  --out $D/out/gamefaqs_en_all_2020-03.zim > $D/full-build.log 2>&1 &
# subset shard (pipeline proof, ~1 min): add  --gens 1st,2nd,3rd,4th --flavour "subset gens 1-4"
```

Both subset and full builds set the SAME metadata `Name=gamefaqs_en_private`, so the
check (which resolves the book by that Name) survives a subset→full swap with no edit.
**Never let two `gamefaqs_*` ZIMs sit in `/volume1/zim` at once** — duplicate Name.

## Placement (rig → NAS, SFTP/scp disabled on the NAS)

Stream over ssh (throttled so it doesn't fight the download queue), land atomically:

```bash
pv -q -L 30m out/gamefaqs_en_all_2020-03.zim \
  | ssh btabaska@192.168.10.4 'cat > /volume1/zim/.incoming/gamefaqs_en_all_2020-03.zim'
ssh btabaska@192.168.10.4 'md5sum /volume1/zim/.incoming/gamefaqs_en_all_2020-03.zim'   # match the rig md5
ssh nas 'mv /volume1/zim/.incoming/gamefaqs_en_all_2020-03.zim /volume1/zim/'            # atomic, same volume
# wire it into the library (root; kiwix-serve cannot hot-add):
printf '%s\n' "$PW" | ssh nas 'sudo -S sh /volume1/docker/kiwix/kiwix-library-refresh.sh'
```

The nightly DSM "kiwix library refresh" task (05:15) also picks it up; the manual run
just makes it live immediately. `/mnt/nas-zim` (rig RO CIFS mount) sees the file for
openzim-mcp automatically.

## The consumer check

`gamefaqs-zim-search` (in `verification/checks.d/local-ai.yaml`, from the mini against
NAS `:8092`) proves the human path end-to-end:

1. the catalog still lists the private book (stable `<name>gamefaqs_en_private</name>`);
2. a **real Xapian fulltext** `/search` for `chrono trigger` (Chrono Trigger = SNES/4th
   gen, present in both the subset shard and the full corpus) returns FAQ article links;
3. the first FAQ article serves with the term **and** the baked-in `PRIVATE archive`
   marker in its body.

The URL base is resolved LIVE from the catalog Name (kiwix `/search` wants the filename
base, not the metadata Name), so nothing hardcodes the subset-vs-full filename.

```bash
VERIFICATION_STATE_DIR=$(mktemp -d) /opt/verification/bin/run-checks.sh --no-notify --check gamefaqs-zim-search
```

## Common failures

| Symptom | Cause / fix |
|---|---|
| `GAMEFAQS_BAD base=none` | Library doesn't list the book — the nightly `library.xml` rebuild failed (one corrupt ZIM fails the whole all-or-nothing rebuild → previous `library.xml` kept). Check `/volume1/docker/kiwix/logs/library-refresh.log`; move the offending ZIM aside and re-run the refresh. |
| `GAMEFAQS_BAD results=0` | Fulltext index missing/broken — the ZIM must be built with `config_indexing(True,"eng")`; rebuild. |
| `GAMEFAQS_BAD bytes=…` (small) | Search hit resolved to the index page, not a FAQ — check that FAQ pages still end in `.html` under `/content/<base>/`. |
| Search slow / timeouts | DS920+ under download I/O (Wikipedia queue running) — expected; the check has generous timeouts. |
| Two `gamefaqs_*` books in the catalog | Both subset and full landed — same `Name`, must not coexist; remove one from `/volume1/zim` and refresh. |

## Note: the corrupt Wikipedia partial (found during lai-14)

lai-14 found `wikipedia_en_all_maxi_2026-02.zim` sitting **complete-but-truncated** in
`/volume1/zim` (13 GB local vs 124 GB remote) — `wget -c` had reported "done" on a short
transfer, and that corrupt ZIM was failing the whole `library.xml` rebuild (so nothing
new, including this ZIM, could be wired). Fix applied: moved the 13 GB partial back to
`/volume1/zim/.incoming/` (a valid `wget -c` resume point) and re-launched
`zim-download-queue.sh`, which resumed it. If a future download "completes" suspiciously
small, compare against the remote `Content-Length` before trusting it.
