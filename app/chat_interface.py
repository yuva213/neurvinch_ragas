from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# ── Path bootstrap ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from neurvinch.indexing import StructuralIndexer
from neurvinch.config import settings
from neurvinch.retrieval import HybridRetriever
from neurvinch.generative import GroqGenerator

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Neurvinch AI Chat",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── Fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');

    /* ── Reset & base ── */
    html, body, [data-testid="stAppViewContainer"] {
        background: #0a0e1a !important;
        font-family: 'Outfit', sans-serif !important;
        color: #e2e8f0 !important;
    }

    [data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }

    /* ── Remove default padding ── */
    .block-container {
        padding-top: 0 !important;
        padding-bottom: 2rem !important;
        max-width: 780px !important;
    }

    /* ── Hero header ── */
    .hero-header {
        text-align: center;
        padding: 3rem 1.5rem 2.5rem;
        background: linear-gradient(135deg, #0a0e1a 0%, #12183a 50%, #0a0e1a 100%);
        position: relative;
        overflow: hidden;
        border-radius: 0 0 2rem 2rem;
        margin-bottom: 2rem;
    }
    .hero-header::before {
        content: '';
        position: absolute;
        inset: 0;
        background: radial-gradient(ellipse 70% 60% at 50% 0%, rgba(99,102,241,0.25) 0%, transparent 70%);
        pointer-events: none;
    }
    .hero-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, #6366f1, #a78bfa, #8b5cf6, #6366f1);
        background-size: 300% 100%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: gradientShift 4s ease infinite;
        margin: 0;
        line-height: 1.1;
        letter-spacing: -0.02em;
    }
    @keyframes gradientShift {
        0%   { background-position: 0% 50%; }
        50%  { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    .hero-subtitle {
        font-size: 1.05rem;
        font-weight: 400;
        color: #94a3b8;
        margin-top: 0.6rem;
        letter-spacing: 0.01em;
    }

    /* ── Status badge ── */
    .status-row {
        display: flex;
        justify-content: center;
        margin-top: 1.2rem;
    }
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.3rem 0.9rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 500;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        backdrop-filter: blur(10px);
    }
    .status-badge.online {
        background: rgba(16,185,129,0.12);
        border: 1px solid rgba(16,185,129,0.35);
        color: #6ee7b7;
    }
    .status-badge.offline {
        background: rgba(251,191,36,0.10);
        border: 1px solid rgba(251,191,36,0.35);
        color: #fcd34d;
    }
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
    }
    .status-dot.online {
        background: #10b981;
        box-shadow: 0 0 0 0 rgba(16,185,129,0.7);
        animation: pulse-green 1.8s ease-out infinite;
    }
    .status-dot.offline {
        background: #f59e0b;
        box-shadow: 0 0 0 0 rgba(245,158,11,0.7);
        animation: pulse-amber 2s ease-out infinite;
    }
    @keyframes pulse-green {
        0%   { box-shadow: 0 0 0 0   rgba(16,185,129,0.7); }
        70%  { box-shadow: 0 0 0 8px rgba(16,185,129,0);   }
        100% { box-shadow: 0 0 0 0   rgba(16,185,129,0);   }
    }
    @keyframes pulse-amber {
        0%   { box-shadow: 0 0 0 0   rgba(245,158,11,0.7); }
        70%  { box-shadow: 0 0 0 8px rgba(245,158,11,0);   }
        100% { box-shadow: 0 0 0 0   rgba(245,158,11,0);   }
    }

    /* ── Input box ── */
    [data-testid="stTextInput"] > div > div {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(99,102,241,0.4) !important;
        border-radius: 14px !important;
        backdrop-filter: blur(12px) !important;
        color: #e2e8f0 !important;
        font-family: 'Outfit', sans-serif !important;
        font-size: 1rem !important;
        transition: border-color 0.25s ease, box-shadow 0.25s ease !important;
    }
    [data-testid="stTextInput"] > div > div:focus-within {
        border-color: rgba(99,102,241,0.9) !important;
        box-shadow: 0 0 0 3px rgba(99,102,241,0.18) !important;
    }
    [data-testid="stTextInput"] input {
        color: #e2e8f0 !important;
        font-family: 'Outfit', sans-serif !important;
    }
    [data-testid="stTextInput"] input::placeholder {
        color: #64748b !important;
    }
    [data-testid="stTextInput"] label {
        color: #94a3b8 !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.05em !important;
        text-transform: uppercase !important;
    }

    /* ── User query bubble ── */
    .user-bubble {
        display: flex;
        justify-content: flex-end;
        margin: 1.2rem 0 0.5rem;
    }
    .user-pill {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        color: #fff;
        padding: 0.65rem 1.2rem;
        border-radius: 20px 20px 4px 20px;
        font-size: 0.97rem;
        font-weight: 500;
        max-width: 75%;
        box-shadow: 0 4px 20px rgba(99,102,241,0.35);
        word-break: break-word;
        line-height: 1.5;
    }

    /* ── AI response glass card ── */
    .ai-card {
        background: rgba(255,255,255,0.05);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255,255,255,0.08);
        border-left: 3px solid #6366f1;
        border-radius: 4px 16px 16px 16px;
        padding: 1.2rem 1.4rem;
        margin: 0.5rem 0 1rem;
        font-size: 0.97rem;
        line-height: 1.75;
        color: #cbd5e1;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    .ai-card-label {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #818cf8;
        margin-bottom: 0.6rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }

    /* ── Source chips ── */
    .sources-section {
        margin-top: 0.8rem;
    }
    .sources-label {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #64748b;
        margin-bottom: 0.5rem;
    }
    .chips-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
    }
    .source-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.28rem 0.75rem;
        background: rgba(99,102,241,0.1);
        border: 1px solid rgba(99,102,241,0.3);
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 500;
        color: #a5b4fc;
        cursor: default;
        transition: background 0.2s ease, box-shadow 0.2s ease;
        box-shadow: 0 0 6px rgba(99,102,241,0.15);
        max-width: 260px;
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
    }
    .source-chip:hover {
        background: rgba(99,102,241,0.2);
        box-shadow: 0 0 12px rgba(99,102,241,0.35);
    }
    .chip-idx {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        color: #fff;
        border-radius: 50%;
        width: 16px;
        height: 16px;
        font-size: 0.62rem;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }

    /* ── Retrieval-only evidence card ── */
    .evidence-card {
        background: rgba(255,255,255,0.04);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.7rem;
        font-size: 0.92rem;
        color: #cbd5e1;
        line-height: 1.65;
    }
    .evidence-meta {
        font-size: 0.72rem;
        color: #475569;
        margin-top: 0.45rem;
        font-weight: 500;
    }

    /* ── Warning / info overrides ── */
    [data-testid="stAlert"] {
        background: rgba(251,191,36,0.08) !important;
        border: 1px solid rgba(251,191,36,0.25) !important;
        border-radius: 12px !important;
        color: #fcd34d !important;
        font-family: 'Outfit', sans-serif !important;
    }

    /* ── Spinner override ── */
    [data-testid="stSpinner"] > div {
        color: #818cf8 !important;
        font-family: 'Outfit', sans-serif !important;
    }

    /* ── Divider ── */
    .glow-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(99,102,241,0.45), transparent);
        margin: 1.5rem 0;
        border: none;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0a0e1a; }
    ::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.4); border-radius: 3px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Backend init ─────────────────────────────────────────────────────────────
