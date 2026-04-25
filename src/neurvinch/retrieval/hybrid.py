from __future__ import annotations

import re

import numpy as np
from rank_bm25 import BM25Okapi

from neurvinch.embeddings import EmbeddingBackendError, TextEmbedder
from neurvinch.models import DocumentChunk, RetrievalResult


class HybridRetriever:
    """Combines BM25 pre-filtering with semantic reranking and source grounding."""

    def __init__(
        self,
        embedding_model_name: str,
        top_k_candidates: int,
        top_k_final: int,
        embedding_backend: str = "tfidf",
    ) -> None:
        self.embedding_model_name = embedding_model_name
        self.embedding_backend = embedding_backend
        self.embedder = TextEmbedder(model_name=embedding_model_name, backend=embedding_backend)
        self.top_k_candidates = top_k_candidates
        self.top_k_final = top_k_final
        self._chunks: list[DocumentChunk] = []
        self._tokenized_corpus: list[list[str]] = []
        self._bm25: BM25Okapi | None = None
        self._embeddings: np.ndarray | None = None

    def fit(self, chunks: list[DocumentChunk]) -> None:
        self._chunks = chunks
        self._tokenized_corpus = [self._tokenize(chunk.text) for chunk in chunks]
        self._bm25 = BM25Okapi(self._tokenized_corpus) if self._tokenized_corpus else None
        if chunks:
            texts = [chunk.text for chunk in chunks]
            try:
                self.embedder.fit(texts)
            except EmbeddingBackendError:
                self.embedder = TextEmbedder(model_name=self.embedding_model_name, backend="tfidf")
                self.embedder.fit(texts)
            self._embeddings = self.embedder.encode(texts)
        else:
            self._embeddings = None

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievalResult]:
        if not self._chunks or self._bm25 is None or self._embeddings is None:
            return []

        top_k = top_k or self.top_k_final
        query_tokens = self._tokenize(query)

        bm25_scores = np.array(self._bm25.get_scores(query_tokens), dtype=float)
        if bm25_scores.size == 0:
            return []

        candidate_count = min(self.top_k_candidates, len(self._chunks))
        candidate_idx = np.argsort(bm25_scores)[::-1][:candidate_count]

        query_emb = self.embedder.encode([query])[0]
        candidate_embs = self._embeddings[candidate_idx]
        semantic_scores = self._cosine(candidate_embs, query_emb)

        bm25_norm = self._normalize(bm25_scores[candidate_idx])
        semantic_norm = self._normalize(semantic_scores)
        combined = 0.35 * bm25_norm + 0.65 * semantic_norm

        # Penalize catalog/index files so specific documentation ranks higher
        for i, idx in enumerate(candidate_idx):
            path = str(self._chunks[idx].metadata.path).lower()
            if "catalog" in path or "index" in path or "readme" in path:
                combined[i] *= 0.6  # Apply 40% penalty to structural overview files

        rank_order = np.argsort(combined)[::-1][: min(top_k, len(candidate_idx))]

        results: list[RetrievalResult] = []
        for order_idx in rank_order:
            source_idx = int(candidate_idx[order_idx])
            chunk = self._chunks[source_idx]
            results.append(
                RetrievalResult(
                    chunk_id=chunk.id,
                    score=float(combined[order_idx]),
                    bm25_score=float(bm25_scores[source_idx]),
                    semantic_score=float(semantic_scores[order_idx]),
                    text=chunk.text,
                    source=chunk.metadata,
                )
            )

        return results

    def best_score(self, query: str) -> float:
        results = self.retrieve(query, top_k=1)
        return results[0].score if results else 0.0

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-zA-Z0-9_]+", text.lower())

    def _normalize(self, values: np.ndarray) -> np.ndarray:
        if values.size == 0:
            return values
        v_min = float(np.min(values))
        v_max = float(np.max(values))
        if np.isclose(v_min, v_max):
            return np.ones_like(values)
        return (values - v_min) / (v_max - v_min)

    def _cosine(self, matrix: np.ndarray, vector: np.ndarray) -> np.ndarray:
        matrix_norm = np.linalg.norm(matrix, axis=1)
        vector_norm = np.linalg.norm(vector)
        denominator = matrix_norm * vector_norm
        denominator = np.where(denominator == 0, 1e-9, denominator)
        return (matrix @ vector) / denominator
