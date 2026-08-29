from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class ClaimType(str, Enum):
    FACTUAL = "factual"
    OPINION = "opinion"
    PROJECTION = "projection"
    ANNOUNCEMENT = "announcement"


class ExtractedClaim(BaseModel):
    text: str = Field(
        ...,
        description="The atomic, self-contained claim statement extracted from the document."
    )
    type: ClaimType = Field(
        default=ClaimType.FACTUAL,
        description="Classification of the claim type: factual, opinion, projection, or announcement."
    )
    entities: List[str] = Field(
        default_factory=list,
        description="List of key entities mentioned in the claim (e.g., organizations, regulators, technologies)."
    )
    temporal_reference: Optional[str] = Field(
        default=None,
        description="Time period, year, or timeframe explicitly referenced (e.g., '2026', 'Q3 2025')."
    )
    source_span: str = Field(
        ...,
        description="Exact verbatim excerpt from the source text that supports this claim."
    )

    @field_validator("text", "source_span", mode="before")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value


class ClaimExtractionResponse(BaseModel):
    claims: List[ExtractedClaim] = Field(
        default_factory=list,
        description="List of structured claims extracted from the document."
    )