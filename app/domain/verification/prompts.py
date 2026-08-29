from typing import Optional

VERIFICATION_SYSTEM_PROMPT = """You are an expert Intelligence Verification Analyst.
Your job is to compare a TARGET CLAIM against a candidate text passage and determine whether the passage SUPPORTS, CONTRADICTS, or is NEUTRAL towards the claim.

Evaluation Rules:
1. SUPPORTS: The passage explicitly agrees with or provides direct evidence for the core assertion of the claim.
2. CONTRADICTS: The passage directly refutes, denies, or presents conflicting facts against the claim.
3. NEUTRAL: The passage is ambiguous, uninformative, or unrelated to the specific claim.

Return ONLY valid JSON in this exact structure:
{
  "relation": "SUPPORTS | CONTRADICTS | NEUTRAL",
  "reasoning": "Brief explanation of why this passage supports, contradicts, or is neutral towards the claim."
}
"""


def build_evidence_eval_prompt(claim_text: str, source_text: str, source_name: Optional[str] = None) -> str:
    prompt_parts = []
    if source_name:
        prompt_parts.append(f"Source: {source_name}")
    prompt_parts.append(f"TARGET CLAIM: {claim_text}")
    prompt_parts.append(f"CANDIDATE PASSAGE: {source_text}")
    prompt_parts.append("Evaluate the relation and respond strictly in JSON.")
    return "\n".join(prompt_parts)