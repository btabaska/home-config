# KOReader + CWA + Wallabag wiring

> End-to-end wiring guide for the analogue reading stack: Calibre → CWA → KOReader (Kobo) → Wallabag, with Syncthing as a file-level backstop.
_Source: `foss-setup/scripts/reading/koreader-cwa-wallabag-wiring.md` · migrated + validated 2026-07-14._

The master library lives in **Calibre on CachyOS**, **Calibre-Web-Automated (CWA)** auto-ingests + serves it from the **NAS**, **KOReader on a Kobo** is the reading device, **Wallabag** (self-hosted on the Ubuntu Docker box) is read-it-later, and **Syncthing** does file-level P2P sync as a backstop.

!!! tip "Device pick"
    **Kobo** is smoothest — native Kobo sync from CWA *and* optional KOReader on top. A jailbroken Kindle + KOReader also works; the KOReader steps below are identical once installed.

You can run **both** the stock Kobo reader (for native CWA Kobo sync) and KOReader (for OPDS + Wallabag + KOSync). They coexist fine.

Authoritative upstream docs are linked inline — follow those for screenshots.

---

## A. Calibre desktop (CachyOS) — the library master

1. Install Calibre: `sudo pacman -S --needed calibre`.
2. Keep your library at a known path (e.g. `~/Calibre Library`). This is the master; do conversions/metadata edits here.
3. Decide how books reach the NAS:
   - **Option 1 (recommended): drop files into CWA's ingest folder** (via Syncthing or an SMB mount) and let CWA convert/import. See section D.
   - **Option 2: run Calibre's own Content Server** for OPDS/wireless to the device directly (good on the LAN when the desktop is awake).

### Calibre Content Server + wireless (optional, desktop-direct)

- **Content Server (OPDS):** `Connect/share → Start Content Server`. Note the address + port (default `8080`). Docs: <https://manual.calibre-ebook.com/server.html>
- **Wireless device connection:** `Connect/share → Start wireless device connection` — lets KOReader's Calibre plugin pull books over WiFi. Docs: <https://github.com/koreader/koreader/wiki/calibre>
- If you enable auth on the Content Server, it **must be HTTP Basic, not Digest** — KOReader doesn't support Digest. Only use Basic on a trusted LAN / behind TLS. (OPDS support: <https://github.com/koreader/koreader/wiki/OPDS-support>)

---

## B. Kobo prep + KOReader install

1. **Register the Kobo first** (initial WiFi + account setup) — a brand-new Kobo won't mount cleanly until onboarding is done.
2. Install **KOReader** using the official Kobo instructions (KFMon-based one-time installer, then drop the release onto the device): <https://github.com/koreader/koreader/wiki/Installation-on-Kobo-devices>
3. Reboot the Kobo; launch KOReader from the NickelMenu/KFMon entry.
4. Useful background: KOReader User Guide — <https://koreader.rocks/user_guide/>

---

## C. KOReader ↔ Calibre over WiFi (browse + send)

### Method A — Calibre wireless (push from desktop)

1. Calibre: `Connect/share → Start wireless device connection`.
2. KOReader: `Tools → (page 2) → Calibre → Connect` (auto-discovers the server via UDP broadcast on the same subnet). Indicator turns green when connected.
3. In Calibre, KOReader now shows as a device; select books → `Send to device`.

!!! note "Firewall on CachyOS"
    If discovery fails, allow TCP **9090** and the UDP discovery ports **54982, 48123, 39001, 44044, 59678**. Docs: <https://github.com/koreader/koreader/wiki/calibre>

### Method B — OPDS (pull from device, works against CWA too)

1. Start an OPDS source: Calibre Content Server, **or** CWA's OPDS endpoint.
2. KOReader: `Search (magnifier) → OPDS catalog → + (add)`:
   - Name: e.g. `CWA library`
   - URL: `http://<HOST>:<PORT>/opds` (CWA default `http://<nas-ip>:8083/opds`)
   - **CWA/calibre-web needs a trailing slash:** `…/opds/`
   - Username/password if the server requires them (Basic auth only).
   - Docs: <https://github.com/koreader/koreader/wiki/OPDS-support>

---

## D. CWA (NAS) auto-ingest + Kobo sync

