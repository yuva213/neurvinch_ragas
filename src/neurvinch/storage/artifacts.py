from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from neurvinch.models import AuditArtifacts


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, default=str)


def load_json(path: Path, fallback: Any = None) -> Any:
    if not path.exists():
        return fallback
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def persist_audit_artifacts(artifacts: AuditArtifacts, output_dir: Path, health_score: float) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    save_json(output_dir / "structural_index.json", [node.model_dump() for node in artifacts.structural_index])
    save_json(output_dir / "chunks.json", [chunk.model_dump() for chunk in artifacts.chunks])
    save_json(output_dir / "contradictions.json", [item.model_dump() for item in artifacts.contradictions])
    save_json(output_dir / "void_clusters.json", [item.model_dump() for item in artifacts.void_clusters])

    summary = {
        "knowledge_health_score": health_score,
        "total_nodes": len(artifacts.structural_index),
        "total_chunks": len(artifacts.chunks),
        "contradictions": len(artifacts.contradictions),
        "void_clusters": len([item for item in artifacts.void_clusters if item.status == "Documentation Void"]),
        "metadata": artifacts.metadata,
    }
    save_json(output_dir / "report.json", summary)
