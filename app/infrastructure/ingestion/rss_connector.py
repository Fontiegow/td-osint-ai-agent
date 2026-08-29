import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional, Union
import feedparser
import httpx

from app.core.interfaces.source_connector import SourceConnector
from app.domain.ingestion.schemas import DateRange, RawDocument

logger = logging.getLogger(__name__)


class RSSConnector(SourceConnector):
    """Generic connector for fetching and parsing standard RSS and Atom feeds."""

    def __init__(
        self,
        feed_urls: Optional[Union[str, List[str]]] = None,
        timeout: float = 10.0,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        """
        Initialize the RSS connector with target feed URLs.

        :param feed_urls: Single feed URL or list of feed URLs to ingest
        :param timeout: HTTP request timeout in seconds
        :param client: Optional shared httpx.AsyncClient instance
        """
        if isinstance(feed_urls, str):
            self.feed_urls = [feed_urls]
        else:
            self.feed_urls = feed_urls or []

        self.timeout = timeout
        self._client = client
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36 OSINTAgent/1.0"
            )
        }

    @property
    def source_name(self) -> str:
        return "rss"

    async def search(
        self,
        query: str,
        date_range: DateRange,
        feed_urls: Optional[List[str]] = None,
        max_results: Optional[int] = None,
    ) -> List[RawDocument]:
        """
        Fetch entries from configured feed URLs, filter by query terms and date range,
        and map results into RawDocument instances.

        :param query: Keyword string to filter feed item titles/content
        :param date_range: DateRange filtering options
        :param feed_urls: Optional override/additional list of feed URLs
        :param max_results: Maximum total documents to return
        :return: List of RawDocument instances
        """
        target_urls = feed_urls or self.feed_urls
        if not target_urls:
            logger.warning("RSSConnector search invoked without any feed URLs configured.")
            return []

        # Fetch all feeds concurrently
        tasks = [self._fetch_and_parse_feed(url) for url in target_urls]
        parsed_feeds = await asyncio.gather(*tasks, return_exceptions=True)

        query_lower = query.strip().lower() if query else ""
        documents: List[RawDocument] = []

        for url, feed_result in zip(target_urls, parsed_feeds):
            if isinstance(feed_result, Exception):
                logger.error(f"Failed to fetch/parse RSS feed from '{url}': {feed_result}")
                continue

            feed_title = getattr(feed_result.feed, "title", "Unknown Feed")

            for entry in feed_result.entries:
                title = getattr(entry, "title", "") or ""
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
                content = summary

                # Fallback to full content array if available
                if hasattr(entry, "content") and entry.content:
                    content = entry.content[0].get("value", summary)

                # Keyword filtering (if a query string is provided)
                if query_lower and (query_lower not in title.lower() and query_lower not in content.lower()):
                    continue

                # Parse publication datetime
                published_at = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    published_at = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

                # Temporal filtering via DateRange
                if published_at:
                    if date_range.start_date and published_at < date_range.start_date:
                        continue
                    if date_range.end_date and published_at > date_range.end_date:
                        continue

                doc = RawDocument(
                    title=title if title else None,
                    url=getattr(entry, "link", None),
                    source=self.source_name,
                    published_at=published_at,
                    raw_content=content if content else None,
                    metadata={
                        "feed_url": url,
                        "feed_title": feed_title,
                        "author": getattr(entry, "author", None),
                        "id": getattr(entry, "id", None),
                    },
                )
                documents.append(doc)

                if max_results and len(documents) >= max_results:
                    return documents

        return documents

    async def _fetch_and_parse_feed(self, url: str) -> feedparser.FeedParserDict:
        """Asynchronously fetches XML from the feed URL and parses it using feedparser."""
        xml_content = await self._fetch_raw_xml(url)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, feedparser.parse, xml_content)

    async def _fetch_raw_xml(self, url: str) -> str:
        """Executes the HTTP GET request to fetch feed content."""
        if self._client and not self._client.is_closed:
            response = await self._client.get(url, headers=self._headers, timeout=self.timeout)
            response.raise_for_status()
            return response.text

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=self._headers)
            response.raise_for_status()
            return response.text