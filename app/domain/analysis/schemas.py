from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ProbabilityLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ImpactLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TrendDirection(str, Enum):
    EMERGING = "EMERGING"
    ACCELERATING = "ACCELERATING"
    STABLE = "STABLE"
    DECLINING = "DECLINING"


class TrendItem(BaseModel):
    topic: str = Field(..., description="The trend or domain topic (e.g. 5G Standalone, AI Agents).")
    direction: TrendDirection = Field(..., description="Velocity trajectory of the trend.")
    timeframe: str = Field(..., description="Associated timeframe or period observed.")
    frequency_count: int = Field(default=1, description="Number of supporting document/claim occurrences.")
    summary: str = Field(..., description="Analytical synthesis explaining the trend movement.")


class CompetitorScore(BaseModel):
    competitor: str = Field(..., description="Entity name (e.g., Irancell, MCI, Rightel).")
    score: int = Field(..., ge=1, le=5, description="Activity intensity rating from 1 to 5.")
    summary: str = Field(..., description="Brief justification for the assigned score.")


class CompetitorTopicComparison(BaseModel):
    topic: str = Field(..., description="Domain area evaluated (e.g. 5G, AI, Cloud, Pricing).")
    scores: List[CompetitorScore] = Field(..., description="Scores for each competitor in this topic.")


class RiskItem(BaseModel):
    risk: str = Field(..., description="Concise description of identified market or operational risk.")
    probability: ProbabilityLevel = Field(..., description="Likelihood of risk materialization.")
    impact: ImpactLevel = Field(..., description="Potential business impact magnitude.")
    evidence: List[str] = Field(..., description="Specific claim quotes or document citations supporting this risk.")
    confidence: ConfidenceLevel = Field(..., description="Analyst confidence in this risk assessment.")


class OpportunityItem(BaseModel):
    opportunity: str = Field(..., description="Strategic commercial or technical opportunity.")
    evidence: List[str] = Field(..., description="Citations supporting the opportunity.")
    market_signal: str = Field(..., description="Observed external market condition or catalyst.")
    strategic_relevance: str = Field(..., description="Why this opportunity matters competitively.")
    confidence: ConfidenceLevel = Field(..., description="Confidence rating for this opportunity.")


class IntelligenceReport(BaseModel):
    """Executive analytical deliverable synthesizing competitive intelligence."""

    report_id: str = Field(..., description="Unique intelligence report ID.")
    generated_at: str = Field(..., description="ISO timestamp of synthesis generation.")
    trends: List[TrendItem] = Field(default_factory=list, description="Extracted trends and topic frequency over time.")
    competitor_matrix: List[CompetitorTopicComparison] = Field(
        default_factory=list, description="Competitor comparison matrix across core domains."
    )
    risks: List[RiskItem] = Field(default_factory=list, description="Identified competitive and operational risks.")
    opportunities: List[OpportunityItem] = Field(
        default_factory=list, description="Identified strategic market opportunities."
    )
    executive_summary: str = Field(..., description="High-level synthesis for executive leadership.")