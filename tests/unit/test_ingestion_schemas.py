from datetime import datetime, timedelta
import pytest
from pydantic import ValidationError

from app.domain.ingestion.schemas import DateRange, RawDocument


def test_date_range_valid():
    now = datetime.now()
    dr = DateRange(start_date=now - timedelta(days=7), end_date=now)
    assert dr.start_date < dr.end_date


def test_date_range_invalid_order():
    now = datetime.now()
    with pytest.raises(ValidationError):
        DateRange(start_date=now, end_date=now - timedelta(days=1))


def test_raw_document_construction():
    doc = RawDocument(
        title="OSINT Ingestion Article",
        url="https://example.com/article",
        source="google_news",
        raw_content="Raw html or plain text content",
        metadata={"author": "Analyst"},
    )
    assert doc.source == "google_news"
    assert doc.metadata["author"] == "Analyst"