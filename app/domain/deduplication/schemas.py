import hashlib
import re
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from app.domain.ingestion.schemas import CanonicalDocument


class DeduplicationResultType(str, Enum):
    UNIQUE = "UNIQUE"
    DUPLICATE_URL = "DUPLICATE_URL"
    DUPLICATE_EXACT_HASH = "DUPLICATE_EXACT_HASH"
    DUPLICATE_SEMANTIC = "DUPLICATE_SEMANTIC"


class DuplicateMatchInfo(BaseModel):
    matched_doc_id: str
    match_layer: DeduplicationResultType
    similarity_score: float = Field(
        default=1.0, ge=0.0, le=1.0, description="1.0 for exact URL/hash, cosine score for semantic"
    )
    details: Optional[str] = None


class DeduplicationResult(BaseModel):
    is_duplicate: bool
    result_type: DeduplicationResultType
    document: CanonicalDocument
    match_info: Optional[DuplicateMatchInfo] = None

    @classmethod
    def unique(cls, doc: CanonicalDocument) -> "DeduplicationResult":
        return cls(
            is_duplicate=False,
            result_type=DeduplicationResultType.UNIQUE,
            document=doc,
            match_info=None,
        )

    @classmethod
    def duplicate(
        cls,
        doc: CanonicalDocument,
        match_type: DeduplicationResultType,
        matched_doc_id: str,
        score: float = 1.0,
        details: Optional[str] = None,
    ) -> "DeduplicationResult":
        return cls(
            is_duplicate=True,
            result_type=match_type,
            document=doc,
            match_info=DuplicateMatchInfo(
                matched_doc_id=matched_doc_id,
                match_layer=match_type,
                similarity_score=score,
                details=details,
            ),
        )


def compute_content_hash(text: str) -> str:
    """Computes a normalized SHA-256 hash of document text ignoring spaces and casing."""
    normalized = re.sub(r"\s+", "", text.strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()