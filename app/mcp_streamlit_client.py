import asyncio, sys
from pathlib import Path
import streamlit as st

# ── Path bootstrap ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
SRC  = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ── MCP server params ────────────────────────────────────────────────────────
server_script = ROOT / "run_mcp_server.py"
server_params  = StdioServerParameters(
    command="python",
    args=["-X", "utf8", str(server_script)],
    env=None,
)

# ── Core MCP helpers ─────────────────────────────────────────────────────────
async def run_mcp_command(tool_name, arguments=None):
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                response = await session.call_tool(tool_name, arguments or {})
                if hasattr(response, "content") and response.content:
                    return "\n".join(
                        item.text for item in response.content if hasattr(item, "text")
                    )
                return str(response)
    except Exception as exc:
        return f"❌ Error: {exc}"

def sync_run_mcp(tool_name, arguments=None):
    return asyncio.run(run_mcp_command(tool_name, arguments))

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Neurvinch MCP Client",
    page_icon="🔌",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');

/* ── Reset & base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"],
[data-testid="stApp"] {
    background: #0a0e1a !important;
    font-family: 'Outfit', sans-serif !important;
    color: #e2e8f0 !important;
}

/* hide default Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0a0e1a; }
::-webkit-scrollbar-thumb { background: #7c3aed55; border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: #7c3aed; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.03) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border-right: 1px solid rgba(255,255,255,0.07) !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 1.5rem 1rem; }

/* ── Sidebar inputs ── */
[data-testid="stSidebar"] input[type="text"],
[data-testid="stSidebar"] input {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(124,58,237,0.35) !important;
    border-radius: 999px !important;
    color: #e2e8f0 !important;
    padding: 0.5rem 1.1rem !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 0.88rem !important;
    transition: border-color .25s, box-shadow .25s;
}
[data-testid="stSidebar"] input:focus {
    border-color: #7c3aed !important;
    box-shadow: 0 0 0 3px rgba(124,58,237,0.2) !important;
    outline: none !important;
}

/* ── Main area padding ── */
[data-testid="stMain"] > div:first-child { padding: 2rem 2.5rem; }

/* ── Glass card ── */
.glass-card {
    background: rgba(255,255,255,0.04);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
}

