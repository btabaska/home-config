import html
import json
import logging
import os
import re
import unicodedata
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# Readarr lookup latency exceeds 15 s under burst load (fix-48 B9: 4 of the 13
# 2026-07-18 request failures were read timeouts at the old hard-coded 15 s).
LOOKUP_TIMEOUT = int(os.environ.get("READARR_TIMEOUT", "60"))


def _norm_name(s: str) -> str:
    """Robust name/title comparison key (fix-48 B11).

    Open Library sends 'Emily Brontë' with a combining diaeresis (e + U+0308)
    while rreading-glasses serves the same author as
    'Emily 1818-1848 Bronte&#776;' — HTML-entity-encoded combining mark plus
    embedded life dates. Raw .lower() equality can never match any of these.
    HTML-unescape, NFKD-decompose, drop combining marks, casefold, then keep
    only alphabetic tokens (drops the dates) as an order-insensitive key.
    """
    s = "".join(
        c for c in unicodedata.normalize("NFKD", html.unescape(s or ""))
        if not unicodedata.combining(c)
    ).casefold()
    return " ".join(sorted(t for t in re.split(r"[^a-z]+", s) if t))


def _norm_text(s: str) -> str:
    """Like _norm_name but order-preserving — for finding one name INSIDE a
    longer text (pen-name mentions in an author bio, bmig-04)."""
    s = "".join(
        c for c in unicodedata.normalize("NFKD", html.unescape(s or ""))
        if not unicodedata.combining(c)
    ).casefold()
    return " ".join(t for t in re.split(r"[^a-z]+", s) if t)


