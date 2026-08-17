#!/usr/bin/env python3
"""build-gamefaqs-zim.py — lai-14: package the PRIVATE GameFAQs text corpus as a ZIM.

Source corpus: Internet Archive item `Gamespot_Gamefaqs_TXTs`
("Gamespot TXT GameFAQs - Full Archive (3/23/20)", ~2.2GB of 7z'd plain text,
layout <gen>/<platform>/<gameid-slug>/faqs/<gameid-slug>-faqs-<faqid>.txt).

PRIVACY — READ THIS FIRST
  GameFAQs guides carry PER-AUTHOR copyright. This build exists for personal,
  LAN-only reference inside the homelab. The resulting ZIM must NEVER be
  redistributed, uploaded, seeded, or exposed on the public Internet. The
  metadata baked into the ZIM (Title/Description/Tags `private;no-redistribute`)
  and every wrapped page repeat that constraint on purpose. GameFAQs itself is
  Cloudflare-Turnstile-gated: do NOT point any crawler at the live site.

What this does:
  * walks an extracted corpus tree, wraps each .txt FAQ as minimal HTML
    (<pre>) with a real <title> derived from the game slug + platform + faq id
    (so the ZIM title index / kiwix suggest work),
  * CHUNKS long guides into part-articles (2026-08-17, retrieval-granularity
    fix): a 400k-char walkthrough as ONE article made Xapian rank whole
    documents — "Pegasus Boots" surfaced junk (every long guide contains both
    words somewhere) and the AI chat lane had to page a 400k body 10k chars at
    a time to find the relevant section. Guides > CHUNK_THRESHOLD chars are
    split at blank-line boundaries into ~CHUNK_TARGET-char part pages
    (faq-<id>-p<N>.html, title "... FAQ <id> [N/M]", prev/next nav), each its
    own fulltext-indexed FRONT_ARTICLE, with faq-<id>.html kept as a parts
    index (stable path) carrying a body preview. One part fits a single capped
    openzim-mcp zim_get (24k chars),
  * builds the ZIM with libzim's Xapian FULLTEXT index (config_indexing) so
    kiwix-serve /search and openzim-mcp zim_search return real results,
  * writes library metadata (Name=gamefaqs_en_private, private tags, source
    link) + a generated 48x48 illustration + an index page with per-platform
    counts and the html_faqs.txt "known missing HTML-only guides" appendix.

Runs on the rig (venv: uv venv --python 3.12 && uv pip install libzim==3.12.0).
Typical invocations (see wiki/docs/runbooks/gamefaqs-zim.md for the full path):
  subset shard (pipeline proof, minutes):
    build-gamefaqs-zim.py --src extract/ --out gamefaqs_en_subset_2020-03.zim \
        --gens 1st,2nd,3rd,4th --flavour "subset gens 1-4"
  full build (long; nice + nohup it):
    build-gamefaqs-zim.py --src extract/ --out gamefaqs_en_all_2020-03.zim
Both use the SAME metadata Name (gamefaqs_en_private) — the verification check
resolves the book by that name, so the subset->full swap never breaks it.
Never let both files sit in /volume1/zim at once (duplicate Name).
"""

from __future__ import annotations

import argparse
import html
import re
import struct
import sys
import time
import zlib
from collections import Counter
from pathlib import Path

from libzim.writer import Creator, Hint, Item, StringProvider  # noqa: E402

ZIM_NAME = "gamefaqs_en_private"
FAQ_RE = re.compile(r"-faqs-([A-Za-z0-9]+)\.txt$")
SLUG_RE = re.compile(r"^\d+-(.+)$")

PRIVACY_LINE = ("PRIVATE archive copy — per-author copyright; "
                "never redistribute or expose publicly.")

PAGE = ("<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
        "<title>{title}</title></head><body>"
        "<h1>{game} <small>({platform}, {gen} generation)</small></h1>"
        "<p><em>GameFAQs text guide #{faqid}. {privacy}</em></p>"
        "<pre>{body}</pre></body></html>")

PART_PAGE = ("<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
             "<title>{title}</title></head><body>"
             "<h1>{game} <small>({platform}, {gen} generation)</small></h1>"
             "<p><em>GameFAQs text guide #{faqid}, part {num} of {total}. "
             "{privacy}</em></p>{nav}"
             "<pre>{body}</pre>{nav}</body></html>")

PARTS_INDEX_PAGE = ("<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
                    "<title>{title}</title></head><body>"
                    "<h1>{game} <small>({platform}, {gen} generation)</small></h1>"
                    "<p><em>GameFAQs text guide #{faqid}. {privacy}</em></p>"
                    "<p>Long guide, split into {total} parts for search "
                    "granularity:</p><ol>{toc}</ol>"
                    "<p>Preview (start of part 1):</p><pre>{preview}</pre>"
                    "</body></html>")

