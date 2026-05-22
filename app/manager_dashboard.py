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

st.set_page_config(page_title="Neurvinch Dashboard", page_icon="🧠", layout="wide")

OUTPUT_DIR = ROOT / "outputs"

# ────────────────────────────────────────────────────────────────
# Global CSS — Premium dark glassmorphism theme
# ────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif !important;
    background-color: #0a0e1a !important;
    color: #e2e8f0 !important;
}

/* Hide default Streamlit chrome decorations */
#MainMenu, footer, header { visibility: hidden; }

/* App container */
.block-container {
    padding: 0 2.5rem 3rem 2.5rem !important;
    max-width: 1400px !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: rgba(255, 255, 255, 0.04) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.10) !important;
    backdrop-filter: blur(16px) !important;
}
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }

/* ── Hero banner ── */
.hero-banner {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f2027 100%);
    border: 1px solid rgba(99, 102, 241, 0.30);
    border-radius: 20px;
    padding: 2.8rem 3rem;
    margin: 1.5rem 0 2rem 0;
    position: relative;
    overflow: hidden;
    box-shadow: 0 0 60px rgba(99, 102, 241, 0.12), inset 0 0 80px rgba(16, 185, 129, 0.04);
}
.hero-banner::before {
    content: '';
    position: absolute;
    top: -50%; left: -20%;
    width: 60%; height: 200%;
    background: radial-gradient(ellipse, rgba(99,102,241,0.15) 0%, transparent 70%);
    pointer-events: none;
}
.hero-banner::after {
    content: '';
    position: absolute;
    bottom: -40%; right: -10%;
    width: 50%; height: 180%;
    background: radial-gradient(ellipse, rgba(16,185,129,0.10) 0%, transparent 70%);
    pointer-events: none;
}
.hero-title {
    font-size: 2.5rem;
    font-weight: 800;
    letter-spacing: -0.5px;
    background: linear-gradient(90deg, #a5b4fc 0%, #38bdf8 50%, #34d399 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 0 0.5rem 0;
    position: relative;
    z-index: 1;
}
.hero-subtitle {
    font-size: 1.05rem;
    font-weight: 400;
    color: #94a3b8;
    margin: 0;
    position: relative;
    z-index: 1;
}

/* ── Section headers ── */
.section-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin: 2rem 0 1rem 0;
    font-size: 1.15rem;
    font-weight: 600;
    color: #e2e8f0;
}
.section-header::before {
    content: '';
    display: inline-block;
    width: 4px;
    height: 1.4em;
    border-radius: 4px;
    background: linear-gradient(180deg, #6366f1, #10b981);
    flex-shrink: 0;
}

/* ── KPI glass tiles ── */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1.2rem;
    margin: 1.5rem 0 2rem 0;
}
.kpi-card {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.10);
    backdrop-filter: blur(16px);
    border-radius: 16px;
    padding: 1.4rem 1.6rem 1.6rem;
    position: relative;
    overflow: hidden;
    transition: border-color 0.25s, box-shadow 0.25s, transform 0.2s;
}
.kpi-card:hover {
    border-color: rgba(255,255,255,0.20);
    transform: translateY(-3px);
}
.kpi-icon {
    font-size: 1.5rem;
    margin-bottom: 0.6rem;
    display: block;
}
.kpi-label {
    font-size: 0.78rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #64748b;
    margin-bottom: 0.35rem;
}
.kpi-value {
    font-size: 2.1rem;
    font-weight: 800;
    line-height: 1;
    margin-bottom: 0.2rem;
}
.kpi-ring {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.78rem;
    font-weight: 500;
    padding: 0.2rem 0.6rem;
    border-radius: 20px;
    margin-top: 0.5rem;
}
/* Per-card accent glow */
.kpi-health  { box-shadow: 0 0 30px rgba(16,185,129,0.12); }
.kpi-health .kpi-value  { color: #10b981; }
.kpi-health .kpi-ring   { background: rgba(16,185,129,0.12); color: #10b981; }

.kpi-chunks  { box-shadow: 0 0 30px rgba(99,102,241,0.10); }
.kpi-chunks .kpi-value  { color: #818cf8; }
.kpi-chunks .kpi-ring   { background: rgba(99,102,241,0.12); color: #818cf8; }

.kpi-contrad { box-shadow: 0 0 30px rgba(239,68,68,0.10); }
.kpi-contrad .kpi-value { color: #ef4444; }
.kpi-contrad .kpi-ring  { background: rgba(239,68,68,0.12); color: #ef4444; }

.kpi-void    { box-shadow: 0 0 30px rgba(245,158,11,0.10); }
.kpi-void .kpi-value    { color: #f59e0b; }
.kpi-void .kpi-ring     { background: rgba(245,158,11,0.12); color: #f59e0b; }

/* ── Glass card wrapper ── */
.glass-card {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.10);
    backdrop-filter: blur(16px);
    border-radius: 16px;
    padding: 1.5rem 1.8rem;
    margin-bottom: 1.2rem;
}

/* ── Response glass card ── */
.response-card {
    background: rgba(16, 185, 129, 0.05);
    border: 1px solid rgba(16, 185, 129, 0.25);
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    font-size: 0.95rem;
    line-height: 1.7;
    color: #d1fae5;
    margin: 1rem 0;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    padding: 0.55rem 1.4rem !important;
    letter-spacing: 0.02em !important;
    transition: all 0.25s ease !important;
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.40) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px rgba(99, 102, 241, 0.55) !important;
}

/* ── Text input ── */
.stTextInput > div > div > input {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.14) !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 0.65rem 1rem !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextInput > div > div > input:focus {
    border-color: rgba(99,102,241,0.60) !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
}
.stTextInput > div > div > input::placeholder { color: #475569 !important; }

/* ── Dataframes ── */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.08);
}

/* ── Info / warning / success ── */
.stAlert {
    background: rgba(255,255,255,0.04) !important;
    border-radius: 10px !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
}

/* ── Spinner ── */
.stSpinner > div { border-top-color: #10b981 !important; }

/* ── Divider ── */
hr { border-color: rgba(255,255,255,0.08) !important; }

/* ── Status bar ── */
.status-bar {
    display: flex;
    align-items: center;
    gap: 2rem;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 0.85rem 1.4rem;
    margin-top: 2.5rem;
    font-size: 0.80rem;
    color: #475569;
}
.status-bar .pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.2rem 0.65rem;
    border-radius: 20px;
    font-weight: 500;
}
.pill-green { background: rgba(16,185,129,0.12); color: #10b981; }
.pill-indigo { background: rgba(99,102,241,0.12); color: #818cf8; }
.pill-amber  { background: rgba(245,158,11,0.12); color: #f59e0b; }
</style>
""",
    unsafe_allow_html=True,
)

# ────────────────────────────────────────────────────────────────
# Logic helpers  (unchanged)
# ────────────────────────────────────────────────────────────────

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


# ────────────────────────────────────────────────────────────────
# Hero banner
# ────────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="hero-banner">
    <p class="hero-title">🧠 Neurvinch Knowledge Audit Dashboard</p>
    <p class="hero-subtitle">
        Detect contradictions · Uncover documentation voids · Test grounded hybrid retrieval
    </p>
</div>
""",
    unsafe_allow_html=True,
)

# Run Full Audit button in hero area
hero_col, btn_col = st.columns([5, 1])
with btn_col:
    if st.button("⚡ Run Full Audit", type="primary", use_container_width=True):
        with st.spinner("Executing ingestion, indexing, audit, and gap analysis..."):
            summary = run_pipeline()
        st.success(f"Audit complete. Knowledge Health Score: {summary['knowledge_health_score']}")

# ────────────────────────────────────────────────────────────────
# Load artifacts  (unchanged logic)
# ────────────────────────────────────────────────────────────────
report = ensure_artifacts()
structural_index = load_json(OUTPUT_DIR / "structural_index.json", [])
chunks_raw = load_json(OUTPUT_DIR / "chunks.json", [])
contradictions = load_json(OUTPUT_DIR / "contradictions.json", [])
void_clusters = load_json(OUTPUT_DIR / "void_clusters.json", [])

if not report:
    st.warning("No report generated yet. Click '⚡ Run Full Audit' to create artifacts.")
    st.stop()

# ────────────────────────────────────────────────────────────────
# KPI metric tiles
# ────────────────────────────────────────────────────────────────
health_score = report.get("knowledge_health_score", 0.0)
total_chunks  = report.get("total_chunks", 0)
total_contrad = report.get("contradictions", 0)
total_voids   = report.get("void_clusters", 0)

# Determine health label
if isinstance(health_score, (int, float)):
    if health_score >= 0.8:
        health_label = "🟢 Excellent"
    elif health_score >= 0.6:
        health_label = "🟡 Moderate"
    else:
        health_label = "🔴 Critical"
else:
    health_label = "⚪ N/A"

st.markdown(
    f"""
<div class="kpi-grid">
    <div class="kpi-card kpi-health">
        <span class="kpi-icon">💚</span>
        <div class="kpi-label">Knowledge Health Score</div>
        <div class="kpi-value">{health_score}</div>
        <span class="kpi-ring">{health_label}</span>
    </div>
    <div class="kpi-card kpi-chunks">
        <span class="kpi-icon">📦</span>
        <div class="kpi-label">Indexed Chunks</div>
        <div class="kpi-value">{total_chunks}</div>
        <span class="kpi-ring">🔵 Active</span>
    </div>
    <div class="kpi-card kpi-contrad">
        <span class="kpi-icon">⚡</span>
        <div class="kpi-label">Contradictions</div>
        <div class="kpi-value">{total_contrad}</div>
        <span class="kpi-ring">{"🔴 Review Needed" if total_contrad > 0 else "✅ Clear"}</span>
    </div>
    <div class="kpi-card kpi-void">
        <span class="kpi-icon">🕳️</span>
        <div class="kpi-label">Documentation Voids</div>
        <div class="kpi-value">{total_voids}</div>
        <span class="kpi-ring">{"🟡 Gaps Detected" if total_voids > 0 else "✅ Complete"}</span>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ────────────────────────────────────────────────────────────────
# Contradiction Alerts + Documentation Void Clusters
# ────────────────────────────────────────────────────────────────
left, right = st.columns(2)

with left:
    st.markdown(
        '<div class="section-header">⚡ Contradiction Alerts</div>',
        unsafe_allow_html=True,
    )
    if contradictions:
        contradiction_df = pd.DataFrame(contradictions)
        st.dataframe(contradiction_df, use_container_width=True)
    else:
        st.info("✅ No high-confidence contradictions found.")

with right:
    st.markdown(
        '<div class="section-header">🕳️ Documentation Void Clusters</div>',
        unsafe_allow_html=True,
    )
    if void_clusters:
        void_df = pd.DataFrame(void_clusters)
        st.dataframe(void_df, use_container_width=True)
    else:
        st.info("✅ No void clusters detected from query logs.")

# ────────────────────────────────────────────────────────────────
# Hybrid Retrieval Playground
# ────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="section-header">🔍 Hybrid Retrieval Playground</div>',
    unsafe_allow_html=True,
)

# Build retriever (unchanged logic)
chunks = [DocumentChunk(**item) for item in chunks_raw]
retriever = HybridRetriever(
    embedding_model_name=settings.embedding_model,
    embedding_backend=settings.embedding_backend,
    top_k_candidates=20,
    top_k_final=5,
)
retriever.fit(chunks)

query = st.text_input(
    "Ask a question to test grounded retrieval:",
    placeholder="How often should VPN credentials be rotated?",
    label_visibility="visible",
)

if query:
    answer, citations = build_grounded_answer(query, retriever)

    # Show answer in styled glass card
    answer_html = answer.replace("\n", "<br>")
    st.markdown(
        f'<div class="response-card">{answer_html}</div>',
        unsafe_allow_html=True,
    )

    if citations:
        st.markdown(
            '<div class="section-header" style="margin-top:1rem;">📎 Citations</div>',
            unsafe_allow_html=True,
        )
        citations_df = pd.DataFrame(citations)
        st.dataframe(citations_df, use_container_width=True)

# ────────────────────────────────────────────────────────────────
# Structural Index Snapshot
# ────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="section-header">🗂️ Structural Index Snapshot</div>',
    unsafe_allow_html=True,
)
if structural_index:
    index_df = pd.DataFrame(structural_index)
    st.dataframe(index_df.head(50), use_container_width=True)
else:
    st.info("No structural index available yet.")

# ────────────────────────────────────────────────────────────────
# Status bar
# ────────────────────────────────────────────────────────────────
embed_model = getattr(settings, "embedding_model", "unknown")
embed_backend = getattr(settings, "embedding_backend", "unknown")

st.markdown(
    f"""
<div class="status-bar">
    <span>🧠 <strong>Neurvinch</strong> Knowledge Audit Pipeline</span>
    <span class="pill pill-green">● Pipeline Ready</span>
    <span class="pill pill-indigo">🔗 Embedding: {embed_model}</span>
    <span class="pill pill-indigo">⚙️ Backend: {embed_backend}</span>
    <span class="pill pill-amber">📦 Chunks Loaded: {len(chunks_raw)}</span>
    <span style="margin-left:auto;">v1.0 · Neurvinch RAG Audit</span>
</div>
""",
    unsafe_allow_html=True,
)
