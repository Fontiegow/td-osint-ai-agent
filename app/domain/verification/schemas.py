from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    CORROBORATED = "CORROBORATED"
    CONTRADICTED = "CONTRADICTED"
    DISPUTED = "DISPUTED"
    UNVERIFIED = "UNVERIFIED"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EvidenceRelation(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    NEUTRAL = "NEUTRAL"


class VerificationEvidence(BaseModel):
    source_name: str = Field(..., description="Name or domain of the source provider.")
    url: Optional[str] = Field(default=None, description="URL of the evidence document.")
    excerpt: str = Field(..., description="Relevant text excerpt supporting or contradicting the claim.")
    relation: EvidenceRelation = Field(..., description="Relation of the excerpt to the target claim.")
    reasoning: Optional[str] = Field(default=None, description="Brief explanation of the relationship assessment.")


class ClaimVerificationResult(BaseModel):
    """Structured report verifying a single claim against multiple evidence sources."""

    claim_id: str = Field(..., description="Unique claim identification code (e.g. C-1024).")
    claim_text: str = Field(..., description="The target claim text being verified.")
    status: VerificationStatus = Field(..., description="Overall verification verdict.")
    confidence: ConfidenceLevel = Field(..., description="Confidence score assessment.")
    supporting_sources: List[str] = Field(
        default_factory=list, description="List of unique sources supporting the claim."
    )
    contradicting_sources: List[str] = Field(
        default_factory=list, description="List of unique sources contradicting the claim."
    )
    evidence_count: int = Field(default=0, description="Total relevant evidence pieces evaluated.")
    independent_sources: int = Field(
        default=0, description="Number of distinct independent source providers."
    )
    evidence_details: List[VerificationEvidence] = Field(
        default_factory=list, description="Detailed list of evaluated evidence items."
    )