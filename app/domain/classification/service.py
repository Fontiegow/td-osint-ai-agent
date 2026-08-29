import json
import logging
from typing import Optional
from app.domain.classification.prompts import (
    SYSTEM_CLASSIFICATION_PROMPT,
    USER_CLASSIFICATION_PROMPT,
)
from app.domain.classification.schemas import (
    ClassifiedDocument,
    DocumentClassification,
)
from app.domain.ingestion.schemas import CanonicalDocument
from app.domain.llm.gateway import LLMGateway

logger = logging.getLogger(__name__)


class DocumentClassifier:
    """Service to classify documents into strategic management intelligence metadata."""

    def __init__(self, llm_gateway: LLMGateway):
        self.llm_gateway = llm_gateway

    async def classify_document(
        self, doc: CanonicalDocument, provider: Optional[str] = None
    ) -> ClassifiedDocument:
        """Classifies a CanonicalDocument and returns a ClassifiedDocument."""
        prompt = USER_CLASSIFICATION_PROMPT.format(
            title=doc.title,
            source=doc.source,
            content=doc.content[:2000],  # Truncate content for efficiency
        )

        try:
            response_text = await self.llm_gateway.generate(
                prompt=prompt,
                system_prompt=SYSTEM_CLASSIFICATION_PROMPT,
                provider=provider,
                temperature=0.1,
            )

            classification = self._parse_llm_response(response_text)
        except Exception as exc:
            logger.error(f"Classification failed for doc_id {doc.doc_id}: {exc}")
            # Fallback classification on failure
            classification = DocumentClassification(
                brand=doc.source or "Unknown",
                topics=[],
                event_type="other",
                sentiment="neutral",
                importance=0.5,
            )

        return ClassifiedDocument(
            doc_id=doc.doc_id,
            classification=classification,
        )

    def _parse_llm_response(self, raw_response: str) -> DocumentClassification:
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        data = json.loads(cleaned.strip())
        return DocumentClassification(**data)