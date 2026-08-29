import asyncio
import logging
from typing import List, Optional, Union
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import httpx

from app.core.interfaces.source_connector import SourceConnector
from app.domain.ingestion.schemas import DateRange, RawDocument

logger = logging.getLogger(__name__)


class OfficialWebsiteConnector(SourceConnector):
    """Async ingestion connector for scraping target corporate or news domain websites."""

    def __init__(
        self,
        target_urls: Optional[Union[str, List[str]]] = None,
        timeout: float = 10.0,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        """
        Initialize the website connector with target URL endpoints.

        :param target_urls: Single URL or list of target domain URLs to fetch
        :param timeout: HTTP request timeout in seconds
        :param client: Optional shared httpx.AsyncClient instance
        """
        if isinstance(target_urls, str):
            self.target_urls = [target_urls]
        else:
            self.target_urls = target_urls or []

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
        return "official_website"

    async def search(
        self,
        query: str,
        date_range: DateRange,
        target_urls: Optional[List[str]] = None,
        max_results: Optional[int] = None,
    ) -> List[RawDocument]:
        """
        Fetch HTML from target URLs, extract cleaned main text content, filter by search query keywords,
        and construct RawDocument instances.

        :param query: Keyword string to filter page content/title
        :param date_range: DateRange filter metadata (passed through to raw document)
        :param target_urls: Optional runtime override list of target site URLs
        :param max_results: Maximum document ceiling
        :return: List of RawDocument instances
        """
        urls = target_urls or self.target_urls
        if not urls:
            logger.warning("OfficialWebsiteConnector invoked without any target URLs configured.")
            return []

        # Concurrently fetch target pages
        tasks = [self._fetch_page(url) for url in urls]
        pages = await asyncio.gather(*tasks, return_exceptions=True)

        query_lower = query.strip().lower() if query else ""
        documents: List[RawDocument] = []
        loop = asyncio.get_running_loop()

        for url, page_html in zip(urls, pages):
            if isinstance(page_html, Exception):
                logger.error(f"Failed to fetch content from website '{url}': {page_html}")
                continue

            # Offload HTML parsing and DOM traversal to thread pool
            extracted = await loop.run_in_executor(None, self._parse_html, page_html)

            title = extracted.get("title")
            raw_content = extracted.get("content", "")

            # Query keyword filtering if query parameter provided
            if query_lower and (query_lower not in title.lower() and query_lower not in raw_content.lower()):
                continue

            parsed_url = urlparse(url)

            doc = RawDocument(
                title=title if title else None,
                url=url,
                source=self.source_name,
                published_at=None,  # Web scraping requires full normalization pipeline to deduce dates
                raw_content=raw_content if raw_content else None,
                metadata={
                    "domain": parsed_url.netloc,
                    "description": extracted.get("description"),
                    "search_query": query,
                },
            )
            documents.append(doc)

            if max_results and len(documents) >= max_results:
                return documents

        return documents

    def _parse_html(self, html_content: str) -> dict:
        """Parses raw HTML DOM to extract title, body text, and description metadata."""
        soup = BeautifulSoup(html_content, "html.parser")

        # Strip scripts, styles, and unnecessary tags
        for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            element.decompose()

        # Extract title
        title_tag = soup.find("title")
        title = title_tag.get_text().strip() if title_tag else ""

        # Extract meta description tag
        desc_meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        description = desc_meta.get("content", "").strip() if desc_meta else None

        # Extract body text content
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned_content = "\n".join(lines)

        return {
            "title": title,
            "description": description,
            "content": cleaned_content,
        }

    async def _fetch_page(self, url: str) -> str:
        """Executes an async HTTP GET request to fetch web page markup."""
        if self._client and not self._client.is_closed:
            response = await self._client.get(url, headers=self._headers, timeout=self.timeout)
            response.raise_for_status()
            return response.text

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=self._headers)
            response.raise_for_status()
            return response.text