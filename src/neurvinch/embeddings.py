from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


class EmbeddingBackendError(RuntimeError):
    """Raised when an embedding backend cannot be initialized."""


@dataclass
class TextEmbedder:
    """Thin embedding wrapper with a safe default backend.

    Backends:
    - "tfidf": pure sklearn backend, reliable and lightweight.
    - "sentence-transformers": semantic embeddings via Hugging Face models.
    """

    model_name: str
    backend: str = "tfidf"

    def __post_init__(self) -> None:
        self.backend = (self.backend or "tfidf").strip().lower()
        self._fitted = False
        self._st_model = None
        self._vectorizer: TfidfVectorizer | None = None

    def fit(self, texts: list[str]) -> None:
        texts = texts or [""]
        if self.backend == "sentence-transformers":
            try:
                from sentence_transformers import SentenceTransformer
            except Exception as exc:  # pragma: no cover - environment dependent
                raise EmbeddingBackendError(
                    "sentence-transformers backend requested but package is unavailable"
                ) from exc

            self._st_model = SentenceTransformer(self.model_name)
            self._fitted = True
            return

        self._vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b")
        self._vectorizer.fit(texts)
        self._fitted = True

    def encode(self, texts: list[str]) -> np.ndarray:
        if not self._fitted:
            self.fit(texts)

        if self.backend == "sentence-transformers":
            assert self._st_model is not None
            vectors = self._st_model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            return np.asarray(vectors, dtype=float)

        assert self._vectorizer is not None
        vectors = self._vectorizer.transform(texts).toarray()
        return np.asarray(vectors, dtype=float)