/* ── Tab bar ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.03) !important;
    border-radius: 12px !important;
    padding: 4px !important;
    gap: 4px !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 10px !important;
    color: #94a3b8 !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    padding: 0.5rem 1.2rem !important;
    border: none !important;
    transition: all .2s !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: linear-gradient(135deg, #7c3aed, #4f46e5) !important;
    color: #fff !important;
    box-shadow: 0 0 20px rgba(124,58,237,0.45) !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] { display: none !important; }

/* ── Primary button ── */
.stButton > button {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    border-radius: 999px !important;
    padding: 0.55rem 1.6rem !important;
    transition: all .25s !important;
    cursor: pointer !important;
}
/* default = outlined secondary */
.stButton > button {
    background: transparent !important;
    border: 1.5px solid rgba(124,58,237,0.55) !important;
    color: #a78bfa !important;
}
.stButton > button:hover {
    border-color: #7c3aed !important;
    background: rgba(124,58,237,0.12) !important;
    box-shadow: 0 0 18px rgba(124,58,237,0.3) !important;
    color: #fff !important;
}
/* primary class override */
.btn-primary > button,
button[kind="primary"] {
    background: linear-gradient(135deg, #7c3aed, #4f46e5) !important;
    border: none !important;
    color: #fff !important;
    box-shadow: 0 4px 24px rgba(124,58,237,0.4) !important;
}
.btn-primary > button:hover,
button[kind="primary"]:hover {
    box-shadow: 0 6px 32px rgba(124,58,237,0.6) !important;
    transform: translateY(-1px) !important;
}

/* ── Text input / textarea ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(124,58,237,0.3) !important;
    border-radius: 12px !important;
    color: #e2e8f0 !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 0.92rem !important;
    transition: border-color .25s, box-shadow .25s !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: #7c3aed !important;
    box-shadow: 0 0 0 3px rgba(124,58,237,0.2) !important;
    outline: none !important;
}

/* ── Code blocks ── */
pre, code, .stCodeBlock {
    background: rgba(0,0,0,0.4) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 10px !important;
    font-size: 0.82rem !important;
}

/* ── Success / error overrides ── */
[data-testid="stAlert"] {
    border-radius: 12px !important;
    border: none !important;
    font-family: 'Outfit', sans-serif !important;
}
[data-testid="stAlert"][data-type="success"] {
    background: rgba(16,185,129,0.12) !important;
    border-left: 3px solid #10b981 !important;
    color: #6ee7b7 !important;
}
[data-testid="stAlert"][data-type="error"] {
    background: rgba(239,68,68,0.1) !important;
    border-left: 3px solid #ef4444 !important;
    color: #fca5a5 !important;
}

/* ── Labels ── */
label, .stTextInput label, .stTextArea label {
    color: #94a3b8 !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    letter-spacing: .04em !important;
    text-transform: uppercase !important;
}

/* ── Divider ── */
hr { border-color: rgba(255,255,255,0.07) !important; margin: 1rem 0 !important; }

/* ── Animations ── */
@keyframes pulseGreen {
    0%,100% { opacity:1; box-shadow: 0 0 6px #10b981; }
    50%      { opacity:.5; box-shadow: 0 0 14px #10b981; }
}
@keyframes fadeSlideUp {
    from { opacity:0; transform: translateY(14px); }
    to   { opacity:1; transform: translateY(0); }
}
@keyframes shimmer {
    0%   { background-position: -200% center; }
    100% { background-position:  200% center; }
}
@keyframes subtlePulse {
    0%,100% { opacity:.8; } 50% { opacity:1; }
}

/* ── Hero ── */
.hero-title {
    font-size: 2.6rem;
    font-weight: 800;
    letter-spacing: -.02em;
    background: linear-gradient(135deg, #a78bfa 0%, #818cf8 40%, #38bdf8 100%);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: shimmer 4s linear infinite, fadeSlideUp .6s ease;
    margin-bottom: .25rem;
}
.hero-subtitle {
    font-size: 1rem;
    color: #64748b;
    font-weight: 400;
    animation: fadeSlideUp .8s ease, subtlePulse 4s ease infinite;
    margin-bottom: 2rem;
}

/* ── Sidebar branding ── */
.sidebar-brand {
    font-size: 1.15rem;
    font-weight: 700;
    color: #a78bfa;
    letter-spacing: -.01em;
    margin-bottom: 1.2rem;
    display: flex;
    align-items: center;
    gap: .5rem;
}

/* ── Status dot ── */
.status-row {
    display: flex;
    align-items: center;
    gap: .6rem;
    font-size: .85rem;
    font-weight: 500;
    margin-bottom: 1rem;
    color: #94a3b8;
}
.dot-connected {
    width: 9px; height: 9px;
    background: #10b981;
    border-radius: 50%;
    animation: pulseGreen 2s ease infinite;
    flex-shrink: 0;
}
.dot-disconnected {
    width: 9px; height: 9px;
    background: #ef4444;
    border-radius: 50%;
    flex-shrink: 0;
}

/* ── Tool badge ── */
.tool-badge {
    display: inline-flex;
    align-items: center;
    gap: .35rem;
    background: rgba(124,58,237,0.15);
    border: 1px solid rgba(124,58,237,0.3);
    border-radius: 999px;
    padding: .22rem .75rem;
    font-size: .78rem;
    font-weight: 500;
    color: #a78bfa;
    margin: .2rem .15rem;
    transition: background .2s;
}
.tool-badge:hover { background: rgba(124,58,237,0.28); }

/* ── Result card ── */
.result-card {
    background: rgba(0,0,0,0.35);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 1.1rem 1.3rem;
    font-size: .86rem;
    line-height: 1.7;
    color: #cbd5e1;
    white-space: pre-wrap;
    animation: fadeSlideUp .5s ease;
    margin-top: .75rem;
}

/* ── Answer card ── */
.answer-card {
    background: rgba(124,58,237,0.07);
    border: 1px solid rgba(124,58,237,0.25);
    border-radius: 16px;
    padding: 1.3rem 1.5rem;
    animation: fadeSlideUp .5s ease;
    color: #e2e8f0;
    font-size: .92rem;
    line-height: 1.8;
    margin-top: .75rem;
}

/* ── Citation chip ── */
.citation-chip {
    display: inline-block;
    background: rgba(79,70,229,0.2);
    border: 1px solid rgba(79,70,229,0.4);
    border-radius: 999px;
    padding: .15rem .65rem;
    font-size: .75rem;
    color: #818cf8;
    margin: .2rem .15rem;
    font-weight: 500;
}

/* ── Toast ── */
.toast-success {
    background: rgba(16,185,129,0.13);
    border: 1px solid rgba(16,185,129,0.35);
    border-radius: 12px;
    padding: .7rem 1.1rem;
    color: #6ee7b7;
    font-size: .88rem;
    font-weight: 500;
    animation: fadeSlideUp .4s ease;
    margin-top: .5rem;
}
.toast-error {
    background: rgba(239,68,68,0.1);
    border: 1px solid rgba(239,68,68,0.3);
    border-radius: 12px;
    padding: .7rem 1.1rem;
    color: #fca5a5;
    font-size: .88rem;
    font-weight: 500;
    animation: fadeSlideUp .4s ease;
    margin-top: .5rem;
}

/* ── Section header ── */
.section-header {
    font-size: 1rem;
    font-weight: 600;
    color: #cbd5e1;
    margin-bottom: .75rem;
    letter-spacing: -.01em;
}

/* ── Sidebar section label ── */
.sidebar-section {
    font-size: .72rem;
    font-weight: 600;
    color: #475569;
    letter-spacing: .08em;
    text-transform: uppercase;
    margin: 1.2rem 0 .5rem;
}

/* ── Upload area ── */
.upload-hint {
    font-size: .8rem;
    color: #475569;
    margin-top: .35rem;
    font-style: italic;
}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div class="sidebar-brand">🔌 Neurvinch</div>', unsafe_allow_html=True)

    # ── Server status ────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section">MCP Server</div>', unsafe_allow_html=True)

    if "server_connected" not in st.session_state:
        st.session_state.server_connected = False

    if st.button("⚡ Ping Server", key="ping_btn"):
        with st.spinner("Connecting…"):
            result = sync_run_mcp("list_available_tools", {})
        if result and "❌" not in result:
            st.session_state.server_connected = True
            st.session_state.tool_list = result
        else:
            st.session_state.server_connected = False
            st.session_state.tool_list = ""

    if st.session_state.server_connected:
        st.markdown(
            '<div class="status-row">'
            '<span class="dot-connected"></span>'
            '<span style="color:#10b981;font-weight:600;">Connected</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="status-row">'
            '<span class="dot-disconnected"></span>'
            '<span style="color:#ef4444;">Disconnected</span>'
            '</div>',
            unsafe_allow_html=True,
        )

    # ── Active tools ─────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section">Active Tools</div>', unsafe_allow_html=True)
    known_tools = [
        ("🗑️", "clean_dataset"),
        ("🔍", "index_dataset"),
        ("💬", "query_rag"),
        ("📄", "upload_document"),
        ("📋", "list_available_tools"),
    ]
    badges_html = "".join(
        f'<span class="tool-badge">{icon} {name}</span>' for icon, name in known_tools
    )
    st.markdown(f'<div style="margin-bottom:.5rem">{badges_html}</div>', unsafe_allow_html=True)

    # ── Dataset path ─────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section">📁 Dataset Path</div>', unsafe_allow_html=True)
    dataset_path = st.text_input(
        "Dataset path",
        value=st.session_state.get("dataset_path", ""),
        placeholder="📂  /path/to/dataset",
        label_visibility="collapsed",
        key="dataset_path_input",
    )

    if st.button("💾 Set Path", key="set_path_btn"):
        if dataset_path.strip():
            st.session_state.dataset_path = dataset_path.strip()
            result = sync_run_mcp("set_dataset_path", {"path": dataset_path.strip()})
            if "❌" not in result:
                st.markdown(
                    f'<div class="toast-success">✅ Path set successfully</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="toast-error">{result}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div class="toast-error">⚠️ Please enter a dataset path</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:.72rem;color:#334155;text-align:center;padding-top:1rem;">'
        'Neurvinch RAG · MCP Client<br>'
        '<span style="color:#4f46e5;">v1.0</span>'
        '</div>',
        unsafe_allow_html=True,
    )

# ═══════════════════════════════════════════════════════════════════════════
#  HERO HEADER
# ═══════════════════════════════════════════════════════════════════════════
st.markdown(
    '<div class="hero-title">🔌 Neurvinch MCP Client</div>'
    '<div class="hero-subtitle">Model Context Protocol · Retrieval-Augmented Generation · Premium Interface</div>',
    unsafe_allow_html=True,
)

# thin divider
st.markdown(
    '<div style="height:2px;background:linear-gradient(90deg,'
    'transparent,rgba(124,58,237,0.5),transparent);'
    'border-radius:999px;margin-bottom:1.5rem;"></div>',
    unsafe_allow_html=True,
)

# ═══════════════════════════════════════════════════════════════════════════
#  MAIN TABS
# ═══════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3 = st.tabs(["🧹  Clean & Index", "💬  Grounded Q&A", "📄  Upload Document"])

# ─────────────────────────────────────────────────────────────────────────
#  TAB 1 — Clean & Index
# ─────────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-header">Dataset Management</div>'
        '<p style="color:#64748b;font-size:.88rem;margin-bottom:1.1rem;">'
        'Clean stale vectors or re-index your dataset with a single click.</p>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2, gap="medium")

    with col1:
        st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
        clean_clicked = st.button("🗑️  Clean Dataset", key="clean_btn", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        index_clicked = st.button("🔍  Index Dataset", key="index_btn", use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)  # /glass-card

    # results
    if clean_clicked:
        with st.spinner("Cleaning dataset…"):
            result = sync_run_mcp("clean_dataset", {})
        if "❌" not in result:
            st.markdown(
                f'<div class="toast-success">✅ Clean complete</div>'
                f'<div class="result-card">{result}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="toast-error">{result}</div>',
                unsafe_allow_html=True,
            )

    if index_clicked:
        with st.spinner("Indexing dataset… this may take a moment"):
            result = sync_run_mcp("index_dataset", {})
        if "❌" not in result:
            st.markdown(
                f'<div class="toast-success">✅ Indexing complete</div>'
                f'<div class="result-card">{result}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="toast-error">{result}</div>',
                unsafe_allow_html=True,
            )

# ─────────────────────────────────────────────────────────────────────────
#  TAB 2 — Grounded Q&A
# ─────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-header">Ask a Question</div>'
        '<p style="color:#64748b;font-size:.88rem;margin-bottom:1rem;">'
        'Queries are grounded in your indexed documents via RAG.</p>',
        unsafe_allow_html=True,
    )
    question = st.text_input(
        "Your question",
        placeholder="✦  What would you like to know?",
        label_visibility="collapsed",
        key="question_input",
    )

    st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
    ask_clicked = st.button("🚀  Send", key="ask_btn", use_container_width=False)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)  # /glass-card

    if ask_clicked:
        if question.strip():
            with st.spinner("Searching knowledge base…"):
                answer = sync_run_mcp("query_rag", {"query": question.strip()})
            if "❌" not in answer:
                # Parse citations (lines starting with "Source:" or "[" )
                lines = answer.split("\n")
                body_lines, citation_lines = [], []
                for line in lines:
                    stripped = line.strip()
                    if stripped.lower().startswith("source:") or (
                        stripped.startswith("[") and "]" in stripped
                    ):
                        citation_lines.append(stripped)
                    else:
                        body_lines.append(line)

                body = "\n".join(body_lines).strip()
                chips_html = "".join(
                    f'<span class="citation-chip">📎 {c}</span>' for c in citation_lines
                )

                st.markdown(
                    f'<div class="answer-card">'
                    f'<div style="margin-bottom:.6rem;font-size:.8rem;color:#7c3aed;font-weight:600;'
                    f'letter-spacing:.05em;text-transform:uppercase;">✦ AI Answer</div>'
                    f'{body}'
                    f'{"<br><br>" + chips_html if chips_html else ""}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="toast-error">{answer}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div class="toast-error">⚠️ Please enter a question</div>',
                unsafe_allow_html=True,
            )

# ─────────────────────────────────────────────────────────────────────────
#  TAB 3 — Upload Document
# ─────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-header">Upload a Document</div>'
        '<p style="color:#64748b;font-size:.88rem;margin-bottom:1rem;">'
        'Paste document content below to ingest it into the knowledge base.</p>',
        unsafe_allow_html=True,
    )

    doc_filename = st.text_input(
        "Document filename",
        placeholder="e.g.  research_paper.txt",
        label_visibility="collapsed",
        key="doc_filename",
    )
    st.markdown(
        '<div class="upload-hint">Give your document a descriptive filename (including extension).</div>',
        unsafe_allow_html=True,
    )

    doc_content = st.text_area(
        "Document content",
        placeholder="Paste or type your document content here…",
        height=320,
        label_visibility="collapsed",
        key="doc_content",
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
    upload_clicked = st.button("📤  Upload Document", key="upload_btn", use_container_width=False)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)  # /glass-card

    if upload_clicked:
        if doc_filename.strip() and doc_content.strip():
            with st.spinner("Uploading and ingesting document…"):
                result = sync_run_mcp(
                    "upload_document",
                    {"filename": doc_filename.strip(), "content": doc_content.strip()},
                )
            if "❌" not in result:
                st.markdown(
                    f'<div class="toast-success">✅ Document uploaded successfully</div>'
                    f'<div class="result-card">{result}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="toast-error">{result}</div>',
                    unsafe_allow_html=True,
                )
        else:
            missing = []
            if not doc_filename.strip():
                missing.append("filename")
            if not doc_content.strip():
                missing.append("content")
            st.markdown(
                f'<div class="toast-error">⚠️ Please provide: {", ".join(missing)}</div>',
                unsafe_allow_html=True,
            )
