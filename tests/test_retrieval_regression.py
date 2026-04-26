from __future__ import annotations

import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from neurvinch.models import DocumentChunk, SourceMetadata
from neurvinch.retrieval import HybridRetriever


class TestHybridRetrieverRegression(unittest.TestCase):
    def test_catalog_file_is_demoted_below_specific_doc(self) -> None:
        chunks = [
            DocumentChunk(
                id="specific-auth-doc",
                text="GitHub REST API authentication uses bearer tokens in the Authorization header.",
                metadata=SourceMetadata(path="data/kb/external/github_rest_api_docs_curated.md", section="Authentication"),
            ),
            DocumentChunk(
                id="catalog-overview",
                text="This external docs catalog includes GitHub API, Python docs, and React docs.",
                metadata=SourceMetadata(path="data/kb/external/external_docs_catalog.md", section="Catalog"),
            ),
            DocumentChunk(
                id="noise-doc",
                text="Boto3 includes paginators and waiters for AWS service workflows.",
                metadata=SourceMetadata(path="data/kb/external/boto3_docs_curated.md", section="Core Concepts"),
            ),
        ]

        retriever = HybridRetriever(
            embedding_model_name="sentence-transformers/all-MiniLM-L6-v2",
            embedding_backend="tfidf",
            top_k_candidates=3,
            top_k_final=2,
        )
        retriever.fit(chunks)

        query = "How do I authenticate GitHub REST API requests?"
        results = retriever.retrieve(query, top_k=2)

        self.assertGreaterEqual(len(results), 2)
        self.assertEqual(results[0].chunk_id, "specific-auth-doc")

    def test_best_score_returns_zero_for_unfitted_or_empty(self) -> None:
        retriever = HybridRetriever(
            embedding_model_name="sentence-transformers/all-MiniLM-L6-v2",
            embedding_backend="tfidf",
            top_k_candidates=3,
            top_k_final=2,
        )

        score = retriever.best_score("test query")
        self.assertEqual(score, 0.0)


if __name__ == "__main__":
    unittest.main()
