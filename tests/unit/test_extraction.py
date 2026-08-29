import pytest
from app.domain.extraction.schemas import ClaimExtractionResponse, ClaimType, ExtractedClaim
from app.domain.extraction.service import ClaimExtractor


class MockLLMGateway:

    def __init__(self, response_text: str):
        self.response_text = response_text

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return self.response_text


def test_extracted_claim_schema_valid():
    claim = ExtractedClaim(
        text="Irancell launched new 5G towers in 2026.",
        type=ClaimType.FACTUAL,
        entities=["Irancell", "5G"],
        temporal_reference="2026",
        source_span="Irancell launched new 5G towers in 2026."
    )
    assert claim.type == ClaimType.FACTUAL
    assert claim.temporal_reference == "2026"
    assert len(claim.entities) == 2


def test_claim_extractor_service_success():
    sample_text = (
        "Irancell expanded its 5G network footprint across major urban centers in early 2026. "
        "The company expects network traffic to grow by 40% by Q4."
    )

    mock_json = """
    {
      "claims": [
        {
          "text": "Irancell expanded its 5G network footprint across major urban centers.",
          "type": "factual",
          "entities": ["Irancell", "5G"],
          "temporal_reference": "early 2026",
          "source_span": "Irancell expanded its 5G network footprint across major urban centers in early 2026."
        },
        {
          "text": "Network traffic is projected to increase by 40%.",
          "type": "projection",
          "entities": ["Irancell"],
          "temporal_reference": "Q4",
          "source_span": "The company expects network traffic to grow by 40% by Q4."
        }
      ]
    }
    """

    llm_gateway = MockLLMGateway(response_text=mock_json)
    extractor = ClaimExtractor(llm_gateway=llm_gateway)

    result = extractor.extract_claims(text=sample_text, title="Irancell Network Update")

    assert isinstance(result, ClaimExtractionResponse)
    assert len(result.claims) == 2
    assert result.claims[0].type == ClaimType.FACTUAL
    assert result.claims[0].source_span in sample_text
    assert result.claims[1].type == ClaimType.PROJECTION


def test_claim_extractor_fallback_on_invalid_json():
    llm_gateway = MockLLMGateway(response_text="Invalid LLM JSON response")
    extractor = ClaimExtractor(llm_gateway=llm_gateway)

    result = extractor.extract_claims(text="Some valid input text")
    assert isinstance(result, ClaimExtractionResponse)
    assert len(result.claims) == 0