!!! info "Deployment"
    CWA is deployed by the NAS agent. Compose lives at `foss-setup/configs/nas/calibre-web-automated/docker-compose.yml`. Pinned image: `ghcr.io/new-usemame/calibre-web-nextgen:v4.0.7` (validated live on the NAS 2026-07-14 — running, healthy, port 8083). Upstream Docker Hub crocodilestick repo stops at v4.0.6; the NextGen fork ships v4.0.7 with **CVE-2026-7713** (Kobo auth-token IDOR) fixed. Projects: [NextGen fork](https://github.com/new-usemame/Calibre-Web-NextGen) · [original CWA](https://github.com/crocodilestick/Calibre-Web-Automated)

1. Confirm CWA is up at `http://<nas-ip>:8083` and log in.
2. **Auto-ingest:** drop `.epub/.mobi/etc.` into the ingest folder (`/cwa-book-ingest` inside the container); CWA converts + imports into the library, runs the EPUB-fixer, and enforces metadata/covers.
3. **Native Kobo sync (stock Kobo reader):** enable Kobo sync in CWA, then set the Kobo's sync endpoint to CWA per the CWA Kobo docs. Requires NextGen **v4.0.7+** (CVE-2026-7713 fixed — satisfied by the deployed image). Keep CWA LAN/Tailscale-only (no public `:8083`).

---

## E. KOReader progress sync via CWA (KOSync) — recommended

CWA has a **built-in KOReader sync server** (since CWA v3.1.0); use it instead of the stock progress-sync server so progress flows KOReader → CWA → Kobo.

1. On any browser, open **`http://<nas-ip>:8083/kosync`** — this page has the plugin download + instructions. Docs: <https://deepwiki.com/crocodilestick/Calibre-Web-Automated/5.1-koreader-synchronization>
2. Download `koplugin.zip`, extract the **`cwasync.koplugin`** folder, and copy it to the device at `…/koreader/plugins/cwasync.koplugin/` (on a Kobo: `.adds/koreader/plugins/` over USB).
3. In KOReader: **disable the stock "Progress sync"** plugin to avoid conflicts (`Tools → page 2 → More tools → Plugin management`), and ensure **CWA Progress Sync** is enabled.
4. **Open a book**, then the CWA Progress Sync menu appears in the top menu (it only shows with a book open, not in the file browser).
5. Configure the plugin:
   - **Server URL:** your CWA base URL **without** `/kosync` (e.g. `https://cwa.example.com` or `http://<nas-ip>:8083`). The plugin appends `/kosync` itself — adding it yourself double-paths and fails. (Bug ref: <https://github.com/crocodilestick/Calibre-Web-Automated/issues/463>)
   - **Username / Password:** your CWA account credentials (HTTP Basic).
6. Progress now auto-syncs on page turn / book close / KOReader exit. Books are matched automatically via KOReader-compatible partial-MD5 checksums (no manual pairing).

---

## F. Wallabag in KOReader (read-it-later on the device)

!!! info "Deployment"
    Wallabag is deployed by the Docker-stack agent (image `wallabag/wallabag:2.6.14`, verified in repo 2026-07-14). Compose lives at `foss-setup/configs/docker-stack/wallabag/`. Plugin docs: <https://github.com/koreader/koreader/wiki/Wallabag>

1. In Wallabag: **create an API client** — `Settings → API clients management → Create a new client`. Note the **Client ID** and **Client secret**.
2. In KOReader, open the **Wallabag** plugin (top menu) → `Configure Wallabag server`. Tip: leave the fields blank and tap OK once — KOReader writes an empty config file you can edit comfortably over USB instead of typing on the e-ink keyboard.
3. Edit `…/koreader/settings/wallabag.lua` over USB (on a Kobo: `.adds/koreader/settings/wallabag.lua` — note the leading dot) and fill in:
   - `server_url` = your Wallabag URL (e.g. `https://wallabag.example.com`)
   - `client_id`, `client_secret` (from step 1)
   - `username`, `password` (your Wallabag login)
4. Back in KOReader: **`Synchronize articles with server`** downloads one EPUB per article into the `wallabag` folder (offline-readable).
5. Enable **`Remote mark-as-read settings → Auto-upload article statuses when downloading`** so finished articles get marked read on the server in the same sync pass.
6. (Optional) Set KOReader's **Home folder** to the `wallabag` folder so the reader opens straight into your saved articles.

---

## G. RSS / news on the device

Two complementary paths — pick based on whether you want sync:

- **Built-in News downloader (no account):** `Tools → News downloader` — point it at RSS/Atom feed URLs; it fetches entries as HTML for offline reading. Guide: <https://koreader.rocks/user_guide/> (News downloader section).
- **RSS Reader plugin (synced read-state):** the community `rssreader.koplugin` syncs against **Miniflux** (already running — compose at `foss-setup/configs/docker-stack/stacks/miniflux/`, image `miniflux/miniflux:2.3.1`), FreshRSS, CommaFeed, or Fever-API servers. Repo: <https://github.com/omer-faruq/rssreader.koplugin>

This is the "Apple News → Miniflux/Wallabag on the e-reader" tie-in: Miniflux feeds your unread queue, Wallabag holds long-reads you saved, both land on the Kobo via KOReader.

---

## H. Syncthing backstop (file-level)

Run `./syncthing-setup-cachyos.sh` on CachyOS (script at `foss-setup/scripts/reading/syncthing-setup-cachyos.sh`), then in the Web GUI (`http://127.0.0.1:8384`) share:

- A **books** folder (EPUBs) between desktop ↔ NAS ↔ device.
- Optionally the **book folder + KOReader `.sdr` sidecars**, so reading-progress metadata travels with files even off-network.

Docs: <https://docs.syncthing.net/intro/getting-started.html>

Prefer **CWA KOSync (section E)** for live cross-device progress; Syncthing is the no-cloud, file-level belt-and-suspenders for the books themselves.

---

## Verify (end-to-end)

- [ ] Drop an EPUB into CWA ingest → it appears in the CWA library + OPDS feed.
- [ ] KOReader OPDS catalog lists the book and downloads it.
- [ ] Read a few pages in KOReader, open the same book elsewhere → progress matches (CWA KOSync working).
- [ ] Save an article to Wallabag → it downloads to the Kobo's `wallabag` folder; finishing it marks it read on the server.
- [ ] Syncthing shows the books folder "Up to Date" on all peers.

---
[← Guides](index.md)
