# tests/unit/test_document_normalizer.py

from datetime import datetime, timezone
import pytest

from app.domain.ingestion.normalizer import DocumentNormalizer, NormalizationError
from app.domain.ingestion.schemas import RawDocument


def test_url_canonicalization_strips_tracking():
    normalizer = DocumentNormalizer()
    raw_url = "https://Example.COM:443/article/123/?utm_source=twitter&fbclid=xyz&id=99#header"
    clean_url = normalizer.canonicalize_url(raw_url)

    assert clean_url == "https://example.com/article/123?id=99"


def test_clean_text_removes_html_tags_and_unescapes():
    normalizer = DocumentNormalizer()
    raw_html = "<h1>Header &amp; Title</h1><p>Some   body text with <a href='#'>links</a>.</p>"
    cleaned = normalizer.clean_text(raw_html)

    assert cleaned == "Header & Title Some body text with links."


def test_normalizer_transforms_valid_raw_document():
    normalizer = DocumentNormalizer()
    raw_doc = RawDocument(
        title="  <b>Breaking AI News</b>  ",
        url="https://news.example.com/item/?utm_medium=email",
        source="rss",
        published_at=datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        raw_content="<p>This is a valid long news content body for testing normalizer logic.</p>",
        metadata={"author": "Reporter"},
    )

    canonical = normalizer.normalize(raw_doc)

    assert canonical.title == "Breaking AI News"
    assert canonical.url == "https://news.example.com/item"
    assert canonical.content == "This is a valid long news content body for testing normalizer logic."
    assert len(canonical.doc_id) == 64  # SHA-256 hex string length
    assert canonical.metadata["author"] == "Reporter"


def test_normalizer_raises_error_on_short_content():
    normalizer = DocumentNormalizer()
    raw_doc = RawDocument(
        title="Valid Title",
        url="https://example.com",
        source="rss",
        raw_content="Too short",  # < 10 characters
    )

    with pytest.raises(NormalizationError, match="insufficient content length"):
        normalizer.normalize(raw_doc)