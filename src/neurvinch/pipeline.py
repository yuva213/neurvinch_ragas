from __future__ import annotations

from datetime import datetime

from neurvinch.audit import NLIAuditor
from neurvinch.config import settings
from neurvinch.indexing import StructuralIndexer
from neurvinch.intents import IntentDiscovery
from neurvinch.models import AuditArtifacts
from neurvinch.retrieval import HybridRetriever
from neurvinch.storage import persist_audit_artifacts


def knowledge_health_score(chunks_count: int, contradictions_count: int, void_clusters_count: int) -> float:
    if chunks_count <= 0:
        return 0.0

    contradiction_rate = contradictions_count / max(chunks_count, 1)
    contradiction_penalty = min(1.0, contradiction_rate)

    void_penalty = min(1.0, void_clusters_count / 10.0)

    score = 1.0 - (0.65 * contradiction_penalty + 0.35 * void_penalty)
    return round(max(0.0, score), 4)


def run_pipeline() -> dict[str, float | int]:
    indexer = StructuralIndexer(settings.kb_path)
    structural_index, chunks = indexer.index()

    retriever = HybridRetriever(
        embedding_model_name=settings.embedding_model,
        embedding_backend=settings.embedding_backend,
        top_k_candidates=settings.top_k_candidates,
        top_k_final=settings.top_k_final,
    )
    retriever.fit(chunks)

    auditor = NLIAuditor(
        embedding_model_name=settings.embedding_model,
        embedding_backend=settings.embedding_backend,
        nli_model_name=settings.nli_model,
        nli_backend=settings.nli_backend,
        contradiction_threshold=settings.contradiction_threshold,
    )
    contradictions = auditor.audit(chunks)

    intent_discovery = IntentDiscovery(
        embedding_model_name=settings.embedding_model,
        embedding_backend=settings.embedding_backend,
        eps=settings.dbscan_eps,
        min_samples=settings.dbscan_min_samples,
        void_threshold=settings.void_retrieval_threshold,
    )
    void_clusters = intent_discovery.discover_voids(
        query_log_path=settings.query_log_path,
        retrieval_score_fn=retriever.best_score,
    )

    void_count = len([cluster for cluster in void_clusters if cluster.status == "Documentation Void"])
    health_score = knowledge_health_score(
        chunks_count=len(chunks),
        contradictions_count=len(contradictions),
        void_clusters_count=void_count,
    )

    artifacts = AuditArtifacts(
        structural_index=structural_index,
        chunks=chunks,
        contradictions=contradictions,
        void_clusters=void_clusters,
        metadata={
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "kb_path": str(settings.kb_path),
            "query_log_path": str(settings.query_log_path),
            "embedding_model": settings.embedding_model,
            "embedding_backend": settings.embedding_backend,
            "nli_model": settings.nli_model,
            "nli_backend": settings.nli_backend,
        },
    )

    persist_audit_artifacts(artifacts, settings.output_dir, health_score)

    return {
        "knowledge_health_score": health_score,
        "total_nodes": len(structural_index),
        "total_chunks": len(chunks),
        "contradictions": len(contradictions),
        "void_clusters": void_count,
    }


def main() -> None:
    summary = run_pipeline()
    print("Neurvinch pipeline completed.")
    for key, value in summary.items():
        print(f"- {key}: {value}")
