import asyncio
import sys
from pathlib import Path
import streamlit as st
import pandas as pd

# Add src path to sys.path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

st.set_page_config(page_title="Neurvinch Streamlit MCP Client", layout="wide")

# Theme styling helper
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        color: #1E3A8A;
        font-weight: 700;
        margin-bottom: 0.1rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #4B5563;
        margin-bottom: 2rem;
    }
    .card {
        padding: 1.5rem;
        border-radius: 12px;
        background-color: #F3F4F6;
        border: 1px solid #E5E7EB;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown('<div class="main-header">⚡ Neurvinch Streamlit MCP Client</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Demonstrating how to connect your Python Streamlit frontend to the Neurvinch MCP Server over standard I/O (stdio) transport.</div>', unsafe_allow_html=True)

# Define server parameters
server_script = ROOT / "run_mcp_server.py"
server_params = StdioServerParameters(
    command="python",
    args=["-X", "utf8", str(server_script)],
    env=None
)

async def run_mcp_command(tool_name: str, arguments: dict = None) -> str:
    """Helper function to execute an MCP tool command on the local stdio server."""
    if arguments is None:
        arguments = {}
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                response = await session.call_tool(tool_name, arguments)
                # Parse text response from Content elements
                if hasattr(response, 'content') and response.content:
                    text_parts = [item.text for item in response.content if hasattr(item, 'text')]
                    return "\n".join(text_parts)
                return str(response)
    except Exception as e:
        return f"❌ Error communicating with MCP server: {e}\nEnsure python is on your PATH and you have installed all requirements."

def sync_run_mcp(tool_name: str, arguments: dict = None) -> str:
    """Synchronous wrapper to run async MCP function."""
    return asyncio.run(run_mcp_command(tool_name, arguments))

# --- UI Layout ---
col_sidebar, col_main = st.columns([1, 2])

with col_sidebar:
    st.header("⚙️ Server Parameters")
    st.info(f"📁 **Server script found:** `{server_script.name}`")
    
    # Tool Selector
    st.subheader("🛠️ Active MCP Tools")
    st.markdown(
        """
        The following tools are exposed by the server and called dynamically by this client:
        - `set_knowledge_base_path`
        - `upload_document`
        - `clean_and_index_dataset`
        - `ask_grounded_question`
        - `get_cleaned_dataset_summary`
        """
    )
    
    st.divider()
    
    # Dataset Configuration
    st.subheader("📁 Configure Target Dataset")
    custom_path = st.text_input("Local Folder Path", str(ROOT / "data" / "kb"))
    if st.button("Set Dataset Path", type="secondary"):
        with st.spinner("Connecting to MCP server and updating path..."):
            result = sync_run_mcp("set_knowledge_base_path", {"directory_path": custom_path})
            st.success(result)

with col_main:
    tabs = st.tabs(["🚀 Clean & Index Dataset", "💬 Grounded Q&A Playground", "📄 Add Document"])
    
    # Tab 1: Ingestion & Ingestion summary
    with tabs[0]:
        st.subheader("🧹 Dataset Cleaning & Deduplication Panel")
        st.markdown(
            "Click the button below to trigger the MCP server's indexer, exact de-duplicator, and "
            "contradiction resolution engine. This will produce a clean, hallucination-free knowledge base."
        )
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🧼 Run Dataset Clean & Index", type="primary"):
                with st.spinner("MCP Server is processing, cleaning, and indexing your data..."):
                    result = sync_run_mcp("clean_and_index_dataset")
                    st.markdown("### Clean Results")
                    st.markdown(result)
        
        with c2:
            if st.button("📊 Fetch Clean Dataset Summary"):
                with st.spinner("Fetching active index metadata..."):
                    result = sync_run_mcp("get_cleaned_dataset_summary")
                    st.markdown("### Active Index Status")
                    st.markdown(result)

    # Tab 2: Grounded Q&A Play area
    with tabs[1]:
        st.subheader("💬 Hallucination-Free Q&A Playground")
        st.write("Submit queries to retrieve matching clean evidence and generate cited answers:")
        
        user_query = st.text_input("Enter your question", placeholder="e.g. How often should VPN credentials be rotated?")
        if st.button("Submit Question", type="primary") and user_query:
            with st.spinner("RAG Retrieval & Groq LLM generating answers..."):
                answer = sync_run_mcp("ask_grounded_question", {"query": user_query})
                st.markdown("### Grounded Response")
                st.markdown(answer)

    # Tab 3: Upload new doc
    with tabs[2]:
        st.subheader("📄 Direct Document Ingestion")
        st.write("Upload or create a new file in the active dataset folder:")
        
        new_filename = st.text_input("Filename", placeholder="e.g., policy_v3.0.md")
        new_content = st.text_area("File Content", height=200, placeholder="Type markdown or plain text here...")
        
        if st.button("Upload to KB") and new_filename and new_content:
            with st.spinner("Ingesting file via MCP..."):
                result = sync_run_mcp("upload_document", {"filename": new_filename, "content": new_content})
                st.success(result)