def _name_match(a: str, b: str) -> bool:
    """Token-level author identity match (bmig-04 author gate).

    _norm_name equality handles 'Austen, Jane' vs 'Jane Austen' plus the
    diacritic/life-date/HTML-entity junk; token-subset covers middle names
    ('Emily Jane Brontë' vs 'Emily Brontë'). Empty on either side is never a
    match — an authorless candidate must not pass the gate.
    """
    na, nb = _norm_name(a), _norm_name(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    ta, tb = set(na.split()), set(nb.split())
    return ta <= tb or tb <= ta


class ReadarrClient:
    """Client for interacting with a Readarr instance."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"X-Api-Key": api_key})

    def _url(self, path: str) -> str:
        return f"{self.base_url}/api/v1{path}"

    def test_connection(self) -> dict:
        """Test connection to the Readarr instance."""
        resp = self.session.get(self._url("/system/status"), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def search_books(self, query: str) -> list:
        """Search for books using the Readarr lookup endpoint."""
        resp = self.session.get(
            self._url("/book/lookup"), params={"term": query}, timeout=LOOKUP_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()

    def lookup_by_isbn(self, isbn: str) -> list:
        """Look up a book in Readarr by ISBN."""
        resp = self.session.get(
            self._url("/book/lookup"), params={"term": f"isbn:{isbn}"}, timeout=LOOKUP_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()

    def lookup_author(self, name: str) -> list:
        """Look up an author in Readarr by name."""
        resp = self.session.get(
            self._url("/author/lookup"), params={"term": name}, timeout=LOOKUP_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()

    def get_authors(self) -> list:
        """Get all library authors (Bookshelf's /book LIST omits the embedded
        author object — resolve record authors via authorId, bmig-04)."""
        resp = self.session.get(self._url("/author"), timeout=LOOKUP_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def resolve_author(self, name: str) -> Optional[dict]:
        """Metadata-provider author record for a name — exact-ish match only
        (hardcover's author/lookup needs near-exact terms; a fuzzy hit here
        would defeat the bmig-04 author gate)."""
        try:
            for a in self.lookup_author(name):
                if _name_match(a.get("authorName", ""), name):
                    return a
        except Exception as e:
            logger.warning("Author lookup failed for '%s': %s", name, e)
        return None

    def _author_record_cached(self, name: str) -> Optional[dict]:
        key = _norm_name(name)
        cache = getattr(self, "_author_rec_cache", None)
        if cache is None:
            cache = self._author_rec_cache = {}
        if key not in cache:
            cache[key] = self.resolve_author(name)
        return cache[key]

    def author_alias_match(self, requested: str, candidate: str,
                           candidate_overview: str = "") -> bool:
        """True when the metadata provider's own author bios link the two
        names as one person (pen names, bmig-04).

        Hardcover keeps 'Mira Grant' and 'Seanan McGuire' as separate author
        identities and author/lookup does NOT surface the link — but genuine
        pen-name pairs name each other in BOTH bios. The mention must hold in
        both directions: a parody author's bio ('Pride and Prejudice and
        Zombies') names the original author one-directionally and must not
        pass the gate.
        """
        want, have = _norm_text(requested), _norm_text(candidate)
        if not want or not have:
            return False
        cand_over = candidate_overview or (
            (self._author_record_cached(candidate) or {}).get("overview") or ""
        )
        if f" {want} " not in f" {_norm_text(cand_over)} ":
            return False
        req_over = (self._author_record_cached(requested) or {}).get("overview") or ""
        return f" {have} " in f" {_norm_text(req_over)} "

    def get_quality_profiles(self) -> list:
        """Get available quality profiles."""
        resp = self.session.get(self._url("/qualityprofile"), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_metadata_profiles(self) -> list:
        """Get available metadata profiles."""
        resp = self.session.get(self._url("/metadataprofile"), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_root_folders(self) -> list:
        """Get configured root folders."""
        resp = self.session.get(self._url("/rootfolder"), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _get_metadata_profile_id(self) -> int:
        """Get the first available metadata profile ID."""
        profiles = self.get_metadata_profiles()
        if not profiles:
            raise ValueError("No metadata profiles configured in Readarr")
        return profiles[0].get("id")

    def _ensure_author_monitored(self, author: dict) -> dict:
        """Force author.monitored=True (idempotent).

        Adding with addOptions.monitor="none" (correct: we don't want the whole
        bibliography) also sets author.monitored=False as a side effect — and
        Readarr's wanted/missing EXCLUDES books whose author is unmonitored, so
        a requested book whose one-shot search found nothing is never retried
        (quality-gate H6/H16). monitorNewItems stays "none"; only the flag that
        gates wanted/missing is repaired. -- local patch (fix-25)
        """
        if author.get("monitored"):
            return author
        author_id = author.get("id")
        if author_id is None:
            return author
        try:
            full = self.session.get(self._url(f"/author/{author_id}"), timeout=LOOKUP_TIMEOUT).json()
            full["monitored"] = True
            resp = self.session.put(self._url(f"/author/{author_id}"), json=full, timeout=LOOKUP_TIMEOUT)
            if resp.ok:
                logger.info("Monitored author id=%s '%s'", author_id, full.get("authorName"))
                return resp.json()
            logger.warning("Could not monitor author id=%s: HTTP %s", author_id, resp.status_code)
        except Exception as e:
            logger.warning("Could not monitor author id=%s: %s", author_id, e)
        return author

    def _ensure_author(self, author_data: dict, quality_profile_id: int, root_folder: str) -> dict:
        """Ensure the author exists in Readarr, monitored. Returns the author record."""
        author_name = author_data.get("authorName", "")
        foreign_author_id = author_data.get("foreignAuthorId", "")

        if not author_name or author_name == "Unknown":
            raise ValueError(
                f"Cannot add author: no valid author name provided. "
                f"Got: {json.dumps(author_data)}"
            )

        logger.info(
            "Ensuring author: name='%s', foreignAuthorId='%s'", author_name, foreign_author_id
        )

        # Check existing authors in Readarr
        existing = self.session.get(self._url("/author"), timeout=LOOKUP_TIMEOUT).json()

        # Match by foreignAuthorId first (most reliable)
        if foreign_author_id:
            match = next(
                (a for a in existing if a.get("foreignAuthorId") == foreign_author_id),
                None,
            )
            if match:
                logger.info("Author already exists (matched by ID): %s", match.get("authorName"))
                return self._ensure_author_monitored(match)

        # Match by name (diacritic-insensitive, fix-48 B11)
        match = next(
            (a for a in existing if _norm_name(a.get("authorName", "")) == _norm_name(author_name)),
            None,
        )
        if match:
            logger.info("Author already exists (matched by name): %s", match.get("authorName"))
            return self._ensure_author_monitored(match)

        # Author not in Readarr — need to add it
        # If we don't have a valid foreignAuthorId, look up the author by name
        # to get the correct metadata provider ID first.
        if not foreign_author_id:
            logger.info("No foreignAuthorId, looking up author by name: '%s'", author_name)
            lookup = self.session.get(
                self._url("/author/lookup"),
                params={"term": author_name},
                timeout=LOOKUP_TIMEOUT,
            )
            if lookup.ok and lookup.json():
                all_results = lookup.json()
                for i, r in enumerate(all_results[:5]):
                    logger.info(
                        "  lookup[%d]: '%s' (foreignAuthorId='%s')",
                        i, r.get("authorName", ""), r.get("foreignAuthorId", ""),
                    )
                # Prefer exact name match (diacritic-insensitive, fix-48 B11)
                exact = [
                    a for a in all_results
                    if _norm_name(a.get("authorName", "")) == _norm_name(author_name)
                ]
                if exact:
                    author_data = exact[0]
                    foreign_author_id = author_data.get("foreignAuthorId", "")
                    logger.info("Using exact lookup match: foreignAuthorId='%s'", foreign_author_id)
                else:
                    raise ValueError(
                        f"Could not find author '{author_name}' in Readarr metadata"
                    )
            else:
                raise ValueError(
                    f"Could not find author '{author_name}' in Readarr metadata"
                )

        metadata_profile_id = self._get_metadata_profile_id()
        author_payload = {
            "authorName": author_data.get("authorName", author_name),
            "foreignAuthorId": foreign_author_id,
            "qualityProfileId": quality_profile_id,
            "metadataProfileId": metadata_profile_id,
            "rootFolderPath": root_folder,
            "monitored": True,
            "monitorNewItems": "none",
            "addOptions": {
                "monitor": "none",
                "searchForMissingBooks": False,
            },
        }
        for key in ("images", "overview", "links", "genres", "ratings"):
            if author_data.get(key):
                author_payload[key] = author_data[key]

        resp = self.session.post(
            self._url("/author"), json=author_payload, timeout=LOOKUP_TIMEOUT
        )

        if resp.ok:
            return self._ensure_author_monitored(resp.json())

        # Still failing — check if author was added by another process
        updated = self.session.get(self._url("/author"), timeout=LOOKUP_TIMEOUT).json()
        match = next(
            (a for a in updated if a.get("foreignAuthorId") == foreign_author_id),
            None,
        )
        if match:
            return self._ensure_author_monitored(match)
        match = next(
            (a for a in updated if _norm_name(a.get("authorName", "")) == _norm_name(author_name)),
            None,
        )
        if match:
            return self._ensure_author_monitored(match)

        resp.raise_for_status()

    def add_book(self, book_data: dict, quality_profile_id: int, root_folder: str) -> dict:
        """Add a book to Readarr for downloading."""
        added_author = self._ensure_author(
            book_data.get("author", {}),
            quality_profile_id,
            root_folder,
        )
        logger.info("Author for book '%s': %s (id=%s)", book_data.get("title"), added_author.get("authorName"), added_author.get("id"))

        foreign_book_id = book_data.get("foreignBookId", "")
        foreign_edition_id = book_data.get("foreignEditionId", "")
        title = book_data.get("title", "Unknown")

        # Check if the book already exists in Readarr
        if foreign_book_id:
            existing_books = self.session.get(self._url("/book"), timeout=LOOKUP_TIMEOUT).json()
            match = next(
                (b for b in existing_books if b.get("foreignBookId") == foreign_book_id),
                None,
            )
            if match:
                logger.info("Book already exists: '%s' (id=%s)", match.get("title"), match.get("id"))
                # May pre-exist UNMONITORED (Readarr auto-imports the author's
                # whole bibliography) -> a bare return leaves the request stuck
                # "processing". Monitor + search it. -- local patch (libreseerr-diagnosis)
                self._monitor_and_search(match)
                return match

        # Build the edition payload.  Readarr's EditionResourceMapper.ToModel
        # throws ArgumentNullException('source') when editions is null.
        # The lookup result has images/links/ratings at the book level
        # but not at the edition level — EditionResource expects them.
        edition = {
            "foreignEditionId": foreign_edition_id,
            "title": title,
            "monitored": True,
        }
        # Copy edition-level fields from the lookup if present
        for key in ("images", "links", "ratings", "disambiguation",
                    "remoteCover", "grabbed", "titleSlug"):
            if key in book_data:
                edition[key] = book_data[key]

        book_payload = {
            "foreignBookId": foreign_book_id,
            "foreignEditionId": foreign_edition_id,
            "title": title,
            "authorId": added_author.get("id"),
            "qualityProfileId": quality_profile_id,
            "rootFolderPath": root_folder,
            "monitored": True,
            # False pins the requested edition (readarr-api-quirks): with True,
            # Readarr may match/file any edition of the work — fix-46 B3, the
            # enabler for the foreign-edition grabs and wrong-edition filing.
            "anyEditionOk": False,
            "editions": [edition],
            "author": added_author,
            "addOptions": {
                "addType": "manual",
                "searchForMissingBooks": False,
            },
        }

        logger.info("Adding book: %s", json.dumps(book_payload))

        resp = self.session.post(
            self._url("/book"), json=book_payload, timeout=LOOKUP_TIMEOUT
        )

        if not resp.ok:
            # The book may already exist (orphaned from a prior partial add).
            # Re-check and return the existing book.
            existing_books = self.session.get(self._url("/book"), timeout=LOOKUP_TIMEOUT).json()
            match = next(
                (b for b in existing_books if b.get("foreignBookId") == foreign_book_id),
                None,
            )
            if match:
                logger.info("Book already exists (after POST error): '%s' (id=%s)", match.get("title"), match.get("id"))
                self._monitor_and_search(match)
                return match

            logger.error("POST /book failed (%d): %s", resp.status_code, resp.text[:500])

        resp.raise_for_status()
        result = resp.json()
        book_id = result.get("id")

        # Trigger a search for just this book via the command API
        if book_id:
            search_resp = self.session.post(
                self._url("/command"),
                json={"name": "BookSearch", "bookIds": [book_id]},
                timeout=LOOKUP_TIMEOUT,
            )
            if search_resp.ok:
                logger.info("Triggered BookSearch for book id=%d", book_id)
            else:
                logger.warning(
                    "BookSearch command failed (%d): %s",
                    search_resp.status_code, search_resp.text[:200],
                )

        return result

    def _monitor_and_search(self, book: dict) -> None:
        """Ensure an already-existing book is monitored and being searched.

        Readarr auto-imports an author's full bibliography as UNMONITORED
        books, so a requested title often already exists with monitored=False
        -> it never downloads and the request sticks on "processing". Monitor
        it (if needed) and trigger a search when it has no file yet.
        """
        book_id = book.get("id")
        if not book_id:
            return
        has_file = (book.get("statistics") or {}).get("bookFileCount", 0) > 0
        if not book.get("monitored"):
            try:
                self.session.put(
                    self._url("/book/monitor"),
                    json={"bookIds": [book_id], "monitored": True},
                    timeout=LOOKUP_TIMEOUT,
                )
                logger.info("Monitored pre-existing book id=%s", book_id)
            except Exception as e:
                logger.warning("Could not monitor book id=%s: %s", book_id, e)
        if not has_file:
            try:
                self.session.post(
                    self._url("/command"),
                    json={"name": "BookSearch", "bookIds": [book_id]},
                    timeout=LOOKUP_TIMEOUT,
                )
                logger.info("Triggered BookSearch for pre-existing book id=%s", book_id)
            except Exception as e:
                logger.warning("BookSearch failed for book id=%s: %s", book_id, e)

    def adopt_library_book(self, title: str, author_name: str) -> Optional[dict]:
        """Find an existing library record by normalized title/author, ensure
        it is monitored and searched, and return it (fix-48).

        The metadata lookup often ranks junk user-uploaded editions above the
        canonical work — or omits the canonical work entirely (The Return of
        the King: every lookup hit was a 'Custom Rebind by ValBinds' record
        that 400s on add, while the real record already sat in the library
        unmonitored). Matching the library directly rescues those requests
        without any POST /book.
        """
        want_t = _norm_name(title)
        if not want_t:
            return None
        want_a = author_name if author_name and author_name != "Unknown" else ""
        authors_by_id = None
        for b in self.get_books():
            if _norm_name(b.get("title", "")) != want_t:
                continue
            author = b.get("author") or {}
            have_a = author.get("authorName", "")
            if not have_a and b.get("authorId"):
                # Bookshelf's /book list carries author=None — resolve via the
                # (lazily cached) author list. (bmig-04)
                if authors_by_id is None:
                    authors_by_id = {a.get("id"): a for a in self.get_authors()}
                author = authors_by_id.get(b.get("authorId")) or {}
                have_a = author.get("authorName", "")
            if want_a:
                # The C4 author gate applies to adoption too: a title
                # coincidence ('Feed') must not adopt another author's
                # record. (bmig-04)
                if not have_a:
                    continue
                if not (_name_match(want_a, have_a)
                        or self.author_alias_match(
                            want_a, have_a, author.get("overview") or "")):
                    continue
            logger.info(
                "Request '%s' matches existing library book id=%s ('%s') — adopting",
                title, b.get("id"), b.get("title"),
            )
            self._monitor_and_search(b)
            return b
        return None

    def trigger_search(self, book_id: int) -> bool:
        """Re-trigger a BookSearch for one book (fix-48 B10 reconciler retry)."""
        resp = self.session.post(
            self._url("/command"),
            json={"name": "BookSearch", "bookIds": [book_id]},
            timeout=LOOKUP_TIMEOUT,
        )
        if resp.ok:
            logger.info("Re-triggered BookSearch for book id=%s", book_id)
        else:
            logger.warning(
                "BookSearch re-trigger failed for book id=%s (%d): %s",
                book_id, resp.status_code, resp.text[:200],
            )
        return resp.ok

    def get_queue(self) -> list:
        """Get current download queue."""
        resp = self.session.get(self._url("/queue"), params={"pageSize": 200}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("records", data) if isinstance(data, dict) else data

    def get_book_status(self, book_id: int) -> Optional[dict]:
        """Get the status of a specific book."""
        resp = self.session.get(self._url(f"/book/{book_id}"), timeout=10)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def get_books(self) -> list:
        """Get all books from the Readarr library."""
        resp = self.session.get(self._url("/book"), timeout=LOOKUP_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def get_history(self) -> list:
        """Get download history."""
        resp = self.session.get(
            self._url("/history"), params={"pageSize": 50}, timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("records", data) if isinstance(data, dict) else data
