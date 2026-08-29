from datetime import datetime, timezone
import math
from typing import Dict, List, Optional, Tuple

import pytest

from app.domain.deduplication.pipeline import DeduplicationPipeline, VectorSimilarityProvider
from app.domain.deduplication.schemas import DeduplicationResultType, compute_content_hash
from app.domain.deduplication.store import InMemoryDocumentStore
from app.domain.ingestion.schemas import CanonicalDocument


class FakeVectorStore(VectorSimilarityProvider):
    """In-memory vector store mock for Layer 3 semantic similarity testing."""

    def __init__(self) -> None:
        self.vectors: Dict[str, List[float]] = {}
        self.payloads: Dict[str, dict] = {}
        # Pre-configured text embeddings for deterministic tests
        self.embeddings_db: Dict[str, List[float]] = {}

    def set_mock_embedding(self, text: str, vector: List[float]) -> None:
        """Helper to register exact mock embeddings for text inputs."""
        normalized_key = text.strip().lower()
        self.embeddings_db[normalized_key] = vector

    def compute_embedding(self, text: str) -> List[float]:
        normalized_key = text.strip().lower()
        if normalized_key in self.embeddings_db:
            return self.embeddings_db[normalized_key]
        # Fallback dummy 3D vector for unmapped text
        return [0.1, 0.2, 0.3]

    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    def search_similar(
        self, query_vector: List[float], top_k: int = 1, min_score: float = 0.85
    ) -> List[Tuple[str, float]]:
        matches: List[Tuple[str, float]] = []
        for doc_id, vector in self.vectors.items():
            score = self._cosine_similarity(query_vector, vector)
            if score >= min_score:
                matches.append((doc_id, score))

        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:top_k]

    def index_vector(self, doc_id: str, vector: List[float], payload: dict) -> None:
        self.vectors[doc_id] = vector
        self.payloads[doc_id] = payload


@pytest.fixture
def doc_a() -> CanonicalDocument:
    return CanonicalDocument(
        doc_id="doc_101",
        title="Irancell 5G Network Expansion",
        url="https://news.example.com/tech/irancell-5g",
        source="TechNews",
        published_at=datetime.now(timezone.utc),
        content="Irancell announces new 5G initiative expanding connectivity across major cities.",
    )


@pytest.fixture
def doc_store() -> InMemoryDocumentStore:
    return InMemoryDocumentStore()


# --- Layer 1 Tests: URL Matching ---

def test_l1_duplicate_url_detection(doc_store: InMemoryDocumentStore, doc_a: CanonicalDocument):
    pipeline = DeduplicationPipeline(store=doc_store)
    
    # Process original document
    res1 = pipeline.process_and_index(doc_a)
    assert not res1.is_duplicate
    assert res1.result_type == DeduplicationResultType.UNIQUE

    # Duplicate document with same canonical URL, different content
    doc_b = CanonicalDocument(
        doc_id="doc_102",
        title="Irancell Updates 5G",
        url="https://news.example.com/tech/irancell-5g",
        source="MirrorNews",
        published_at=datetime.now(timezone.utc),
        content="Completely different body text here that is long enough.",
    )

    res2 = pipeline.evaluate(doc_b)
    assert res2.is_duplicate
    assert res2.result_type == DeduplicationResultType.DUPLICATE_URL
    assert res2.match_info is not None
    assert res2.match_info.matched_doc_id == "doc_101"
    assert res2.match_info.similarity_score == 1.0


# --- Layer 2 Tests: Content Hash Matching ---

def test_l2_duplicate_exact_content_hash(doc_store: InMemoryDocumentStore, doc_a: CanonicalDocument):
    pipeline = DeduplicationPipeline(store=doc_store)
    pipeline.process_and_index(doc_a)

    # Secondary document from a different URL with identical text content (varying spaces/casing)
    doc_republished = CanonicalDocument(
        doc_id="doc_103",
        title="Syndicated 5G Post",
        url="https://syndicated.com/irancell-5g-news",
        source="Syndicate",
        published_at=datetime.now(timezone.utc),
        content="IRANCELL announces new 5G initiative   expanding connectivity across major cities.",
    )

    res = pipeline.evaluate(doc_republished)
    assert res.is_duplicate
    assert res.result_type == DeduplicationResultType.DUPLICATE_EXACT_HASH
    assert res.match_info is not None
    assert res.match_info.matched_doc_id == "doc_101"


# --- Layer 3 Tests: Semantic Vector Cosine Similarity ---

def test_l3_duplicate_semantic_similarity(doc_store: InMemoryDocumentStore, doc_a: CanonicalDocument):
    vector_provider = FakeVectorStore()
    pipeline = DeduplicationPipeline(store=doc_store, vector_provider=vector_provider, semantic_threshold=0.90)

    text_a = doc_a.content
    text_b = "Irancell unveiled a new 5G program expanding speed and coverage."

    # Set up vector embeddings (high cosine similarity: ~0.992)
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [0.99, 0.12, 0.0]

    vector_provider.set_mock_embedding(text_a, vec_a)
    vector_provider.set_mock_embedding(text_b, vec_b)

    # Process Doc A
    pipeline.process_and_index(doc_a)

    # Doc B has a different URL and different text (L1 and L2 pass), but semantic similarity is high
    doc_b = CanonicalDocument(
        doc_id="doc_104",
        title="Irancell Unveils 5G Program",
        url="https://alternative-outlet.org/news/5g-program",
        source="AltNews",
        published_at=datetime.now(timezone.utc),
        content=text_b,
    )

    res = pipeline.evaluate(doc_b)
    assert res.is_duplicate
    assert res.result_type == DeduplicationResultType.DUPLICATE_SEMANTIC
    assert res.match_info is not None
    assert res.match_info.matched_doc_id == "doc_101"
    assert res.match_info.similarity_score >= 0.90


def test_unique_document_passes_all_layers(doc_store: InMemoryDocumentStore, doc_a: CanonicalDocument):
    vector_provider = FakeVectorStore()
    pipeline = DeduplicationPipeline(store=doc_store, vector_provider=vector_provider, semantic_threshold=0.90)

    text_a = doc_a.content
    text_unrelated = "Cybersecurity threat report details new ransomware strain targeting industrial devices."

    vector_provider.set_mock_embedding(text_a, [1.0, 0.0, 0.0])
    vector_provider.set_mock_embedding(text_unrelated, [0.0, 1.0, 0.0])  # Orthogonal vector (similarity 0.0)

    pipeline.process_and_index(doc_a)

    doc_unrelated = CanonicalDocument(
        doc_id="doc_105",
        title="Ransomware Threat Intelligence",
        url="https://cybersec.io/reports/ransomware",
        source="CyberSec",
        published_at=datetime.now(timezone.utc),
        content=text_unrelated,
    )

    res = pipeline.process_and_index(doc_unrelated)
    assert not res.is_duplicate
    assert res.result_type == DeduplicationResultType.UNIQUE
    assert doc_store.count() == 2