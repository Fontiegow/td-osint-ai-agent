from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class DateRange(BaseModel):
    """Filter criteria for date range constraints during ingestion."""

    start_date: Optional[datetime] = Field(
        default=None, description="Start date/time threshold (UTC)"
    )
    end_date: Optional[datetime] = Field(
        default=None, description="End date/time threshold (UTC)"
    )

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def ensure_utc(cls, value: Optional[datetime]) -> Optional[datetime]:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return value

    @model_validator(mode="after")
    def validate_range(self) -> "DateRange":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be less than or equal to end_date")
        return self


class RawDocument(BaseModel):
    """Raw ingestion payload before normalization."""

    title: str = Field(..., min_length=1, description="Raw headline or document title")
    url: str = Field(..., description="Source URL of the document")
    source: str = Field(..., min_length=1, description="Origin source name or connector type")
    published_at: Optional[datetime] = Field(
        default=None, description="Publication timestamp if available"
    )
    raw_content: str = Field(
        ..., min_length=1, description="Raw HTML or unparsed text payload"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary connector metadata"
    )

    @field_validator("title", "raw_content", "source")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value


class CanonicalDocument(BaseModel):
    """Normalized, validated canonical document schema used across domain services."""

    doc_id: str = Field(..., min_length=1, description="Unique document ID (e.g., hash or UUID)")
    title: str = Field(..., min_length=1, description="Normalized document headline")
    url: str = Field(..., description="Canonicalized source URL")
    source: str = Field(..., min_length=1, description="Canonical source provider name")
    published_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Standardized UTC timestamp",
    )
    content: str = Field(
        ..., min_length=10, description="Cleaned, plain-text body without HTML markup"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Normalized metadata attributes"
    )

    @field_validator("published_at", mode="before")
    @classmethod
    def ensure_utc_tz(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return value