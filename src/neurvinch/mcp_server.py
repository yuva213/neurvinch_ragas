import json
import logging
from pathlib import Path
import re
from typing import Optional, List, Dict, Any

from mcp.server.fastmcp import FastMCP

from neurvinch.config import settings
from neurvinch.indexing import StructuralIndexer
from neurvinch.retrieval import HybridRetriever
from neurvinch.audit import NLIAuditor
from neurvinch.generative import GroqGenerator
from neurvinch.models import DocumentChunk, SourceMetadata, RetrievalResult

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("neurvinch-mcp")

# Initialize FastMCP Server
mcp = FastMCP("Neurvinch RAG & Data Cleaner")

# Active state
_kb_path: Path = Path(settings.kb_path).resolve()
_cleaned_chunks: List[DocumentChunk] = []
_retriever: Optional[HybridRetriever] = None
_generator: Optional[GroqGenerator] = None

# Try initializing Groq generator
try:
    if settings.llm_api_key:
        _generator = GroqGenerator(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
        logger.info(f"Groq generator initialized with model {settings.llm_model}")
except Exception as e:
    logger.warning(f"Failed to initialize Groq generator: {e}")


def _get_retriever() -> HybridRetriever:
    """Helper to initialize or retrieve the hybrid retriever."""
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever(
            embedding_model_name=settings.embedding_model,
            embedding_backend=settings.embedding_backend,
            top_k_candidates=settings.top_k_candidates,
            top_k_final=settings.top_k_final,
        )
    return _retriever


def _parse_version(version_str: Optional[str]) -> tuple:
    """Parse version string like 'v1.2.3' or '2.0' into a tuple of ints for comparison."""
    if not version_str:
        return (0,)
    # Remove leading 'v' or 'version'
    clean = re.sub(r'^[a-zA-Z\s\-]+', '', version_str)
    try:
        return tuple(int(x) for x in re.findall(r'\d+', clean))
    except Exception:
        return (0,)


@mcp.tool()
def set_knowledge_base_path(directory_path: str) -> str:
    """Configure the local directory path containing the user's dataset to index and clean.
    
    Args:
        directory_path: The absolute folder path to read files from.
    """
    global _kb_path, _cleaned_chunks, _retriever
    path = Path(directory_path).resolve()
    if not path.exists():
        # Create it if it doesn't exist to make it user-friendly
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return f"❌ Error: Path does not exist and could not be created: {e}"
            
    _kb_path = path
    # Reset state for the new directory
    _cleaned_chunks = []
    _retriever = None
    
    return (
        f"✅ Dataset path successfully updated to: {_kb_path}\n"
        f"Please run the `clean_and_index_dataset` tool next to import, clean, and activate this dataset."
    )


@mcp.tool()
def get_current_dataset_path() -> str:
    """Get the active dataset/knowledge base directory path."""
    return f"Active Dataset Path: {_kb_path}"


@mcp.tool()
def upload_document(filename: str, content: str) -> str:
    """Upload or write a new document (text/markdown) directly into the active dataset folder.
    
    Args:
        filename: Name of the file (e.g. 'company_policy_v2.md' or 'network_guide.txt')
        content: The text content of the document.
    """
    global _kb_path
    if not _kb_path.exists():
        _kb_path.mkdir(parents=True, exist_ok=True)
        
    file_path = _kb_path / filename
    try:
        file_path.write_text(content, encoding="utf-8")
        return (
            f"✅ File successfully saved: {file_path.name}\n"
            f"Size: {len(content)} characters.\n"
            f"Note: Remember to run `clean_and_index_dataset` to re-clean and index the dataset with this file!"
        )
    except Exception as e:
        return f"❌ Failed to save file: {e}"


@mcp.tool()
def clean_and_index_dataset() -> str:
    """Ingests raw documents from the active path, cleans duplicates, resolves contradictions, and fits the retriever.
    
    It performs:
      1. Extraction of chunks.
      2. Exact duplicate text removal.
      3. Near-duplicate removal via cosine similarity.
      4. Contradiction resolution: drops older versions or less informative chunks that conflict.
    """
    global _kb_path, _cleaned_chunks, _retriever
    
    if not _kb_path.exists():
        return f"❌ Error: Dataset path {_kb_path} does not exist. Please configure it or upload a document first."

    # Step 1: Index raw chunks
    indexer = StructuralIndexer(_kb_path)
    try:
        nodes, raw_chunks = indexer.index()
    except Exception as e:
        return f"❌ Error indexing files in dataset: {e}"

    if not raw_chunks:
        return f"⚠️ No text files (.md, .pdf, .txt) found in active dataset path: {_kb_path}"

    total_raw_chunks = len(raw_chunks)
    
    # Step 2: Exact Duplicate Removal
    exact_duplicates_removed = 0
    seen_texts = set()
    first_pass_chunks: List[DocumentChunk] = []
    
    for chunk in raw_chunks:
        norm_text = " ".join(chunk.text.strip().lower().split())
        if norm_text in seen_texts:
            exact_duplicates_removed += 1
            continue
        seen_texts.add(norm_text)
        first_pass_chunks.append(chunk)

    # Step 3: Semantic Duplicate Removal & Contradiction Resolution
    # Initialize Auditor
    auditor = NLIAuditor(
        embedding_model_name=settings.embedding_model,
        embedding_backend=settings.embedding_backend,
        nli_model_name=settings.nli_model,
        nli_backend=settings.nli_backend,
        contradiction_threshold=settings.contradiction_threshold,
    )
    
    # We audit first_pass_chunks
    try:
        contradictions = auditor.audit(first_pass_chunks)
    except Exception as e:
        logger.error(f"Audit step encountered an error: {e}. Falling back to heuristic audit.")
        auditor.nli_backend = "heuristic"
        contradictions = auditor.audit(first_pass_chunks)

    # Resolve contradictions by dropping conflicting chunks
    chunks_by_id = {c.id: c for c in first_pass_chunks}
    ids_to_drop = set()
    resolved_contradictions = []

    for finding in contradictions:
        id_a, id_b = finding.chunk_a_id, finding.chunk_b_id
        if id_a in ids_to_drop or id_b in ids_to_drop:
            continue  # Already dropped one of them

        chunk_a = chunks_by_id[id_a]
        chunk_b = chunks_by_id[id_b]

        # Determine which one to keep
        version_a = _parse_version(chunk_a.metadata.version)
        version_b = _parse_version(chunk_b.metadata.version)

        if version_a != version_b:
            # Drop older version
            if version_a > version_b:
                drop_id, keep_id = id_b, id_a
            else:
                drop_id, keep_id = id_a, id_b
            reason = f"older version (deprecated in favor of version {max(chunk_a.metadata.version, chunk_b.metadata.version)})"
        else:
            # Fallback to last modified date
            mtime_a = chunk_a.metadata.last_modified
            mtime_b = chunk_b.metadata.last_modified
            
            if mtime_a and mtime_b and mtime_a != mtime_b:
                if mtime_a > mtime_b:
                    drop_id, keep_id = id_b, id_a
                else:
                    drop_id, keep_id = id_a, id_b
                reason = "older file modification time"
            else:
                # Fallback to text length (longer is usually more comprehensive)
                if len(chunk_a.text) >= len(chunk_b.text):
                    drop_id, keep_id = id_b, id_a
                else:
                    drop_id, keep_id = id_a, id_b
                reason = "less comprehensive content (shorter chunk length)"

        ids_to_drop.add(drop_id)
        resolved_contradictions.append({
            "kept": chunks_by_id[keep_id].metadata.path,
            "dropped": chunks_by_id[drop_id].metadata.path,
            "kept_section": chunks_by_id[keep_id].metadata.section,
            "dropped_section": chunks_by_id[drop_id].metadata.section,
            "probability": finding.contradiction_probability,
            "reason": reason
        })

    # Assemble cleaned chunks
    _cleaned_chunks = [c for c in first_pass_chunks if c.id not in ids_to_drop]
    
    # Save cleaned chunks to file
    cleaned_path = Path(settings.output_dir) / "cleaned_chunks.json"
    cleaned_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with cleaned_path.open("w", encoding="utf-8") as f:
            json.dump([c.model_dump() for c in _cleaned_chunks], f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to persist cleaned chunks: {e}")

    # Step 4: Fit Retriever Strictly on Clean Chunks
    retriever = _get_retriever()
    try:
        retriever.fit(_cleaned_chunks)
    except Exception as e:
        return f"❌ Error fitting retriever on cleaned dataset: {e}"

    # Build response summary
    summary = {
        "status": "Success",
        "dataset_path": str(_kb_path),
        "metrics": {
            "total_raw_chunks": total_raw_chunks,
            "exact_duplicates_removed": exact_duplicates_removed,
            "contradictory_chunks_removed": len(ids_to_drop),
            "final_clean_chunks_retained": len(_cleaned_chunks),
        },
        "resolved_contradictions": resolved_contradictions
    }
    
    # Write summary report
    report_path = Path(settings.output_dir) / "mcp_clean_report.json"
    try:
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save mcp_clean_report: {e}")

    out_str = (
        f"🧹 **Dataset Ingested & Cleaned Successfully!**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📁 **Source Folder:** `{_kb_path}`\n"
        f"📄 **Raw Chunks Found:** `{total_raw_chunks}`\n"
        f"🗑️ **Exact Duplicates Removed:** `{exact_duplicates_removed}`\n"
        f"⚔️ **Contradictory Chunks Removed:** `{len(ids_to_drop)}`\n"
        f"✅ **Clean Active Chunks Remaining:** `{len(_cleaned_chunks)}`\n\n"
    )
    
    if resolved_contradictions:
        out_str += "🔍 **Resolved Contradiction Log:**\n"
        for idx, item in enumerate(resolved_contradictions, 1):
            out_str += (
                f"  {idx}. Kept: `{Path(item['kept']).name}` -> `{item['kept_section']}`\n"
                f"     Dropped: `{Path(item['dropped']).name}` -> `{item['dropped_section']}`\n"
                f"     Reason: {item['reason']} (Confidence: {item['probability']:.2f})\n"
            )
            
    return out_str


@mcp.tool()
def ask_grounded_question(query: str) -> str:
    """Submit a question to query strictly the active cleaned dataset, preventing hallucinations.
    
    Args:
        query: Your question about the dataset (e.g. 'What is the VPN session timeout?').
    """
    global _cleaned_chunks, _generator
    
    # Load cleaned chunks from disk if memory state is empty
    if not _cleaned_chunks:
        cleaned_path = Path(settings.output_dir) / "cleaned_chunks.json"
        if cleaned_path.exists():
            try:
                with cleaned_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    _cleaned_chunks = [DocumentChunk(**item) for item in data]
                # Refit retriever
                retriever = _get_retriever()
                retriever.fit(_cleaned_chunks)
            except Exception as e:
                logger.error(f"Error restoring cleaned chunks: {e}")
                
    if not _cleaned_chunks:
        return (
            "⚠️ No cleaned dataset active. Please configure your dataset path using "
            "`set_knowledge_base_path` and run `clean_and_index_dataset` first!"
        )

    retriever = _get_retriever()
    try:
        results = retriever.retrieve(query, top_k=4)
    except Exception as e:
        return f"❌ Error performing retrieval: {e}"

    if not results:
        return "❌ No grounded evidence found in the cleaned dataset to answer this question."

    # If Groq is connected, generate grounded response
    if _generator:
        try:
            response = _generator.generate(query, results)
            
            # Format output nicely with citations
            citations_str = "\n\n📚 **Cleaned Sources Cited:**\n"
            for idx, res in enumerate(results, start=1):
                citations_str += (
                    f"[{idx}] `{Path(res.source.path).name}` | "
                    f"Section: `{res.source.section}` (Relevance: {res.score:.3f})\n"
                )
            return response + citations_str
        except Exception as e:
            logger.error(f"Generation error: {e}")
            # Fall back to retrieval only
            pass

    # Fallback to pure retrieval with clean chunks if Groq not configured
    out_str = (
        "🤖 **Grounded Retrieval-Only Answers (LLM Generator Offline)**\n"
        "Here are the most relevant clean chunks found in the dataset:\n\n"
    )
    for idx, res in enumerate(results, start=1):
        out_str += (
            f"**[{idx}] Source:** `{Path(res.source.path).name}` | Section: `{res.source.section}`\n"
            f"📄 **Content:** {res.text.strip()}\n"
            f"📈 **Relevance Score:** {res.score:.3f}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        )
    return out_str


@mcp.tool()
def get_cleaned_dataset_summary() -> str:
    """Fetch current metadata and details of the active cleaned dataset."""
    global _cleaned_chunks
    cleaned_path = Path(settings.output_dir) / "cleaned_chunks.json"
    
    # Try restoring if empty in memory
    if not _cleaned_chunks and cleaned_path.exists():
        try:
            with cleaned_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                _cleaned_chunks = [DocumentChunk(**item) for item in data]
        except Exception:
            pass

    if not _cleaned_chunks:
        return "⚠️ No active cleaned dataset. Use `clean_and_index_dataset` to index and clean one."

    # Group by file source
    sources = {}
    for chunk in _cleaned_chunks:
        filename = Path(chunk.metadata.path).name
        sources[filename] = sources.get(filename, 0) + 1

    sources_str = "\n".join(f" - `{name}`: {count} clean chunks" for name, count in sources.items())
    
    return (
        f"📊 **Active Cleaned Dataset Summary:**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📂 **Active Directory:** `{_kb_path}`\n"
        f"✅ **Total Clean Chunks Retained:** `{len(_cleaned_chunks)}`\n"
        f"📄 **Active Files Contained:**\n{sources_str}"
    )


# Expose resource endpoint for external audit report
@mcp.resource("audit://report")
def get_report_resource() -> str:
    """Get the latest audit report summary JSON."""
    report_path = Path(settings.output_dir) / "mcp_clean_report.json"
    if report_path.exists():
        return report_path.read_text(encoding="utf-8")
    return json.dumps({"error": "No audit report generated yet. Run clean_and_index_dataset first."})


@mcp.resource("audit://cleaned_chunks")
def get_cleaned_chunks_resource() -> str:
    """Get the raw list of clean active chunks."""
    cleaned_path = Path(settings.output_dir) / "cleaned_chunks.json"
    if cleaned_path.exists():
        return cleaned_path.read_text(encoding="utf-8")
    return json.dumps({"error": "No clean dataset generated yet. Run clean_and_index_dataset first."})


if __name__ == "__main__":
    mcp.run()
