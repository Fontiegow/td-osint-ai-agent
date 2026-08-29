from datetime import datetime, timezone
import httpx
import pytest

from app.domain.ingestion.schemas import DateRange
from app.infrastructure.ingestion.rss_connector import RSSConnector

SAMPLE_ATOM_XML = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Security Feed</title>
  <entry>
    <title>Critical Zero-Day Advisory</title>
    <link href="https://example.com/security/zero-day"/>
    <updated>2026-08-28T10:00:00Z</updated>
    <summary>A major vulnerability was disclosed today.</summary>
    <author><name>Security Team</name></author>
  </entry>
</feed>
"""


@pytest.mark.asyncio
async def test_rss_connector_fetches_and_filters_documents():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=SAMPLE_ATOM_XML)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        connector = RSSConnector(
            feed_urls=["https://example.com/feed.xml"], client=client
        )
        date_range = DateRange(
            start_date=datetime(2026, 8, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 8, 29, tzinfo=timezone.utc),
        )

        docs = await connector.search(query="Zero-Day", date_range=date_range)

        assert len(docs) == 1
        doc = docs[0]
        assert doc.source == "rss"
        assert doc.title == "Critical Zero-Day Advisory"
        assert doc.url == "https://example.com/security/zero-day"
        assert doc.metadata["feed_title"] == "Security Feed"
        assert doc.metadata["author"] == "Security Team"