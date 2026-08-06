# `strategywiki-zim-handler.sh`

> lai-15 completion handler (runs on the MINI, invoked by

**Path:** `foss-setup/scripts/ai/strategywiki-zim-handler.sh` · **Category:** [ai](index.md) · **Type:** Bash

## What it does

```text
 strategywiki-zim-handler.sh — lai-15 completion handler (runs on the MINI, invoked by
 build-strategywiki-zim.sh once mwoffliner exits 0).

 Steps, each logged to the parent build.log and reflected in $BASE/status:
   1. locate the produced .zim in $OUT
   2. VALIDATING — zimcheck integrity + checksum (kiwix-tools, same image+digest the
      NAS refresh script pins) — a corrupt ZIM must never reach the library
   3. PUSHING    — stream to NAS /volume1/zim/.incoming over ssh (SFTP/scp are disabled
      on the NAS), md5-verify, then atomic mv into /volume1/zim (same volume)
   4. PUSHED_AWAITING_REFRESH:<file> — the nightly DSM "kiwix library refresh" (05:15)
      rebuilds library.xml and bounces kiwix-serve; the file is then live LAN/tailnet
      (kiwix.tabaska.us + NAS :8092) and openzim-mcp sees it via the rig RO mount.

 NAS filename is normalized to strategywiki_en_all_nopic_<YYYY-MM>.zim regardless of
 what mwoffliner named the file, so the verification check + runbook match.
```

## Environment / variables referenced

`BASE`, `DEST_NAME`, `NAS`, `OUT`, `SSH`, `STATUS`, `TOOLS`

## See also

- [`build-gamefaqs-zim.py`](build-gamefaqs-zim-py.md)
- [`build-strategywiki-zim.sh`](build-strategywiki-zim-sh.md)
- [`wiki-rag-sync.py`](wiki-rag-sync-py.md)
- [ai scripts](index.md) · [All scripts](../index.md)
