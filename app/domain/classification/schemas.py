from enum import Enum
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class EventType(str, Enum):
    TECHNOLOGY = "technology"
    FINANCIAL = "financial"
    REGULATORY = "regulatory"
    COMMERCIAL = "commercial"
    STRATEGIC = "strategic"
    OPERATIONAL = "operational"
    CYBERSECURITY = "cybersecurity"
    OTHER = "other"


STANDARD_TOPICS = [
    "5G",
    "AI",
    "cloud",
    "investment",
    "pricing",
    "regulation",
    "partnership",
    "customer growth",
    "network expansion",
    "cybersecurity",
    "financial performance",
    "competition",
]


class DocumentClassification(BaseModel):
    """Structured management intelligence metadata extracted from a document."""

    brand: Optional[str] = Field(
        default="Unknown",
        description="Primary brand, entity, or corporate subject identified in the text.",
    )
    topics: List[str] = Field(
        default_factory=list,
        description="List of domain and business topics identified in the content.",
    )
    event_type: EventType = Field(
        default=EventType.OTHER,
        description="Primary event category for management intelligence classification.",
    )
    sentiment: Literal["positive", "neutral", "negative"] = Field(
        default="neutral",
        description="Overall business tone/sentiment of the news.",
    )
    importance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Normalized strategic importance score (0.0 = trivial, 1.0 = critical executive alert).",
    )

    @field_validator("topics")
    @classmethod
    def normalize_topics(cls, topics: List[str]) -> List[str]:
        cleaned = [t.strip().lower() for t in topics if t and t.strip()]
        return list(dict.fromkeys(cleaned))


class ClassifiedDocument(BaseModel):
    """Canonical document combined with extracted strategic classification metadata."""

    doc_id: str
    classification: DocumentClassification