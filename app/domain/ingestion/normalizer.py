# app/domain/ingestion/normalizer.py

import hashlib
import html
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.domain.ingestion.schemas import CanonicalDocument, RawDocument

logger = logging.getLogger(__name__)

# Tracking query parameters to strip during URL canonicalization
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
    "msclkid",
    "_ga",
}


class NormalizationError(Exception):
    """Raised when a RawDocument fails normalization criteria."""


class DocumentNormalizer:
    """Pipeline for cleaning and transforming RawDocuments into CanonicalDocuments."""

    def normalize(self, raw_doc: RawDocument) -> CanonicalDocument:
        """
        Transforms a RawDocument into a validated CanonicalDocument.

        :param raw_doc: The incoming uncleaned document model
        :return: A standardized CanonicalDocument
        :raises NormalizationError: If title/content is missing or unparseable
        """
        if not raw_doc.url:
            raise NormalizationError("Raw document missing mandatory 'url' field.")

        canonical_url = self.canonicalize_url(raw_doc.url)
        clean_title = self.clean_text(raw_doc.title or "")
        clean_content = self.clean_text(raw_doc.raw_content or "")

        # Mandatory content presence validation
        if not clean_title:
            raise NormalizationError(f"Document at '{canonical_url}' lacks a valid title.")
        if len(clean_content) < 10:
            raise NormalizationError(
                f"Document at '{canonical_url}' has insufficient content length ({len(clean_content)} chars)."
            )

        # Fallback timestamp to UTC now if published_at is absent
        published_at = raw_doc.published_at or datetime.now(timezone.utc)
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)

        # Compute deterministic hash from canonical URL
        doc_id = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()

        return CanonicalDocument(
            doc_id=doc_id,
            title=clean_title,
            url=canonical_url,
            source=raw_doc.source,
            published_at=published_at,
            content=clean_content,
            language=raw_doc.metadata.get("language", "en"),
            metadata=raw_doc.metadata,
        )

    @staticmethod
    def canonicalize_url(url: str) -> str:
        """Strips query tracking parameters, fragments, and standardizes URL formatting."""
        parsed = urlparse(url.strip())
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        # Remove port 80/443 defaults if explicit
        if netloc.endswith(":80"):
            netloc = netloc[:-3]
        elif netloc.endswith(":443"):
            netloc = netloc[:-4]

        # Filter out tracking query params
        query_params = parse_qsl(parsed.query, keep_blank_values=False)
        filtered_params = [
            (k, v) for k, v in query_params if k.lower() not in TRACKING_PARAMS
        ]
        new_query = urlencode(filtered_params)

        # Normalize trailing slash on path
        path = parsed.path
        if path != "/" and path.endswith("/"):
            path = path[:-1]

        # Reconstruct without fragment (#)
        return urlunparse((scheme, netloc, path, parsed.params, new_query, ""))

    @staticmethod
    def clean_text(text: str) -> str:
        """Strips HTML tags, unescapes entities, and collapses excessive whitespace."""
        if not text:
            return ""

        # Unescape HTML entities (&amp; -> &, &quot; -> ", etc.)
        text = html.unescape(text)

        # Replace HTML markup tags with a space to separate adjacent block elements
        text = re.sub(r"<[^>]+>", " ", text)

        # Clean spaces preceding common closing punctuation
        text = re.sub(r"\s+([.,!?;:])", r"\1", text)

        # Normalize spaces, tabs, non-breaking spaces, and newlines
        text = re.sub(r"\s+", " ", text).strip()

        return text