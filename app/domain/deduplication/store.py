import logging
from threading import RLock
from typing import Dict, Optional, Set

from app.domain.deduplication.schemas import compute_content_hash
from app.domain.ingestion.schemas import CanonicalDocument

logger = logging.getLogger(__name__)


class InMemoryDocumentStore:
    """Thread-safe index for Layer 1 (URL) and Layer 2 (Content Hash) fast lookups."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._documents: Dict[str, CanonicalDocument] = {}
        self._url_index: Dict[str, str] = {}  # url -> doc_id
        self._content_hash_index: Dict[str, str] = {}  # content_hash -> doc_id

    def exists_by_url(self, url: str) -> Optional[str]:
        """Layer 1 Check: Returns matching doc_id if canonical URL exists."""
        with self._lock:
            return self._url_index.get(url.strip().lower())

    def exists_by_content_hash(self, content: str) -> Optional[str]:
        """Layer 2 Check: Returns matching doc_id if normalized content hash exists."""
        content_hash = compute_content_hash(content)
        with self._lock:
            return self._content_hash_index.get(content_hash)

    def get_by_id(self, doc_id: str) -> Optional[CanonicalDocument]:
        """Retrieves a document by doc_id."""
        with self._lock:
            return self._documents.get(doc_id)

    def add(self, doc: CanonicalDocument) -> None:
        """Stores document and indexes its URL and content hash."""
        content_hash = compute_content_hash(doc.content)
        normalized_url = doc.url.strip().lower()

        with self._lock:
            self._documents[doc.doc_id] = doc
            self._url_index[normalized_url] = doc.doc_id
            self._content_hash_index[content_hash] = doc.doc_id

        logger.debug("Indexed document %s (URL: %s)", doc.doc_id, doc.url)

    def clear(self) -> None:
        """Flushes all stored documents and indexes."""
        with self._lock:
            self._documents.clear()
            self._url_index.clear()
            self._content_hash_index.clear()

    def count(self) -> int:
        """Returns the total number of unique documents indexed."""
        with self._lock:
            return len(self._documents)