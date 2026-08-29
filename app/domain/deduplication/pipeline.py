import logging
from typing import List, Optional, Protocol

from app.domain.deduplication.schemas import (
    DeduplicationResult,
    DeduplicationResultType,
)
from app.domain.deduplication.store import InMemoryDocumentStore
from app.domain.ingestion.schemas import CanonicalDocument

logger = logging.getLogger(__name__)


class VectorSimilarityProvider(Protocol):
    """Protocol interface for generating embeddings and finding semantically similar documents."""

    def compute_embedding(self, text: str) -> List[float]:
        """Generates a dense vector embedding for a given text."""
        ...

    def search_similar(
        self, query_vector: List[float], top_k: int = 1, min_score: float = 0.85
    ) -> List[tuple[str, float]]:
        """
        Searches the vector store for similar document IDs.
        
        :return: List of tuples containing (doc_id, cosine_similarity_score)
        """
        ...

    def index_vector(self, doc_id: str, vector: List[float], payload: dict) -> None:
        """Indexes document vector and metadata into vector storage."""
        ...


class DeduplicationPipeline:
    """
    3-Layer Document Deduplication Pipeline:
      - Layer 1: Canonical URL exact match check (O(1))
      - Layer 2: Normalized Content Hash match check (O(1))
      - Layer 3: Dense Vector Cosine Similarity check (Embedding + Vector Search)
    """

    def __init__(
        self,
        store: InMemoryDocumentStore,
        vector_provider: Optional[VectorSimilarityProvider] = None,
        semantic_threshold: float = 0.90,
    ) -> None:
        self.store = store
        self.vector_provider = vector_provider
        self.semantic_threshold = semantic_threshold

    def evaluate(self, doc: CanonicalDocument) -> DeduplicationResult:
        """
        Evaluates an inbound CanonicalDocument through all 3 deduplication layers.
        Returns a DeduplicationResult indicating whether it is unique or a duplicate.
        """
        # --- Layer 1: Canonical URL Matching ---
        url_match_id = self.store.exists_by_url(doc.url)
        if url_match_id:
            logger.info("L1 DUPLICATE [URL]: Doc '%s' matches existing doc '%s'", doc.doc_id, url_match_id)
            return DeduplicationResult.duplicate(
                doc=doc,
                match_type=DeduplicationResultType.DUPLICATE_URL,
                matched_doc_id=url_match_id,
                score=1.0,
                details=f"Exact match on canonical URL: {doc.url}",
            )

        # --- Layer 2: Exact Content Hash Matching ---
        hash_match_id = self.store.exists_by_content_hash(doc.content)
        if hash_match_id:
            logger.info("L2 DUPLICATE [HASH]: Doc '%s' matches existing doc '%s'", doc.doc_id, hash_match_id)
            return DeduplicationResult.duplicate(
                doc=doc,
                match_type=DeduplicationResultType.DUPLICATE_EXACT_HASH,
                matched_doc_id=hash_match_id,
                score=1.0,
                details="Exact match on normalized content SHA-256 hash",
            )

        # --- Layer 3: Vector Semantic Cosine Similarity ---
        if self.vector_provider:
            try:
                vector = self.vector_provider.compute_embedding(doc.content)
                matches = self.vector_provider.search_similar(
                    query_vector=vector,
                    top_k=1,
                    min_score=self.semantic_threshold,
                )
                if matches:
                    matched_doc_id, score = matches[0]
                    logger.info(
                        "L3 DUPLICATE [SEMANTIC]: Doc '%s' matches existing doc '%s' (score: %.4f)",
                        doc.doc_id,
                        matched_doc_id,
                        score,
                    )
                    return DeduplicationResult.duplicate(
                        doc=doc,
                        match_type=DeduplicationResultType.DUPLICATE_SEMANTIC,
                        matched_doc_id=matched_doc_id,
                        score=score,
                        details=f"Cosine similarity ({score:.4f}) >= threshold ({self.semantic_threshold})",
                    )
            except Exception as e:
                logger.warning("Layer 3 semantic vector check failed for doc '%s': %s", doc.doc_id, e)

        # --- Unique Document ---
        logger.debug("Doc '%s' passed all deduplication layers and is UNIQUE", doc.doc_id)
        return DeduplicationResult.unique(doc)

    def process_and_index(self, doc: CanonicalDocument) -> DeduplicationResult:
        """
        Evaluates the document for duplicates.
        If UNIQUE, stores and indexes it across all lookup layers.
        """
        result = self.evaluate(doc)
        if not result.is_duplicate:
            # Add to Layer 1 & 2 in-memory store
            self.store.add(doc)

            # Index in Layer 3 vector store if available
            if self.vector_provider:
                try:
                    vector = self.vector_provider.compute_embedding(doc.content)
                    self.vector_provider.index_vector(
                        doc_id=doc.doc_id,
                        vector=vector,
                        payload={"url": doc.url, "title": doc.title, "source": doc.source},
                    )
                except Exception as e:
                    logger.error("Failed to index vector for doc '%s': %s", doc.doc_id, e)

        return result