import json
import logging
from typing import Any, Dict, List, Optional
from app.domain.extraction.schemas import ClaimExtractionResponse, ExtractedClaim
from app.domain.extraction.prompts import (
    CLAIM_EXTRACTION_SYSTEM_PROMPT,
    build_claim_extraction_user_prompt,
)

logger = logging.getLogger(__name__)


class ClaimExtractor:

    def __init__(self, llm_gateway: Any):
        """
        llm_gateway must implement complete(system_prompt, user_prompt) -> str
        """
        self.llm_gateway = llm_gateway

    def extract_claims(self, text: str, title: Optional[str] = None) -> ClaimExtractionResponse:
        """
        Extracts atomic claims from raw text and validates verbatim source spans.
        """
        if not text or not text.strip():
            return ClaimExtractionResponse(claims=[])

        user_prompt = build_claim_extraction_user_prompt(text=text, title=title)

        try:
            raw_response = self.llm_gateway.complete(
                system_prompt=CLAIM_EXTRACTION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            parsed_data = self._parse_json(raw_response)
            extracted = ClaimExtractionResponse.model_validate(parsed_data)

            # Validate that source spans exist within the original document text
            validated_claims = []
            for claim in extracted.claims:
                if claim.source_span and claim.source_span in text:
                    validated_claims.append(claim)
                else:
                    logger.warning(
                        "Source span not exact match in text. Keeping claim but logging mismatch: '%s'",
                        claim.source_span
                    )
                    validated_claims.append(claim)

            return ClaimExtractionResponse(claims=validated_claims)

        except Exception as exc:
            logger.error("Failed to extract claims: %s", exc, exc_info=True)
            return ClaimExtractionResponse(claims=[])

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