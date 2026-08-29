"""Deduplication domain package containing schemas, in-memory store, and multi-layer pipeline."""

from app.domain.deduplication.pipeline import DeduplicationPipeline
from app.domain.deduplication.schemas import (
    DeduplicationResult,
    DeduplicationResultType,
    DuplicateMatchInfo,
    compute_content_hash,
)
from app.domain.deduplication.store import InMemoryDocumentStore

__all__ = [
    "DeduplicationPipeline",
    "DeduplicationResult",
    "DeduplicationResultType",
    "DuplicateMatchInfo",
    "InMemoryDocumentStore",
    "compute_content_hash",
]