import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from app.domain.analysis.prompts import (
    INTELLIGENCE_ANALYSIS_SYSTEM_PROMPT,
    build_intelligence_analysis_prompt,
)
from app.domain.analysis.schemas import (
    CompetitorScore,
    CompetitorTopicComparison,
    ConfidenceLevel,
    ImpactLevel,
    IntelligenceReport,
    OpportunityItem,
    ProbabilityLevel,
    RiskItem,
    TrendDirection,
    TrendItem,
)

logger = logging.getLogger(__name__)


class IntelligenceAnalyzer:
    """Orchestrates multi-source claim and document synthesis into executive intelligence outputs."""

    def __init__(self, llm_gateway: Any):
        self.llm_gateway = llm_gateway

    def analyze(
        self,
        verified_claims: List[Dict[str, Any]],
        target_competitors: Optional[List[str]] = None,
        report_id: Optional[str] = None,
    ) -> IntelligenceReport:
        """
        Synthesizes a list of verified claims into an IntelligenceReport.
        `verified_claims` can contain string items or dicts with 'claim_text' / 'text'.
        """
        claims_text = []
        for item in verified_claims:
            if isinstance(item, str):
                claims_text.append(item)
            elif isinstance(item, dict):
                claims_text.append(item.get("claim_text") or item.get("text") or str(item))

        if not claims_text:
            return self._build_empty_report(report_id)

        user_prompt = build_intelligence_analysis_prompt(claims_text, target_competitors)

        try:
            raw_response = self.llm_gateway.complete(
                system_prompt=INTELLIGENCE_ANALYSIS_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            parsed = self._parse_json(raw_response)
            return self._build_intelligence_report(parsed, report_id)
        except Exception as exc:
            logger.error("Intelligence synthesis failed: %s", exc)
            return self._build_empty_report(report_id, fallback_summary="Analysis generation encountered an error.")

    def _build_intelligence_report(
        self, parsed: Dict[str, Any], report_id: Optional[str]
    ) -> IntelligenceReport:
        report_id = report_id or f"REP-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()

        # Parse Trends
        trends = []
        for t in parsed.get("trends", []):
            try:
                direction = TrendDirection(t.get("direction", "STABLE").upper())
            except ValueError:
                direction = TrendDirection.STABLE

            trends.append(
                TrendItem(
                    topic=t.get("topic", "General"),
                    direction=direction,
                    timeframe=str(t.get("timeframe", "Current")),
                    frequency_count=int(t.get("frequency_count", 1)),
                    summary=t.get("summary", ""),
                )
            )

        # Parse Competitor Matrix
        competitor_matrix = []
        for comp_topic in parsed.get("competitor_matrix", []):
            scores = []
            for score_entry in comp_topic.get("scores", []):
                scores.append(
                    CompetitorScore(
                        competitor=score_entry.get("competitor", "Unknown"),
                        score=max(1, min(5, int(score_entry.get("score", 3)))),
                        summary=score_entry.get("summary", ""),
                    )
                )
            competitor_matrix.append(
                CompetitorTopicComparison(
                    topic=comp_topic.get("topic", "General"),
                    scores=scores,
                )
            )

        # Parse Risks
        risks = []
        for r in parsed.get("risks", []):
            risks.append(
                RiskItem(
                    risk=r.get("risk", "Unclassified Risk"),
                    probability=self._parse_enum(ProbabilityLevel, r.get("probability"), ProbabilityLevel.MEDIUM),
                    impact=self._parse_enum(ImpactLevel, r.get("impact"), ImpactLevel.MEDIUM),
                    evidence=r.get("evidence", []),
                    confidence=self._parse_enum(ConfidenceLevel, r.get("confidence"), ConfidenceLevel.MEDIUM),
                )
            )

        # Parse Opportunities
        opportunities = []
        for o in parsed.get("opportunities", []):
            opportunities.append(
                OpportunityItem(
                    opportunity=o.get("opportunity", "Unclassified Opportunity"),
                    evidence=o.get("evidence", []),
                    market_signal=o.get("market_signal", ""),
                    strategic_relevance=o.get("strategic_relevance", ""),
                    confidence=self._parse_enum(ConfidenceLevel, o.get("confidence"), ConfidenceLevel.MEDIUM),
                )
            )

        return IntelligenceReport(
            report_id=report_id,
            generated_at=now_iso,
            trends=trends,
            competitor_matrix=competitor_matrix,
            risks=risks,
            opportunities=opportunities,
            executive_summary=parsed.get("executive_summary", "No summary provided."),
        )

    def _parse_enum(self, enum_cls: Any, val: Any, default: Any) -> Any:
        if not val:
            return default
        try:
            return enum_cls(str(val).upper())
        except ValueError:
            return default

    def _build_empty_report(
        self, report_id: Optional[str] = None, fallback_summary: str = "Insufficient data to perform intelligence analysis."
    ) -> IntelligenceReport:
        report_id = report_id or f"REP-{uuid.uuid4().hex[:8].upper()}"
        return IntelligenceReport(
            report_id=report_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            trends=[],
            competitor_matrix=[],
            risks=[],
            opportunities=[],
            executive_summary=fallback_summary,
        )

    def _parse_json(self, raw_response: str) -> Dict[str, Any]:
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned.removeprefix("```json")
        elif cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```")
        if cleaned.endswith("```"):
            cleaned = cleaned.removesuffix("```")
        cleaned = cleaned.strip()
        return json.loads(cleaned)