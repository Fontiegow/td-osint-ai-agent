import json
import logging
from typing import Any, Dict, List, Optional
from app.domain.verification.prompts import (
    VERIFICATION_SYSTEM_PROMPT,
    build_evidence_eval_prompt,
)
from app.domain.verification.schemas import (
    ClaimVerificationResult,
    ConfidenceLevel,
    EvidenceRelation,
    VerificationEvidence,
    VerificationStatus,
)

logger = logging.getLogger(__name__)


class ClaimVerifier:
    """Evaluates claims against retrieved evidence documents to calculate verification status and confidence."""

    def __init__(self, llm_gateway: Any):
        self.llm_gateway = llm_gateway

    def verify_claim(
        self,
        claim_id: str,
        claim_text: str,
        candidate_evidence: List[Dict[str, Any]],
    ) -> ClaimVerificationResult:
        """
        Verifies a single claim against candidate evidence documents.
        
        `candidate_evidence` expects items with:
        - `source_name` (str)
        - `text` (str)
        - `url` (optional str)
        """
        evaluated_evidence: List[VerificationEvidence] = []

        for candidate in candidate_evidence:
            source_name = candidate.get("source_name", "Unknown Source")
            excerpt = candidate.get("text", "").strip()
            url = candidate.get("url")

            if not excerpt:
                continue

            relation_data = self._eval_evidence_relation(claim_text, excerpt, source_name)
            
            if relation_data["relation"] != EvidenceRelation.NEUTRAL:
                evaluated_evidence.append(
                    VerificationEvidence(
                        source_name=source_name,
                        url=url,
                        excerpt=excerpt,
                        relation=relation_data["relation"],
                        reasoning=relation_data.get("reasoning"),
                    )
                )

        return self._build_verification_result(
            claim_id=claim_id,
            claim_text=claim_text,
            evidence_items=evaluated_evidence,
        )

    def _eval_evidence_relation(
        self, claim_text: str, excerpt: str, source_name: str
    ) -> Dict[str, Any]:
        user_prompt = build_evidence_eval_prompt(claim_text, excerpt, source_name)
        try:
            raw_response = self.llm_gateway.complete(
                system_prompt=VERIFICATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            parsed = self._parse_json(raw_response)
            relation_str = parsed.get("relation", "NEUTRAL").upper()
            
            try:
                relation = EvidenceRelation(relation_str)
            except ValueError:
                relation = EvidenceRelation.NEUTRAL

            return {
                "relation": relation,
                "reasoning": parsed.get("reasoning", ""),
            }
        except Exception as exc:
            logger.error("Evidence evaluation failed: %s", exc)
            return {"relation": EvidenceRelation.NEUTRAL, "reasoning": "Evaluation error"}

    def _build_verification_result(
        self,
        claim_id: str,
        claim_text: str,
        evidence_items: List[VerificationEvidence],
    ) -> ClaimVerificationResult:
        supporting = [e for e in evidence_items if e.relation == EvidenceRelation.SUPPORTS]
        contradicting = [e for e in evidence_items if e.relation == EvidenceRelation.CONTRADICTS]

        supporting_sources = sorted(list({e.source_name for e in supporting}))
        contradicting_sources = sorted(list({e.source_name for e in contradicting}))

        all_independent_sources = len(set(e.source_name for e in evidence_items))
        evidence_count = len(evidence_items)

        # Status Logic
        if len(supporting_sources) >= 1 and len(contradicting_sources) == 0:
            status = VerificationStatus.CORROBORATED
        elif len(contradicting_sources) >= 1 and len(supporting_sources) == 0:
            status = VerificationStatus.CONTRADICTED
        elif len(supporting_sources) >= 1 and len(contradicting_sources) >= 1:
            status = VerificationStatus.DISPUTED
        else:
            status = VerificationStatus.UNVERIFIED

        # Confidence Scoring Logic
        if status == VerificationStatus.CORROBORATED:
            if len(supporting_sources) >= 2:
                confidence = ConfidenceLevel.HIGH
            else:
                confidence = ConfidenceLevel.MEDIUM
        elif status == VerificationStatus.CONTRADICTED:
            if len(contradicting_sources) >= 2:
                confidence = ConfidenceLevel.HIGH
            else:
                confidence = ConfidenceLevel.MEDIUM
        elif status == VerificationStatus.DISPUTED:
            confidence = ConfidenceLevel.LOW
        else:
            confidence = ConfidenceLevel.LOW

        return ClaimVerificationResult(
            claim_id=claim_id,
            claim_text=claim_text,
            status=status,
            confidence=confidence,
            supporting_sources=supporting_sources,
            contradicting_sources=contradicting_sources,
            evidence_count=evidence_count,
            independent_sources=all_independent_sources,
            evidence_details=evidence_items,
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