# Retrieval granularity (2026-08-17): guides longer than CHUNK_THRESHOLD raw
# chars are split into ~CHUNK_TARGET-char part-articles. CHUNK_MAX must stay
# under the openzim-mcp per-get content cap (24000 chars, mcpo env) so one
# zim_get returns a whole part; splits prefer blank lines, then any newline.
CHUNK_THRESHOLD = 32_000
CHUNK_TARGET = 16_000
CHUNK_MAX = 22_000


def split_chunks(text: str) -> list[str]:
    if len(text) <= CHUNK_THRESHOLD:
        return [text]
    chunks, start = [], 0
    floor = int(CHUNK_TARGET * 0.6)
    while start < len(text):
        rest = len(text) - start
        if rest <= CHUNK_MAX:
            chunks.append(text[start:])
            break
        seg = text[start:start + CHUNK_MAX]
        cut = seg.rfind("\n\n", floor)
        if cut == -1:
            cut = seg.rfind("\n", floor)
        if cut == -1:
            cut = CHUNK_TARGET
        chunks.append(seg[:cut])
        start += cut
    return chunks


def decode(raw: bytes) -> str:
    for enc in ("utf-8", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", "replace")


def game_title(gamedir: str) -> str:
    m = SLUG_RE.match(gamedir)
    slug = m.group(1) if m else gamedir
    return slug.replace("-", " ").strip().title() or gamedir


def make_icon_48() -> bytes:
    """48x48 PNG (blocky 'G' on slate), pure stdlib — no PIL on the rig."""
    w = h = 48
    fg, bg = (36, 99, 235), (15, 23, 42)
    rows = []
    for y in range(h):
        row = bytearray([0])
        for x in range(w):
            g = (8 <= y <= 39 and 8 <= x <= 39
                 and not (14 <= y <= 33 and 14 <= x <= 39
                          and not (24 <= y <= 33 and 26 <= x <= 39)
                          and not (24 <= y <= 27 and 20 <= x <= 39)))
            row += bytes(fg if g else bg)
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


class HtmlItem(Item):
    def __init__(self, path: str, title: str, content: str):
        super().__init__()
        self._path, self._title, self._content = path, title, content

    def get_path(self):
        return self._path

    def get_title(self):
        return self._title

    def get_mimetype(self):
        return "text/html"

    def get_contentprovider(self):
        return StringProvider(self._content)

    def get_hints(self):
        return {Hint.FRONT_ARTICLE: True}


def iter_faqs(src: Path, gens: list[str] | None):
    for gen_dir in sorted(p for p in src.iterdir() if p.is_dir()):
        if gens and gen_dir.name not in gens:
            continue
        for txt in sorted(gen_dir.rglob("*.txt")):
            rel = txt.relative_to(src)
            if len(rel.parts) != 5 or rel.parts[3] != "faqs":
                continue  # not <gen>/<platform>/<game>/faqs/<file>
            yield rel.parts[0], rel.parts[1], rel.parts[2], txt


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", required=True, type=Path,
                    help="extracted corpus root (contains 1st/ 2nd/ ... 9th/)")
    ap.add_argument("--out", required=True, type=Path, help="output .zim path")
    ap.add_argument("--gens", default=None,
                    help="comma-separated generation dirs to include (default all)")
    ap.add_argument("--flavour", default="full",
                    help="Flavour metadata + title suffix (e.g. 'subset gens 1-4')")
    ap.add_argument("--html-list", type=Path, default=None,
                    help="html_faqs.txt from the IA item (appendix of HTML-only "
                         "guides NOT in this corpus)")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    gens = args.gens.split(",") if args.gens else None
    t0 = time.time()

    creator = Creator(args.out)
    creator.config_indexing(True, "eng")      # Xapian fulltext — the point of lai-14
    creator.config_nbworkers(args.workers)
    counts: Counter[tuple[str, str]] = Counter()
    n = 0
    with creator:
        creator.set_mainpath("index.html")
        n_parts = 0
        for gen, platform, gamedir, txt in iter_faqs(args.src, gens):
            m = FAQ_RE.search(txt.name)
            faqid = m.group(1) if m else txt.stem
            game = game_title(gamedir)
            title = f"{game} ({platform.upper()}) — FAQ {faqid}"
            text = decode(txt.read_bytes())
            chunks = split_chunks(text)
            common = dict(game=html.escape(game), platform=html.escape(platform),
                          gen=html.escape(gen), faqid=html.escape(faqid),
                          privacy=PRIVACY_LINE)
            base = f"{gen}/{platform}/{gamedir}/faq-{faqid}"
            if len(chunks) == 1:
                creator.add_item(HtmlItem(
                    f"{base}.html", title,
                    PAGE.format(title=html.escape(title),
                                body=html.escape(text), **common)))
            else:
                total = len(chunks)
                toc_rows = []
                for i, chunk in enumerate(chunks, 1):
                    ptitle = f"{title} [{i}/{total}]"
                    prev_a = (f"<a href=\"faq-{html.escape(faqid)}-p{i - 1}.html\">"
                              f"&larr; part {i - 1}</a> · " if i > 1 else "")
                    next_a = (f" · <a href=\"faq-{html.escape(faqid)}-p{i + 1}.html\">"
                              f"part {i + 1} &rarr;</a>" if i < total else "")
                    nav = (f"<p>{prev_a}<a href=\"faq-{html.escape(faqid)}.html\">"
                           f"all {total} parts</a>{next_a}</p>")
                    creator.add_item(HtmlItem(
                        f"{base}-p{i}.html", ptitle,
                        PART_PAGE.format(title=html.escape(ptitle), num=i,
                                         total=total, nav=nav,
                                         body=html.escape(chunk), **common)))
                    n_parts += 1
                    first_line = next(
                        (ln.strip() for ln in chunk.splitlines() if ln.strip()), "")
                    toc_rows.append(
                        f"<li><a href=\"faq-{html.escape(faqid)}-p{i}.html\">"
                        f"Part {i}</a> — <code>{html.escape(first_line[:100])}"
                        f"</code></li>")
                # stable faq-<id>.html path stays valid: a parts index with a
                # searchable preview (guide head = title/ToC region).
                creator.add_item(HtmlItem(
                    f"{base}.html", title,
                    PARTS_INDEX_PAGE.format(title=html.escape(title), total=total,
                                            toc="".join(toc_rows),
                                            preview=html.escape(chunks[0][:2000]),
                                            **common)))
            counts[(gen, platform)] += 1
            n += 1
            if n % 5000 == 0:
                print(f"[{time.time() - t0:7.0f}s] {n} FAQs added "
                      f"({n_parts} part pages)", flush=True)

        # appendix: guides that only ever existed as HTML (not in the TXT corpus)
        appendix = ""
        if args.html_list and args.html_list.exists():
            creator.add_item(HtmlItem(
                "missing-html-faqs.html", "Appendix — HTML-only guides NOT included",
                PAGE.format(title="HTML-only guides NOT included",
                            game="Appendix", platform="meta", gen="n/a",
                            faqid="none", privacy=PRIVACY_LINE,
                            body=html.escape(decode(args.html_list.read_bytes())))))
            appendix = ("<p><a href=\"missing-html-faqs.html\">Appendix: HTML-only "
                        "guides NOT included in this corpus</a></p>")

        rows = "".join(
            f"<tr><td>{g}</td><td>{p}</td><td>{c}</td></tr>"
            for (g, p), c in sorted(counts.items()))
        creator.add_item(HtmlItem(
            "index.html", "GameFAQs Text Archive (PRIVATE)",
            "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
            "<title>GameFAQs Text Archive (PRIVATE)</title></head><body>"
            "<h1>GameFAQs Text Archive (PRIVATE)</h1>"
            f"<p><strong>{PRIVACY_LINE}</strong></p>"
            "<p>Snapshot 2020-03-23 (IA item Gamespot_Gamefaqs_TXTs), "
            f"{n} text guides ({html.escape(args.flavour)}). Use search — every "
            "guide is fulltext-indexed.</p>"
            f"{appendix}<table border=\"1\"><tr><th>gen</th><th>platform</th>"
            f"<th>guides</th></tr>{rows}</table></body></html>"))

        title_sfx = "" if args.flavour == "full" else f" [{args.flavour}]"
        for k, v in {
            "Name": ZIM_NAME,
            "Title": f"GameFAQs Text Archive (PRIVATE){title_sfx}",
            "Language": "eng",
            "Creator": "GameFAQs FAQ authors (individual per-author copyrights)",
            "Publisher": "homelab private build — DO NOT REDISTRIBUTE",
            "Description": "PRIVATE personal-use archive of GameFAQs text guides "
                           "(2020-03-23). Per-author copyright: never redistribute "
                           "or expose publicly.",
            "Date": "2020-03-23",
            "Flavour": args.flavour,
            "Tags": "gaming;guides;_ftindex:yes;_pictures:no;_videos:no;"
                    "private;no-redistribute",
            "Source": "https://archive.org/details/Gamespot_Gamefaqs_TXTs",
            "Scraper": "build-gamefaqs-zim.py (foss-setup lai-14)",
        }.items():
            creator.add_metadata(k, v)
        creator.add_illustration(48, make_icon_48())

    print(f"DONE {n} FAQs ({n_parts} part pages) -> {args.out} "
          f"({args.out.stat().st_size / 1e6:.0f} MB) in {time.time() - t0:.0f}s")
    return 0 if n else 1


if __name__ == "__main__":
    sys.exit(main())
