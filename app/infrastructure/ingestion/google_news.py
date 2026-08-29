import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import quote_plus

import feedparser
import httpx

from app.core.interfaces.source_connector import SourceConnector
from app.domain.ingestion.schemas import DateRange, RawDocument

logger = logging.getLogger(__name__)


class GoogleNewsConnector(SourceConnector):
    """Async ingestion connector for retrieving RSS news feeds from Google News."""

    BASE_URL: str = "https://news.google.com/rss/search"

    def __init__(
        self,
        language: str = "en-US",
        country: str = "US",
        ceid: str = "US:en",
        timeout: float = 10.0,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        """
        Initialize Google News RSS connector configuration.

        :param language: Interface language code (hl parameter)
        :param country: Geography country code (gl parameter)
        :param ceid: Country edition ID formatted as COUNTRY:language
        :param timeout: HTTP request timeout in seconds
        :param client: Optional shared httpx.AsyncClient instance
        """
        self.language = language
        self.country = country
        self.ceid = ceid
        self.timeout = timeout
        self._client = client
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }

    @property
    def source_name(self) -> str:
        return "google_news"

    def _build_search_url(self, query: str, date_range: DateRange) -> str:
        """Constructs the target Google News RSS search URL with query parameters and relative timeframe."""
        formatted_query = query.strip()

        # Append Google search operators if date boundaries are supplied
        if date_range.start_date:
            formatted_query += f" after:{date_range.start_date.strftime('%Y-%m-%d')}"
        if date_range.end_date:
            formatted_query += f" before:{date_range.end_date.strftime('%Y-%m-%d')}"

        encoded_q = quote_plus(formatted_query)
        return (
            f"{self.BASE_URL}?q={encoded_q}"
            f"&hl={self.language}&gl={self.country}&ceid={self.ceid}"
        )

    async def search(
        self,
        query: str,
        date_range: DateRange,
        max_results: Optional[int] = None,
    ) -> List[RawDocument]:
        """
        Fetch raw news documents matching the query and date range.

        :param query: Search keywords or boolean terms
        :param date_range: DateRange filtering options
        :param max_results: Optional ceiling for returned documents
        :return: List of RawDocument instances
        """
        url = self._build_search_url(query=query, date_range=date_range)
        xml_content = await self._fetch_raw_rss(url)

        # Offload feedparser execution to a thread to avoid blocking the async loop
        loop = asyncio.get_running_loop()
        feed = await loop.run_in_executor(None, feedparser.parse, xml_content)

        if feed.get("bozo", 0) and feed.get("bozo_exception"):
            logger.warning(
                f"Feedparser flagged malformed XML for Google News query '{query}': {feed.bozo_exception}"
            )

        entries = feed.entries[:max_results] if max_results else feed.entries
        documents: List[RawDocument] = []

        for entry in entries:
            # Extract publisher source name
            source_info = getattr(entry, "source", {})
            source_title = (
                source_info.get("title")
                if isinstance(source_info, dict)
                else getattr(source_info, "text", "Google News")
            )

            # Extract publication timestamp
            published_at = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published_at = datetime(
                    *entry.published_parsed[:6], tzinfo=timezone.utc
                )

            # Construct standardized domain document
            doc = RawDocument(
                title=getattr(entry, "title", None),
                url=getattr(entry, "link", None),
                source=self.source_name,
                published_at=published_at,
                raw_content=getattr(entry, "summary", None),
                metadata={
                    "publisher": source_title,
                    "publisher_url": (
                        source_info.get("href")
                        if isinstance(source_info, dict)
                        else None
                    ),
                    "id": getattr(entry, "id", None),
                    "search_query": query,
                },
            )
            documents.append(doc)

        return documents

    async def _fetch_raw_rss(self, url: str) -> str:
        """Executes the HTTP GET request to retrieve raw RSS feed XML content."""
        if self._client and not self._client.is_closed:
            response = await self._client.get(
                url, headers=self._headers, timeout=self.timeout
            )
            response.raise_for_status()
            return response.text

        async with httpx.AsyncClient(
            timeout=self.timeout, follow_redirects=True
        ) as client:
            response = await client.get(url, headers=self._headers)
            response.raise_for_status()
            return response.text