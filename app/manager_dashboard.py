from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from neurvinch.models import DocumentChunk
from neurvinch.config import settings
from neurvinch.pipeline import run_pipeline
from neurvinch.retrieval import HybridRetriever


st.set_page_config(page_title="Neurvinch Manager Dashboard", layout="wide")

OUTPUT_DIR = ROOT / "outputs"


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def ensure_artifacts() -> dict:
    report_path = OUTPUT_DIR / "report.json"
    if report_path.exists():
        return load_json(report_path, {})

    with st.spinner("Running Neurvinch pipeline for first-time setup..."):
        run_pipeline()
    return load_json(report_path, {})


def build_grounded_answer(query: str, retriever: HybridRetriever) -> tuple[str, list[dict]]:
    results = retriever.retrieve(query, top_k=3)
    if not results:
        return "No grounded evidence found for this query.", []

    snippets: list[str] = []
    citations: list[dict] = []
    for result in results:
        text = " ".join(result.text.split())
        snippets.append(text[:220] + ("..." if len(text) > 220 else ""))
        citations.append(
            {
                "path": result.source.path,
                "section": result.source.section,
                "score": round(result.score, 4),
            }
        )

    answer = (
        "Grounded summary based on retrieved sources:\n\n"
        + "\n\n".join(f"- {snippet}" for snippet in snippets)
    )
    return answer, citations


st.title("Neurvinch: Knowledge Audit & Hybrid RAG")
st.caption("Detect contradictions, uncover documentation voids, and test grounded retrieval.")

col_left, col_right = st.columns([2, 1])
with col_right:
    if st.button("Run Full Audit", type="primary"):
        with st.spinner("Executing ingestion, indexing, audit, and gap analysis..."):
            summary = run_pipeline()
        st.success(f"Audit complete. Knowledge Health Score: {summary['knowledge_health_score']}")

report = ensure_artifacts()
structural_index = load_json(OUTPUT_DIR / "structural_index.json", [])
chunks_raw = load_json(OUTPUT_DIR / "chunks.json", [])
contradictions = load_json(OUTPUT_DIR / "contradictions.json", [])
void_clusters = load_json(OUTPUT_DIR / "void_clusters.json", [])

if not report:
    st.warning("No report generated yet. Click 'Run Full Audit' to create artifacts.")
    st.stop()

metric_cols = st.columns(4)
metric_cols[0].metric("Knowledge Health Score", report.get("knowledge_health_score", 0.0))
metric_cols[1].metric("Indexed Chunks", report.get("total_chunks", 0))
metric_cols[2].metric("Contradictions", report.get("contradictions", 0))
metric_cols[3].metric("Documentation Voids", report.get("void_clusters", 0))

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Contradiction Alerts")
    if contradictions:
        contradiction_df = pd.DataFrame(contradictions)
        st.dataframe(contradiction_df, use_container_width=True)
    else:
        st.info("No high-confidence contradictions found.")

with right:
    st.subheader("Documentation Void Clusters")
    if void_clusters:
        void_df = pd.DataFrame(void_clusters)
        st.dataframe(void_df, use_container_width=True)
    else:
        st.info("No void clusters detected from query logs.")

st.divider()
st.subheader("Hybrid Retrieval Playground")

chunks = [DocumentChunk(**item) for item in chunks_raw]
retriever = HybridRetriever(
    embedding_model_name=settings.embedding_model,
    embedding_backend=settings.embedding_backend,
    top_k_candidates=20,
    top_k_final=5,
)
retriever.fit(chunks)

query = st.text_input("Ask a question to test grounded retrieval:", placeholder="How often should VPN credentials be rotated?")
if query:
    answer, citations = build_grounded_answer(query, retriever)
    st.markdown(answer)

    if citations:
        st.markdown("**Citations**")
        citations_df = pd.DataFrame(citations)
        st.dataframe(citations_df, use_container_width=True)

st.divider()
st.subheader("Structural Index Snapshot")
if structural_index:
    index_df = pd.DataFrame(structural_index)
    st.dataframe(index_df.head(50), use_container_width=True)
else:
    st.info("No structural index available yet.")
