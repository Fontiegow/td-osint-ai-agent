from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, model_validator


class DateRange(BaseModel):
    """Temporal boundary filter for source search queries."""

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_date_order(self) -> "DateRange":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be earlier than start_date")
        return self


class RawDocument(BaseModel):
    """Unprocessed document payload extracted directly from an ingestion source."""

    title: Optional[str] = None
    url: Optional[str] = None
    source: str
    published_at: Optional[datetime] = None
    raw_content: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)