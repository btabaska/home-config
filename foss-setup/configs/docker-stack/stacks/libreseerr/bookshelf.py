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
