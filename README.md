# Neurvinch

Neurvinch is an AI-driven Knowledge Audit and Hybrid RAG system designed to reduce hallucinations in enterprise knowledge assistants.

## What this MVP includes

- **Structural page/document indexer** (vectorless metadata-first index)
- **NLI-based contradiction auditor** (detects knowledge conflicts)
- **Latent intent discovery** via query clustering (gap analysis)
- **Hybrid retrieval** (BM25 + semantic reranking with catalog demotion)
- **Groq-powered generative AI** (grounded response generation)
- **Streamlit interfaces** (chat with AI responses, manager dashboard with health metrics)
- **Expanded knowledge base** (internal + 9 external sources + deep-dive documentation)

## Quick start

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create `.env` file with your Groq API key (get free key at https://console.groq.com/keys):

```bash
GROQ_API_KEY=your_api_key_here
```

4. Run the pipeline to index knowledge base and generate audit reports:

```bash
python run_pipeline.py
```

By default, the pipeline runs with lightweight local backends (`tfidf` embeddings + `heuristic` NLI) for broad environment compatibility.

To opt into transformer-based models, update `.env`:

```bash
NEURVINCH_EMBEDDING_BACKEND=sentence-transformers
NEURVINCH_NLI_BACKEND=cross-encoder
```

5. Start the AI-powered chat interface:

```bash
streamlit run app/chat_interface.py
```

This will launch the chat interface with Groq-powered AI generation backed by your audited knowledge base.

6. Or start the manager dashboard for health metrics:

```bash
streamlit run app/manager_dashboard.py
```

## Judge & Reviewer Quick Run

Use these commands for a fast MVP evaluation flow.

1. Configure environment:

```bash
copy .env.example .env
```

2. Add your Groq key in `.env`:

```bash
GROQ_API_KEY=your_api_key_here
```

3. Run full verification (pipeline + benchmark + tests + ragas traces):

```bash
python verify_system.py --full
```

4. Open the generated reviewer summary:

```bash
type outputs\eval\reviewer_summary.json
```

5. (Optional) Launch UI demos:

```bash
python -m streamlit run app/chat_interface.py
python -m streamlit run app/manager_dashboard.py
```

### Expected Review Artifacts

- `outputs/report.json`: overall pipeline score and counts
- `outputs/eval/contradiction_benchmark.json`: heuristic vs transformer contradiction metrics
- `outputs/eval/qa_traces.json`: held-out QA trace records with retrieved contexts/sources
- `outputs/eval/ragas_metrics.json`: Ragas metric output over held-out QA set
- `outputs/eval/reviewer_summary.json`: one-file summary for judges/reviewers

## Project layout

- `src/neurvinch/indexing`: Structural ingestion and indexing
- `src/neurvinch/audit`: Contradiction auditing (NLI)
- `src/neurvinch/intents`: Gap analysis from query logs
- `src/neurvinch/retrieval`: Hybrid retrieval engine (BM25 + semantic reranking)
- `src/neurvinch/generative`: Groq LLM integration for AI response generation
- `app`: Streamlit interfaces (chat, dashboard)
- `data/kb`: Knowledge base (internal docs + 9 external sources + deep-dive pages)
- `outputs`: Generated audit artifacts (chunks, contradictions, void clusters, report)

## Current Knowledge Base

- **Total Chunks**: 91 (expanded from 9 with external sources)
- **Health Score**: 0.9857/1.0 (excellent quality)
- **Contradictions**: 2 detected
- **Coverage**: Policy docs, API references, framework guides, system architecture

### External Sources Indexed

- OpenAI Chat API, Anthropic Claude, LangChain, Python, React, NumPy, Requests, GitHub API, Boto3
- Plus deep-dive pages on React useState, Python asyncio, OpenAI Chat Completions
