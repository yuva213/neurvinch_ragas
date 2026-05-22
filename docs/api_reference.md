# API & Configuration Reference — Neurvinch AI RAG

## Table of Contents
1. [Environment Variables](#environment-variables)
2. [Pydantic Models Reference](#pydantic-models-reference)
3. [Output Artifacts](#output-artifacts)
4. [CLI Scripts Reference](#cli-scripts-reference)

---

## Environment Variables

All configuration is read by `src/neurvinch/config.py` via a Pydantic `BaseSettings` class. Values can be set in a `.env` file at the project root or as real environment variables. Environment variables take precedence over `.env` values.

### Quick-start `.env` template

```dotenv
GROQ_API_KEY=gsk_...

# Optional overrides — defaults shown
NEURVINCH_LLM_PROVIDER=groq
NEURVINCH_LLM_MODEL=llama-3.1-8b-instant
NEURVINCH_LLM_TEMPERATURE=0.7
NEURVINCH_LLM_MAX_TOKENS=1024
NEURVINCH_KB_PATH=data/kb
NEURVINCH_QUERY_LOG_PATH=data/queries/query_logs.csv
NEURVINCH_OUTPUT_DIR=outputs
NEURVINCH_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
NEURVINCH_EMBEDDING_BACKEND=tfidf
NEURVINCH_NLI_MODEL=cross-encoder/nli-deberta-v3-base
NEURVINCH_NLI_BACKEND=heuristic
NEURVINCH_CONTRADICTION_THRESHOLD=0.85
NEURVINCH_VOID_RETRIEVAL_THRESHOLD=0.35
NEURVINCH_DBSCAN_EPS=0.4
NEURVINCH_DBSCAN_MIN_SAMPLES=8
```

---

### Full Variable Reference

#### LLM Settings

| Variable | Default | Type | Description |
|---|---|---|---|
| `GROQ_API_KEY` | *(required)* | `str` | API key for the Groq cloud service. Obtain from [console.groq.com](https://console.groq.com). The system will raise `ConfigError` at startup if this is unset. |
| `NEURVINCH_LLM_PROVIDER` | `groq` | `str` | LLM provider identifier. Currently only `groq` is supported. Placeholder for future providers (e.g., `openai`, `anthropic`). |
| `NEURVINCH_LLM_MODEL` | `llama-3.1-8b-instant` | `str` | Model ID passed verbatim to the provider API. Any Groq-hosted model name is valid (e.g., `llama-3.1-70b-versatile`, `mixtral-8x7b-32768`). |
| `NEURVINCH_LLM_TEMPERATURE` | `0.7` | `float` | Sampling temperature for generation. `0.0` = deterministic/greedy, `1.0` = highly creative. Values above `1.0` may produce incoherent output. |
| `NEURVINCH_LLM_MAX_TOKENS` | `1024` | `int` | Maximum number of tokens in the generated answer. Increase for long-form answers; decrease to reduce cost and latency. |

---

#### Storage Paths

| Variable | Default | Type | Description |
|---|---|---|---|
| `NEURVINCH_KB_PATH` | `data/kb` | `str` | Root directory for knowledge-base files. The indexer scans this directory recursively for `.txt`, `.pdf`, and `.docx` files. Can be overridden at runtime via the `set_knowledge_base_path` MCP tool. |
| `NEURVINCH_QUERY_LOG_PATH` | `data/queries/query_logs.csv` | `str` | Path to the CSV file where every query and its answer are appended. Parent directory is created automatically if missing. |
| `NEURVINCH_OUTPUT_DIR` | `outputs` | `str` | Directory where the indexer writes `chunks.json` and the auditor writes `audit_report.json`. Created automatically if missing. |

---

#### Embedding Settings

| Variable | Default | Options | Description |
|---|---|---|---|
| `NEURVINCH_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Any HuggingFace model ID | Model used when `NEURVINCH_EMBEDDING_BACKEND=sentence-transformers`. Ignored when backend is `tfidf`. The model is downloaded from HuggingFace Hub on first use and cached locally. |
| `NEURVINCH_EMBEDDING_BACKEND` | `tfidf` | `tfidf` / `sentence-transformers` | Selects the embedding implementation. `tfidf` uses `sklearn.TfidfVectorizer` (no GPU, sparse vectors). `sentence-transformers` uses the model specified by `NEURVINCH_EMBEDDING_MODEL` (dense vectors, higher recall quality). **Must be consistent between indexing and query runs.** |

---

#### NLI / Audit Settings

| Variable | Default | Options | Description |
|---|---|---|---|
| `NEURVINCH_NLI_MODEL` | `cross-encoder/nli-deberta-v3-base` | Any cross-encoder NLI model | Cross-encoder model used when `NEURVINCH_NLI_BACKEND=cross-encoder`. Downloads from HuggingFace Hub on first use. Ignored in `heuristic` mode. |
| `NEURVINCH_NLI_BACKEND` | `heuristic` | `heuristic` / `cross-encoder` | Contradiction detection strategy. `heuristic`: flags chunk pairs whose cosine similarity exceeds `NEURVINCH_CONTRADICTION_THRESHOLD` (fast, ~O(n²) dot products). `cross-encoder`: runs each candidate pair through the NLI model for a true entailment/contradiction label (higher precision, much slower). |
| `NEURVINCH_CONTRADICTION_THRESHOLD` | `0.85` | `float` (0.0–1.0) | Cosine similarity cutoff used in `heuristic` mode. Pairs with similarity above this value are assumed to discuss the same topic and are checked for semantic conflict. Raise to reduce false positives; lower to catch more potential contradictions. |
| `NEURVINCH_VOID_RETRIEVAL_THRESHOLD` | `0.35` | `float` (0.0–1.0) | Minimum hybrid retrieval score required to consider a chunk "relevant". Queries where all chunks score below this threshold trigger a void warning in the response. |
| `NEURVINCH_DBSCAN_EPS` | `0.4` | `float` | Epsilon radius for DBSCAN clustering during void discovery. Controls how densely packed embeddings must be to form a cluster. Smaller values → more clusters, more void detection sensitivity. |
| `NEURVINCH_DBSCAN_MIN_SAMPLES` | `8` | `int` | Minimum number of chunks required to form a DBSCAN core cluster. Points in clusters smaller than this are treated as noise / potential voids. Increase for large corpora to avoid spurious voids. |

---

## Pydantic Models Reference

All models live in `src/neurvinch/models.py` and are used throughout the pipeline for structured data exchange.

### `Chunk`

Represents a single text segment extracted from a source document.

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Unique identifier: `{source_stem}_chunk_{index}` |
| `source` | `str` | Filename of the originating document |
| `text` | `str` | Raw text content of the chunk |
| `chunk_index` | `int` | Zero-based position within the source document |
| `char_start` | `int` | Character offset where the chunk begins in the original file |
| `char_end` | `int` | Character offset where the chunk ends in the original file |
| `embedding` | `Optional[List[float]]` | Pre-computed embedding vector; `None` until `EmbeddingEngine.encode()` is called |

---

### `ContradictionPair`

Represents two chunks flagged as semantically contradictory.

| Field | Type | Description |
|---|---|---|
| `chunk_a_id` | `str` | ID of the first chunk |
| `chunk_b_id` | `str` | ID of the second chunk |
| `text_a` | `str` | Text of chunk A |
| `text_b` | `str` | Text of chunk B |
| `score` | `float` | Similarity or NLI contradiction confidence score |
| `method` | `str` | Detection method used: `"heuristic"` or `"cross-encoder"` |

---

### `VoidCluster`

Represents a topic area with insufficient supporting chunks.

| Field | Type | Description |
|---|---|---|
| `cluster_id` | `int` | DBSCAN cluster label (-1 for noise/void points) |
| `representative_text` | `str` | Text of the chunk nearest the cluster centroid |
| `size` | `int` | Number of chunks in this cluster |

---

### `AuditReport`

Top-level audit result written to `outputs/audit_report.json`.

| Field | Type | Description |
|---|---|---|
| `timestamp` | `str` | ISO 8601 datetime of the audit run |
| `total_chunks` | `int` | Total number of chunks processed |
| `clean_chunks` | `int` | Chunks that passed the audit (not in any contradiction pair) |
| `health_score` | `float` | Overall quality score 0–100 |
| `contradictions` | `List[ContradictionPair]` | All flagged contradiction pairs |
| `void_clusters` | `List[VoidCluster]` | All discovered void clusters |
| `embedding_backend` | `str` | Backend used during this run |
| `nli_backend` | `str` | NLI backend used during this run |

---

### `QueryLog`

Row appended to `NEURVINCH_QUERY_LOG_PATH` after each query.

| Field | Type | Description |
|---|---|---|
| `timestamp` | `str` | ISO 8601 datetime of the query |
| `query` | `str` | Original user query text |
| `answer` | `str` | Generated answer |
| `sources` | `str` | Comma-separated list of source filenames cited |
| `retrieval_score` | `float` | Average hybrid score of the top-K retrieved chunks |
| `latency_ms` | `int` | End-to-end latency in milliseconds |

---

### `NeurvinchConfig`

Pydantic `BaseSettings` class. All fields correspond 1:1 with the environment variables documented above.

```python
class NeurvinchConfig(BaseSettings):
    groq_api_key: str
    llm_provider: str = "groq"
    llm_model: str = "llama-3.1-8b-instant"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1024
    kb_path: str = "data/kb"
    query_log_path: str = "data/queries/query_logs.csv"
    output_dir: str = "outputs"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_backend: str = "tfidf"
    nli_model: str = "cross-encoder/nli-deberta-v3-base"
    nli_backend: str = "heuristic"
    contradiction_threshold: float = 0.85
    void_retrieval_threshold: float = 0.35
    dbscan_eps: float = 0.4
    dbscan_min_samples: int = 8

    model_config = SettingsConfigDict(
        env_prefix="NEURVINCH_",
        env_file=".env",
        env_file_encoding="utf-8",
    )
```

The `groq_api_key` field uses `env_prefix=""` override so it reads `GROQ_API_KEY` (not `NEURVINCH_GROQ_API_KEY`).

---

## Output Artifacts

All output files are written to `NEURVINCH_OUTPUT_DIR` (default: `outputs/`).

| File | Format | Contents | Updated by |
|---|---|---|---|
| `outputs/chunks.json` | JSON array | All `Chunk` objects with embeddings after the last successful indexing run | `clean_and_index_dataset` MCP tool / `run_indexer.py` |
| `outputs/audit_report.json` | JSON object | Full `AuditReport` — contradictions, voids, health score, metadata | `clean_and_index_dataset` MCP tool |
| `outputs/clean_chunks.json` | JSON array | Subset of `chunks.json` with contradictory chunks removed — this is what the retriever loads | `clean_and_index_dataset` MCP tool |
| `data/queries/query_logs.csv` | CSV | `QueryLog` rows appended on every `ask_grounded_question` call | `ask_grounded_question` MCP tool / `run_query.py` |

---

## CLI Scripts Reference

### `run_mcp_server.py`

Starts the Neurvinch MCP server over stdio.

```bash
# Standard launch (required for Windows UTF-8 compatibility)
python -X utf8 run_mcp_server.py

# With an explicit KB path via env
NEURVINCH_KB_PATH=./my_docs python -X utf8 run_mcp_server.py
```

**What it does**:
1. Loads `NeurvinchConfig` from environment / `.env`.
2. Instantiates all pipeline components (indexer, auditor, retriever, generator).
3. Starts FastMCP's `asyncio` stdio transport loop.
4. Blocks until the client closes the connection.

---

### `run_indexer.py`

Runs the ingestion + audit pipeline as a standalone batch job without starting the MCP server.

```bash
python run_indexer.py [--kb-path PATH] [--output-dir DIR]
```

| Flag | Default | Description |
|---|---|---|
| `--kb-path` | `NEURVINCH_KB_PATH` env var | Override knowledge-base directory |
| `--output-dir` | `NEURVINCH_OUTPUT_DIR` env var | Override output directory |
| `--backend` | `NEURVINCH_EMBEDDING_BACKEND` env var | Override embedding backend for this run |

**Exit codes**: `0` = success, `1` = configuration error, `2` = no documents found.

---

### `run_query.py`

Executes a single grounded query from the command line and prints the answer.

```bash
python run_query.py "What are the main revenue drivers?"

# With verbose output showing retrieved chunks
python run_query.py --verbose "What are the main revenue drivers?"
```

| Flag | Default | Description |
|---|---|---|
| `--top-k` | `5` | Number of chunks to retrieve |
| `--verbose` | `false` | Print retrieved chunks before the answer |
| `--output` | stdout | Write answer to a file instead of stdout |

**Example output**:
```
Answer:
The main revenue drivers are cloud subscriptions (42%), professional services (31%),
and hardware sales (27%). [Source: annual_report.txt, chunk 7] [Source: q3_earnings.txt, chunk 2]

Latency: 312ms
```

---

### `app/mcp_streamlit_client.py`

Launches the Streamlit chat interface. This script is both the UI and an MCP client.

```bash
streamlit run app/mcp_streamlit_client.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

**Features**:
- Chat interface with conversation history
- File upload panel (calls `upload_document` MCP tool)
- "Re-index" button (calls `clean_and_index_dataset`)
- Audit report viewer (fetches `audit://report` resource)
- Dataset summary panel (calls `get_cleaned_dataset_summary`)

> **Note**: The Streamlit app spawns the MCP server as a subprocess on startup. Ensure `GROQ_API_KEY` is set before launching.
