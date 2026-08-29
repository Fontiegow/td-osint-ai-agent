from datetime import datetime
from unittest.mock import patch
import httpx
import pytest

from app.domain.ingestion.schemas import DateRange
from app.infrastructure.ingestion.google_news import GoogleNewsConnector

SAMPLE_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Google News - Search</title>
        <item>
            <title>AI System Breakthrough - Tech Daily</title>
            <link>https://news.google.com/rss/articles/CBMi1A</link>
            <pubDate>Fri, 28 Aug 2026 12:00:00 GMT</pubDate>
            <description>&lt;a href="..."&gt;Read details&lt;/a&gt;</description>
            <source url="https://techdaily.com">Tech Daily</source>
        </item>
    </channel>
</rss>
"""


@pytest.mark.asyncio
async def test_google_news_connector_returns_raw_documents():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=SAMPLE_RSS_XML)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        connector = GoogleNewsConnector(client=client)
        date_range = DateRange(
            start_date=datetime(2026, 8, 1), end_date=datetime(2026, 8, 29)
        )

        docs = await connector.search(query="artificial intelligence", date_range=date_range)

        assert len(docs) == 1
        doc = docs[0]
        assert doc.source == "google_news"
        assert doc.title == "AI System Breakthrough - Tech Daily"
        assert doc.url == "https://news.google.com/rss/articles/CBMi1A"
        assert doc.published_at.year == 2026
        assert doc.metadata["publisher"] == "Tech Daily"