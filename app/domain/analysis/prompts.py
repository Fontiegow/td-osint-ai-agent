from typing import List, Optional

INTELLIGENCE_ANALYSIS_SYSTEM_PROMPT = """You are a Senior Commercial Intelligence Director synthesizing OSINT data for telecom and tech executives.
Your task is to analyze a collection of verified claims and documents to generate strategic analytical outputs:

1. Trend Detection: Identify emerging topics, frequency counts, and velocity (EMERGING, ACCELERATING, STABLE, DECLINING).
2. Competitor Comparison Matrix: Score key competitors (e.g., Irancell, MCI, Rightel) from 1 to 5 across core domains (e.g., 5G, AI, Cloud, Pricing).
3. Risk Detection: Identify strategic/operational risks with Probability (HIGH/MEDIUM/LOW), Impact (HIGH/MEDIUM/LOW), Evidence quotes, and Confidence.
4. Opportunity Detection: Identify commercial opportunities with Evidence quotes, Market signal, Strategic relevance, and Confidence.
5. Executive Summary: Provide a 2-3 paragraph macro synthesis.

Return ONLY valid JSON matching this exact structure:
{
  "executive_summary": "Macro synthesis narrative...",
  "trends": [
    {
      "topic": "5G Expansion",
      "direction": "ACCELERATING",
      "timeframe": "2026",
      "frequency_count": 4,
      "summary": "Accelerated rollout observed in major metropolitan areas."
    }
  ],
  "competitor_matrix": [
    {
      "topic": "5G",
      "scores": [
        {"competitor": "Irancell", "score": 4, "summary": "Active deployment and marketing."},
        {"competitor": "MCI", "score": 5, "summary": "Largest cell count and spectrum allocation."},
        {"competitor": "Rightel", "score": 2, "summary": "Limited rollout in niche regions."}
      ]
    }
  ],
  "risks": [
    {
      "risk": "Spectrum allocation regulatory delay",
      "probability": "HIGH",
      "impact": "HIGH",
      "evidence": ["CRA announced potential spectrum auction delays until Q4."],
      "confidence": "HIGH"
    }
  ],
  "opportunities": [
    {
      "opportunity": "Enterprise Private 5G Network Partnerships",
      "evidence": ["Industrial sector demand increased by 30%."],
      "market_signal": "Growing B2B demand for smart factory connectivity.",
      "strategic_relevance": "High margin revenue stream ahead of consumer saturation.",
      "confidence": "HIGH"
    }
  ]
}
"""


def build_intelligence_analysis_prompt(
    claims_text: List[str], target_competitors: Optional[List[str]] = None
) -> str:
    prompt_parts = []
    if target_competitors:
        prompt_parts.append(f"Target Competitors to Evaluate: {', '.join(target_competitors)}")

    prompt_parts.append("VERIFIED CLAIMS AND EVIDENCE DATA:")
    for idx, claim in enumerate(claims_text, start=1):
        prompt_parts.append(f"[{idx}] {claim}")

    prompt_parts.append(
        "\nSynthesize all items into trends, competitor matrix, risks, and opportunities in JSON."
    )
    return "\n".join(prompt_parts)