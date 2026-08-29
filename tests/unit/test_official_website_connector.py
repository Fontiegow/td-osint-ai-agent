from datetime import datetime
import httpx
import pytest

from app.domain.ingestion.schemas import DateRange
from app.infrastructure.ingestion.official_website import OfficialWebsiteConnector

SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Acme Corp Press Release</title>
    <meta name="description" content="Acme Corp launches next-gen OSINT platform." />
</head>
<body>
    <nav>Nav links to remove</nav>
    <main>
        <h1>Acme Corp Launches OSINT Platform</h1>
        <p>Today Acme Corp announced their open-source intelligence platform release.</p>
    </main>
    <footer>Footer to remove</footer>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_official_website_connector_scrapes_and_parses_html():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=SAMPLE_HTML)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        connector = OfficialWebsiteConnector(
            target_urls=["https://acme.example.com/press"], client=client
        )
        date_range = DateRange()

        docs = await connector.search(query="OSINT", date_range=date_range)

        assert len(docs) == 1
        doc = docs[0]
        assert doc.source == "official_website"
        assert doc.title == "Acme Corp Press Release"
        assert doc.url == "https://acme.example.com/press"
        assert "Acme Corp announced" in doc.raw_content
        assert "Nav links to remove" not in doc.raw_content
        assert doc.metadata["domain"] == "acme.example.com"
        assert doc.metadata["description"] == "Acme Corp launches next-gen OSINT platform."