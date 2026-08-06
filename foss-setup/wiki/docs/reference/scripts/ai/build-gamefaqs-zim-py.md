# `build-gamefaqs-zim.py`

> lai-14: package the PRIVATE GameFAQs text corpus as a ZIM.

**Path:** `foss-setup/scripts/ai/build-gamefaqs-zim.py` · **Category:** [ai](index.md) · **Type:** Python

## What it does

```text
build-gamefaqs-zim.py — lai-14: package the PRIVATE GameFAQs text corpus as a ZIM.

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
```

## See also

- [`wiki-rag-sync.py`](wiki-rag-sync-py.md)
- [ai scripts](index.md) · [All scripts](../index.md)
