import pytest
from unittest.mock import AsyncMock
from app.domain.classification.schemas import (
    DocumentClassification,
    EventType,
)
from app.domain.classification.service import DocumentClassifier
from app.domain.ingestion.schemas import CanonicalDocument


def test_document_classification_schema_validation():
    data = {
        "brand": "Irancell",
        "topics": ["5G", "Network ", " INVESTMENT"],
        "event_type": "technology",
        "sentiment": "neutral",
        "importance": 0.82,
    }
    classification = DocumentClassification(**data)

    assert classification.brand == "Irancell"
    assert classification.event_type == EventType.TECHNOLOGY
    assert classification.sentiment == "neutral"
    assert classification.importance == 0.82
    assert "5g" in classification.topics
    assert "network" in classification.topics
    assert "investment" in classification.topics


@pytest.mark.asyncio
async def test_document_classifier_service_success():
    mock_llm_gateway = AsyncMock()
    mock_llm_gateway.generate.return_value = """
    {
        "brand": "Irancell",
        "topics": ["5G", "network", "investment"],
        "event_type": "technology",
        "sentiment": "neutral",
        "importance": 0.82
    }
    """

    classifier = DocumentClassifier(llm_gateway=mock_llm_gateway)
    doc = CanonicalDocument(
        doc_id="doc_123",
        title="Irancell expands 5G coverage with $50M investment",
        url="[https://example.com/news/1](https://example.com/news/1)",
        source="TechNews",
        content="Irancell announced today a major strategic investment in 5G infrastructure.",
    )

    result = await classifier.classify_document(doc)

    assert result.doc_id == "doc_123"
    assert result.classification.brand == "Irancell"
    assert result.classification.event_type == EventType.TECHNOLOGY
    assert result.classification.importance == 0.82
    assert "5g" in result.classification.topics


@pytest.mark.asyncio
async def test_document_classifier_service_fallback_on_error():
    mock_llm_gateway = AsyncMock()
    mock_llm_gateway.generate.side_effect = Exception("LLM Provider Timeout")

    classifier = DocumentClassifier(llm_gateway=mock_llm_gateway)
    doc = CanonicalDocument(
        doc_id="doc_456",
        title="Sample News",
        url="[https://example.com/news/2](https://example.com/news/2)",
        source="NewsSource",
        content="Some raw news content without proper formatting.",
    )

    result = await classifier.classify_document(doc)

    assert result.doc_id == "doc_456"
    assert result.classification.brand == "NewsSource"
    assert result.classification.event_type == EventType.OTHER
    assert result.classification.importance == 0.5