from __future__ import annotations

from itertools import combinations
import re

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from neurvinch.embeddings import EmbeddingBackendError, TextEmbedder
from neurvinch.models import ContradictionFinding, DocumentChunk


class NLIAuditor:
    """Finds high-confidence contradictions between semantically similar chunks."""

    def __init__(
        self,
        embedding_model_name: str,
        embedding_backend: str,
        nli_model_name: str,
        nli_backend: str,
        contradiction_threshold: float,
    ) -> None:
        self.embedding_model_name = embedding_model_name
        self.embedding_backend = embedding_backend
        self.nli_model_name = nli_model_name
        self.nli_backend = (nli_backend or "heuristic").strip().lower()
        self.contradiction_threshold = contradiction_threshold
        self.embedder = TextEmbedder(model_name=embedding_model_name, backend=embedding_backend)
        self.nli_model = None

    def audit(self, chunks: list[DocumentChunk]) -> list[ContradictionFinding]:
        if len(chunks) < 2:
            return []

        texts = [chunk.text for chunk in chunks]
        try:
            self.embedder.fit(texts)
        except EmbeddingBackendError:
            self.embedder = TextEmbedder(model_name=self.embedding_model_name, backend="tfidf")
            self.embedder.fit(texts)

        embeddings = self.embedder.encode(texts)
        similarity = cosine_similarity(embeddings)

        candidate_pairs = self._candidate_pairs(similarity)
        if not candidate_pairs:
            return []

        pair_probabilities = self._pair_probabilities(chunks, candidate_pairs)

        findings: list[ContradictionFinding] = []
        for pair_idx, (i, j) in enumerate(candidate_pairs):
            probs = pair_probabilities[pair_idx]
            contradiction_prob = self._contradiction_probability(probs)
            label = self._label_for_probs(probs)
            if contradiction_prob >= self.contradiction_threshold:
                findings.append(
                    ContradictionFinding(
                        chunk_a_id=chunks[i].id,
                        chunk_b_id=chunks[j].id,
                        contradiction_probability=float(contradiction_prob),
                        label=label,
                        recommended_action="deprecate_older_version",
                    )
                )

        findings.sort(key=lambda item: item.contradiction_probability, reverse=True)
        return findings

    def _candidate_pairs(self, similarity: np.ndarray) -> list[tuple[int, int]]:
        candidates: list[tuple[int, int]] = []
        for i, j in combinations(range(similarity.shape[0]), 2):
            if similarity[i, j] >= 0.35:
                candidates.append((i, j))
        return candidates

    def _pair_probabilities(
        self,
        chunks: list[DocumentChunk],
        candidate_pairs: list[tuple[int, int]],
    ) -> list[np.ndarray]:
        if self.nli_backend == "cross-encoder":
            probabilities = self._cross_encoder_probabilities(chunks, candidate_pairs)
            if probabilities is not None:
                return probabilities

        return [
            self._heuristic_probs(chunks[i].text, chunks[j].text)
            for i, j in candidate_pairs
        ]

    def _cross_encoder_probabilities(
        self,
        chunks: list[DocumentChunk],
        candidate_pairs: list[tuple[int, int]],
    ) -> list[np.ndarray] | None:
        try:
            from sentence_transformers import CrossEncoder
        except Exception:
            return None

        if self.nli_model is None:
            self.nli_model = CrossEncoder(self.nli_model_name)

        sentence_pairs = [(chunks[i].text, chunks[j].text) for i, j in candidate_pairs]
        logits = self.nli_model.predict(sentence_pairs)

        probabilities: list[np.ndarray] = []
        for row in logits:
            arr = np.asarray(row, dtype=float)
            if arr.ndim == 0:
                scalar = float(arr)
                arr = np.array([1.0 - scalar, scalar, 0.0], dtype=float)
            probabilities.append(self._softmax(arr))

        return probabilities

    def _heuristic_probs(self, text_a: str, text_b: str) -> np.ndarray:
        tokens_a = set(self._tokenize(text_a))
        tokens_b = set(self._tokenize(text_b))
        overlap = self._jaccard(tokens_a, tokens_b)

        quantities_a = self._extract_quantities(text_a)
        quantities_b = self._extract_quantities(text_b)

        if overlap >= 0.33 and quantities_a and quantities_b and quantities_a != quantities_b:
            return np.array([0.93, 0.03, 0.04], dtype=float)

        if overlap >= 0.55:
            return np.array([0.08, 0.72, 0.20], dtype=float)

        return np.array([0.05, 0.15, 0.80], dtype=float)

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-z0-9_]+", text.lower())

    def _jaccard(self, set_a: set[str], set_b: set[str]) -> float:
        union = set_a | set_b
        if not union:
            return 0.0
        return len(set_a & set_b) / len(union)

    def _extract_quantities(self, text: str) -> set[tuple[float, str]]:
        quantity_pattern = re.compile(
            r"\b(\d+(?:\.\d+)?)\s*(minute|minutes|hour|hours|day|days|week|weeks|month|months|year|years)\b",
            flags=re.IGNORECASE,
        )

        normalized: set[tuple[float, str]] = set()
        for amount, unit in quantity_pattern.findall(text):
            normalized.add((float(amount), unit.lower().rstrip("s")))

        return normalized

    def _softmax(self, logits: np.ndarray) -> np.ndarray:
        shifted = logits - np.max(logits)
        exps = np.exp(shifted)
        return exps / np.sum(exps)

    def _contradiction_probability(self, probs: np.ndarray) -> float:
        labels = self._id2label()
        contradiction_idx = next((idx for idx, label in labels.items() if "contrad" in label), 0)
        return float(probs[contradiction_idx])

    def _label_for_probs(self, probs: np.ndarray) -> str:
        labels = self._id2label()
        best_idx = int(np.argmax(probs))
        return labels.get(best_idx, str(best_idx))

    def _id2label(self) -> dict[int, str]:
        if self.nli_model is None:
            return {0: "contradiction", 1: "entailment", 2: "neutral"}

        raw = getattr(self.nli_model.model.config, "id2label", {}) or {}
        parsed: dict[int, str] = {}
        for key, value in raw.items():
            try:
                parsed[int(key)] = str(value).lower()
            except ValueError:
                continue
        if parsed:
            return parsed
        return {0: "contradiction", 1: "entailment", 2: "neutral"}
