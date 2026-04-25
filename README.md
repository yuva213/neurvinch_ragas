# Neurvinch

Neurvinch is an AI-driven Knowledge Audit and Hybrid RAG system designed to reduce hallucinations in enterprise knowledge assistants.

## What this MVP includes

- Structural page/document indexer (vectorless metadata-first index)
- NLI-based contradiction auditor
- Latent intent discovery via query clustering
- Hybrid retrieval (BM25 + semantic reranking)
- Streamlit manager dashboard with health indicators

## Quick start

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy env file and edit if needed:

```bash
copy .env.example .env
```

4. Run the pipeline:

```bash
python run_pipeline.py
```

By default, the pipeline runs with lightweight local backends (`tfidf` embeddings + `heuristic` NLI)
for broad environment compatibility.

To opt into transformer-based models, update `.env`:

```bash
NEURVINCH_EMBEDDING_BACKEND=sentence-transformers
NEURVINCH_NLI_BACKEND=cross-encoder
```

5. Start the dashboard:

```bash
streamlit run app/manager_dashboard.py
```

## Project layout

- `src/neurvinch/indexing`: Structural ingestion and indexing
- `src/neurvinch/audit`: Contradiction auditing (NLI)
- `src/neurvinch/intents`: Gap analysis from query logs
- `src/neurvinch/retrieval`: Hybrid retrieval engine
- `app`: Streamlit UIs
- `data`: Input knowledge base and query logs
- `outputs`: Generated audit artifacts and reports
