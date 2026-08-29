import pytest
from app.domain.analysis.schemas import (
    ConfidenceLevel,
    ImpactLevel,
    ProbabilityLevel,
    TrendDirection,
)
from app.domain.analysis.service import IntelligenceAnalyzer


class MockLLMGateway:

    def __init__(self, response_json: str):
        self.response_json = response_json

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return self.response_json


def test_intelligence_analyzer_successful_report():
    mock_json = """
    {
      "executive_summary": "Irancell leads 5G rollout, while MCI invests heavily in AI infrastructure.",
      "trends": [
        {
          "topic": "5G",
          "direction": "ACCELERATING",
          "timeframe": "2026",
          "frequency_count": 5,
          "summary": "Rapid site deployment across urban hubs."
        }
      ],
      "competitor_matrix": [
        {
          "topic": "5G",
          "scores": [
            {"competitor": "Irancell", "score": 3, "summary": "Solid progress"},
            {"competitor": "MCI", "score": 4, "summary": "Leading coverage"},
            {"competitor": "Rightel", "score": 2, "summary": "Niche deployment"}
          ]
        },
        {
          "topic": "AI",
          "scores": [
            {"competitor": "Irancell", "score": 4, "summary": "Active AI integration"},
            {"competitor": "MCI", "score": 2, "summary": "Early exploratory phase"},
            {"competitor": "Rightel", "score": 1, "summary": "No active projects"}
          ]
        }
      ],
      "risks": [
        {
          "risk": "Regulatory delay in 5G spectrum",
          "probability": "HIGH",
          "impact": "HIGH",
          "evidence": ["Regulator postponed spectrum auctions."],
          "confidence": "HIGH"
        }
      ],
      "opportunities": [
        {
          "opportunity": "Enterprise Private 5G networks",
          "evidence": ["High demand from manufacturing plants."],
          "market_signal": "Growing enterprise automation focus.",
          "strategic_relevance": "Uncapped B2B revenue potential.",
          "confidence": "HIGH"
        }
      ]
    }
    """

    analyzer = IntelligenceAnalyzer(llm_gateway=MockLLMGateway(mock_json))
    claims = [
        "Irancell deployed 500 new 5G towers in early 2026.",
        "MCI announced $20M AI data center partnership.",
        "Rightel focuses on affordable pricing plans.",
    ]

    report = analyzer.analyze(
        verified_claims=claims,
        target_competitors=["Irancell", "MCI", "Rightel"],
        report_id="REP-TEST-101",
    )

    assert report.report_id == "REP-TEST-101"
    assert "Irancell leads 5G rollout" in report.executive_summary

    # Trend check
    assert len(report.trends) == 1
    assert report.trends[0].topic == "5G"
    assert report.trends[0].direction == TrendDirection.ACCELERATING

    # Competitor Matrix check
    assert len(report.competitor_matrix) == 2
    matrix_5g = report.competitor_matrix[0]
    assert matrix_5g.topic == "5G"
    scores_dict = {s.competitor: s.score for s in matrix_5g.scores}
    assert scores_dict["Irancell"] == 3
    assert scores_dict["MCI"] == 4
    assert scores_dict["Rightel"] == 2

    # Risk check
    assert len(report.risks) == 1
    assert report.risks[0].probability == ProbabilityLevel.HIGH
    assert report.risks[0].impact == ImpactLevel.HIGH

    # Opportunity check
    assert len(report.opportunities) == 1
    assert report.opportunities[0].confidence == ConfidenceLevel.HIGH


def test_intelligence_analyzer_empty_input_fallback():
    analyzer = IntelligenceAnalyzer(llm_gateway=MockLLMGateway("{}"))
    report = analyzer.analyze(verified_claims=[])

    assert len(report.trends) == 0
    assert len(report.competitor_matrix) == 0
    assert "Insufficient data" in report.executive_summary