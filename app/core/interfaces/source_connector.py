from abc import ABC, abstractmethod
from typing import List

from app.domain.ingestion.schemas import DateRange, RawDocument


class SourceConnector(ABC):
    """Abstract base class contract for all OSINT data ingestion connectors."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique identifier representing the data source (e.g., 'google_news', 'rss')."""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        date_range: DateRange,
    ) -> List[RawDocument]:
        """Fetch raw documents matching the search query and optional date filter."""
        pass