# Roadmap — books-cutover

7 task(s). Status mirrors `docs/progress.json` (the source of truth).

| Task | Title | Status | Effort |
|---|---|---|---|
| `bmig-01` | Books cutover 1/6: Hardcover API key + parallel rreading-glasses:hardcover instance (C2/C3 source fix) | ✅ done | 45-90 min |
| `bmig-02` | Books cutover 2/6: deploy Bookshelf (Readarr fork) in parallel, wired to hardcover metadata | ✅ done | 60-120 min |
| `bmig-03` | Books cutover 3/6: migrate the library into Bookshelf (authors + existing files, no re-downloads) | ✅ done | 90-150 min |
| `bmig-04` | Books cutover 4/6: libreseerr -> Bookshelf backend + author-gate + ISBN-first + fail-loudly (C1/C4 fix) | ✅ done | 60-120 min |
| `bmig-05` | Books cutover 5/6: collateral cleanup (C5), re-drive stuck requests, decommission readarr + goodreads metadata | ✅ done | 90-150 min |
| `bmig-06` | Books cutover 6/6: migrate all checks to Bookshelf + new tripwires (token expiry, author parity, search canary) + docs + close | ⬜ open | 90-150 min |
| `books-hc-upstream-swap` | Swap rreading-glasses-hc off the temporary local image once upstream fixes Hardcover batch limit (#574) | ⬜ open | 15-30 min |

[← Roadmap overview](index.md)
