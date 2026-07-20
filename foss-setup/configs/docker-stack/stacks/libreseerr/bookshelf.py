"""Bookshelf backend client (bmig-04).

Bookshelf is the maintained Readarr fork and serves the same /api/v1 surface
(the container even reports itself as "Readarr" in /system/status). The
image's own bookshelf.py is the unpatched upstream client — this bind-mounted
file shadows it so the Bookshelf backend inherits every local request-path
guard from the patched ReadarrClient in one place: fix-25 author-monitor
repair, fix-46 anyEditionOk=False edition pinning, fix-48 timeouts/adoption/
name normalization, and the bmig-04 author-gate helpers.
"""
from readarr import ReadarrClient


class BookshelfClient(ReadarrClient):
    """Client for a Bookshelf instance (Readarr-compatible v1 API)."""

    def get_quality_profiles(self) -> list:
        # bmig-06: the UI defaults to the FIRST profile returned. On old
        # readarr profile id 1 was "EPUB Preferred"; on Bookshelf the clone
        # landed on id 3, and the stock PDF-tolerant "eBook" profile at id 1
        # silently became the request default (books-format-guard B7 class —
        # authors 13/14 landed on it before the 2026-07-20 fix). The stock
        # profile is deleted server-side; this ordering keeps the default
        # correct even if a future Bookshelf upgrade recreates stock profiles.
        profiles = super().get_quality_profiles()
        return sorted(
            profiles, key=lambda p: (p.get("name") != "EPUB Preferred", p.get("id", 0))
        )
