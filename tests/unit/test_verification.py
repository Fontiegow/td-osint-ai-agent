import pytest
from app.domain.verification.schemas import (
    ClaimVerificationResult,
    ConfidenceLevel,
    EvidenceRelation,
    VerificationStatus,
)
from app.domain.verification.service import ClaimVerifier


class MockLLMGateway:

    def __init__(self, responses: list):
        self.responses = responses
        self.call_count = 0

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        res = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return res


def test_claim_verification_corroborated_high_confidence():
    candidate_evidence = [
        {
            "source_name": "Official company",
            "text": "Irancell confirmed a major $50M investment in 5G expansion.",
            "url": "https://irancell.ir/news/1",
        },
        {
            "source_name": "News organization",
            "text": "Industry reports show Irancell invested heavily into 5G.",
            "url": "https://reuters.com/news/2",
        },
    ]

    llm_responses = [
        '{"relation": "SUPPORTS", "reasoning": "Explicit agreement with 5G investment."}',
        '{"relation": "SUPPORTS", "reasoning": "Corroborates 5G investment claim."}',
    ]

    gateway = MockLLMGateway(llm_responses)
    verifier = ClaimVerifier(llm_gateway=gateway)

    result = verifier.verify_claim(
        claim_id="C-1024",
        claim_text="Irancell invested in 5G network expansion.",
        candidate_evidence=candidate_evidence,
    )

    assert result.claim_id == "C-1024"
    assert result.status == VerificationStatus.CORROBORATED
    assert result.confidence == ConfidenceLevel.HIGH
    assert len(result.supporting_sources) == 2
    assert "Official company" in result.supporting_sources
    assert "News organization" in result.supporting_sources
    assert result.evidence_count == 2
    assert result.independent_sources == 2


def test_claim_verification_disputed_when_contradicted():
    candidate_evidence = [
        {
            "source_name": "Official company",
            "text": "Irancell expands 5G footprint.",
            "url": "https://irancell.ir/news/1",
        },
        {
            "source_name": "Regulatory agency",
            "text": "Regulators denied 5G license expansion to Irancell.",
            "url": "https://cra.ir/news/3",
        },
    ]

    llm_responses = [
        '{"relation": "SUPPORTS", "reasoning": "States expansion happening."}',
        '{"relation": "CONTRADICTS", "reasoning": "States license expansion denied."}',
    ]

    gateway = MockLLMGateway(llm_responses)
    verifier = ClaimVerifier(llm_gateway=gateway)

    result = verifier.verify_claim(
        claim_id="C-1025",
        claim_text="Irancell expanded 5G network.",
        candidate_evidence=candidate_evidence,
    )

    assert result.status == VerificationStatus.DISPUTED
    assert result.confidence == ConfidenceLevel.LOW
    assert len(result.supporting_sources) == 1
    assert len(result.contradicting_sources) == 1


def test_claim_verification_unverified_when_no_evidence():
    gateway = MockLLMGateway([])
    verifier = ClaimVerifier(llm_gateway=gateway)

    result = verifier.verify_claim(
        claim_id="C-1026",
        claim_text="Irancell purchased satellite provider.",
        candidate_evidence=[],
    )

    assert result.status == VerificationStatus.UNVERIFIED
    assert result.confidence == ConfidenceLevel.LOW
    assert result.evidence_count == 0
    assert result.independent_sources == 0