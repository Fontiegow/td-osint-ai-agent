from typing import Optional

CLAIM_EXTRACTION_SYSTEM_PROMPT = """You are an expert intelligence analyst specializing in telecom and technology media evaluation.
Your task is to extract all discrete, verifiable claims from the provided document text.

Extraction Rules:
1. Atomic Claims: Each claim must represent a single, self-contained statement of fact, projection, announcement, or opinion.
2. Source Span Integrity: The `source_span` MUST be an exact, verbatim quote taken directly from the provided text supporting the claim. Do not rephrase `source_span`.
3. Entity Linking: Extract key organization names, tech terms, or decision-makers mentioned in the claim.
4. Temporal Reference: Extract any explicit timeframe (e.g., "2026", "H1 2025", "by end of decade") associated with the claim.

Return ONLY valid JSON matching this structure:
{
  "claims": [
    {
      "text": "Irancell has expanded 5G coverage across major urban centers.",
      "type": "factual",
      "entities": ["Irancell", "5G"],
      "temporal_reference": "2026",
      "source_span": "Irancell expanded its 5G network footprint across major urban centers in early 2026."
    }
  ]
}
"""


def build_claim_extraction_user_prompt(text: str, title: Optional[str] = None) -> str:
    prompt_parts = []
    if title:
        prompt_parts.append(f"Document Title: {title}")
    prompt_parts.append(f"Document Text:\n{text}\n")
    prompt_parts.append("Extract all core claims following the JSON format strictly.")
    return "\n".join(prompt_parts)
