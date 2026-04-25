from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

from neurvinch.embeddings import EmbeddingBackendError, TextEmbedder
from neurvinch.models import VoidCluster


class IntentDiscovery:
    """Clusters user queries and flags low-retrieval clusters as documentation voids."""

    def __init__(
        self,
        embedding_model_name: str,
        eps: float,
        min_samples: int,
        void_threshold: float,
        embedding_backend: str = "tfidf",
    ) -> None:
        self.embedding_model_name = embedding_model_name
        self.embedding_backend = embedding_backend
        self.embedder = TextEmbedder(model_name=embedding_model_name, backend=embedding_backend)
        self.eps = eps
        self.min_samples = min_samples
        self.void_threshold = void_threshold

    def discover_voids(self, query_log_path: Path, retrieval_score_fn) -> list[VoidCluster]:
        if not query_log_path.exists():
            return []

        df = pd.read_csv(query_log_path)
        if df.empty:
            return []

        query_col = "query" if "query" in df.columns else df.columns[0]
        queries = [str(value).strip() for value in df[query_col].tolist() if str(value).strip()]

        if len(queries) < self.min_samples:
            return []

        try:
            self.embedder.fit(queries)
        except EmbeddingBackendError:
            self.embedder = TextEmbedder(model_name=self.embedding_model_name, backend="tfidf")
            self.embedder.fit(queries)

        embeddings = self.embedder.encode(queries)
        clustering = DBSCAN(eps=self.eps, min_samples=self.min_samples, metric="cosine")
        labels = clustering.fit_predict(embeddings)

        groups: dict[int, list[int]] = defaultdict(list)
        for idx, label in enumerate(labels):
            if label == -1:
                continue
            groups[int(label)].append(idx)

        if not groups:
            return []

        clusters: list[VoidCluster] = []
        for cluster_id, indices in groups.items():
            cluster_queries = [queries[i] for i in indices]
            cluster_embeddings = embeddings[indices]
            centroid_query = self._nearest_to_centroid(cluster_queries, cluster_embeddings)
            scores = [float(retrieval_score_fn(query)) for query in cluster_queries]
            avg_score = float(np.mean(scores)) if scores else 0.0

            clusters.append(
                VoidCluster(
                    cluster_id=cluster_id,
                    size=len(cluster_queries),
                    centroid_query=centroid_query,
                    avg_retrieval_score=avg_score,
                    status="Documentation Void" if avg_score < self.void_threshold else "Covered",
                )
            )

        clusters.sort(key=lambda item: (item.status != "Documentation Void", item.avg_retrieval_score))
        return clusters

    def _nearest_to_centroid(self, queries: list[str], embeddings: np.ndarray) -> str:
        centroid = np.mean(embeddings, axis=0)
        norms = np.linalg.norm(embeddings, axis=1) * np.linalg.norm(centroid)
        norms = np.where(norms == 0, 1e-9, norms)
        similarities = (embeddings @ centroid) / norms
        best_idx = int(np.argmax(similarities))
        return queries[best_idx]
