from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SourceMetadata(BaseModel):
    path: str
    page: int | None = None
    section: str | None = None
    last_modified: datetime | None = None
    version: str | None = None


class StructuralNode(BaseModel):
    id: str
    title: str
    level: int
    parent_id: str | None = None
    page: int | None = None


class DocumentChunk(BaseModel):
    id: str
    text: str
    metadata: SourceMetadata


class ContradictionFinding(BaseModel):
    chunk_a_id: str
    chunk_b_id: str
    contradiction_probability: float
    label: str
    recommended_action: str


class VoidCluster(BaseModel):
    cluster_id: int
    size: int
    centroid_query: str
    avg_retrieval_score: float
    status: str


class RetrievalResult(BaseModel):
    chunk_id: str
    score: float
    bm25_score: float
    semantic_score: float
    text: str
    source: SourceMetadata


class AuditArtifacts(BaseModel):
    structural_index: list[StructuralNode]
    chunks: list[DocumentChunk]
    contradictions: list[ContradictionFinding]
    void_clusters: list[VoidCluster]
    metadata: dict[str, Any] = Field(default_factory=dict)