indexer = StructuralIndexer(ROOT / "data" / "kb")
_, chunks = indexer.index()

retriever = HybridRetriever(
    embedding_model_name=settings.embedding_model,
    embedding_backend=settings.embedding_backend,
    top_k_candidates=20,
    top_k_final=4,
)
retriever.fit(chunks)

try:
    generator = GroqGenerator(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )
    groq_enabled = True
except ValueError:
    groq_enabled = False

# ── Hero header ──────────────────────────────────────────────────────────────
_status_cls = "online" if groq_enabled else "offline"
_status_txt = "Groq Connected" if groq_enabled else "Groq Offline – Retrieval Mode"

st.markdown(
    f"""
    <div class="hero-header">
        <p class="hero-title">⚡ Neurvinch AI Chat</p>
        <p class="hero-subtitle">AI-powered grounded answers from your audited knowledge base</p>
        <div class="status-row">
            <span class="status-badge {_status_cls}">
                <span class="status-dot {_status_cls}"></span>
                {_status_txt}
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Query input ───────────────────────────────────────────────────────────────
query = st.text_input(
    "Ask a question",
    placeholder="e.g. What is the account lockout policy?",
    key="main_query",
)

# ── Response area ─────────────────────────────────────────────────────────────
if query:
    results = retriever.retrieve(query, top_k=4)

    # User bubble
    st.markdown(
        f'<div class="user-bubble"><div class="user-pill">{query}</div></div>',
        unsafe_allow_html=True,
    )

    if not results:
        st.warning("⚠️ No grounded evidence found in the knowledge base.")
    else:
        if groq_enabled:
            with st.spinner("✦ Synthesising answer from knowledge base…"):
                response = generator.generate(query, results)

            # AI response card
            st.markdown(
                f"""
                <div class="ai-card">
                    <div class="ai-card-label">✦ &nbsp;Neurvinch AI</div>
                    {response}
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Source chips
            chip_html = ""
            for idx, result in enumerate(results, start=1):
                source_path = Path(result.source.path).name
                section = result.source.section or ""
                label = f"{source_path}" + (f" › {section}" if section else "")
                chip_html += (
                    f'<span class="source-chip" title="{result.source.path} | score={result.score:.3f}">'
                    f'<span class="chip-idx">{idx}</span>{label}'
                    f"</span>"
                )

            st.markdown(
                f"""
                <div class="sources-section">
                    <div class="sources-label">📎 Sources</div>
                    <div class="chips-row">{chip_html}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        else:
            # Retrieval-only mode
            st.warning("⚠️ Groq API key not configured — showing retrieval results only.")
            st.markdown('<hr class="glow-divider">', unsafe_allow_html=True)

            for idx, result in enumerate(results, start=1):
                source = f"{result.source.path} | {result.source.section}"
                st.markdown(
                    f"""
                    <div class="evidence-card">
                        <strong style="color:#a5b4fc;">#{idx}</strong>&nbsp; {result.text}
                        <div class="evidence-meta">📎 {source} &nbsp;·&nbsp; score={result.score:.3f}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
