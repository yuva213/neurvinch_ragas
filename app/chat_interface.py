from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from neurvinch.indexing import StructuralIndexer
from neurvinch.config import settings
from neurvinch.retrieval import HybridRetriever
from neurvinch.generative import GroqGenerator


st.set_page_config(page_title="Neurvinch Chat Tester", layout="centered")
st.title("Neurvinch Chat Tester")
st.caption("AI-powered grounded answers from your audited knowledge base.")

# Initialize components
indexer = StructuralIndexer(ROOT / "data" / "kb")
_, chunks = indexer.index()

retriever = HybridRetriever(
    embedding_model_name=settings.embedding_model,
    embedding_backend=settings.embedding_backend,
    top_k_candidates=20,
    top_k_final=4,
)
retriever.fit(chunks)

# Initialize Groq generator
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
    st.warning("⚠️ Groq API key not configured. Set GROQ_API_KEY in .env to enable AI generation. Showing retrieval results only.")

query = st.text_input("Your question", placeholder="What is the account lockout policy?")
if query:
    results = retriever.retrieve(query, top_k=4)
    if not results:
        st.warning("No grounded evidence found.")
    else:
        if groq_enabled:
            st.subheader("AI-Generated Response")
            with st.spinner("Generating response..."):
                response = generator.generate(query, results)
            st.markdown(response)
            
            with st.expander("📚 View Source Evidence"):
                st.write("Here is the relevant evidence from your KB:")
                for idx, result in enumerate(results, start=1):
                    source = f"{result.source.path} | {result.source.section}"
                    st.markdown(f"**[{idx}]** {result.text}")
                    st.caption(f"Source: {source} | relevance={result.score:.3f}")
        else:
            st.subheader("Grounded Response (Retrieval Only)")
            st.info("Enable Groq API for AI-generated responses.")
            st.write("Here is the most relevant evidence from your KB:")
            for idx, result in enumerate(results, start=1):
                source = f"{result.source.path} | {result.source.section}"
                st.markdown(f"**{idx}.** {result.text}")
                st.caption(f"Source: {source} | score={result.score:.3f}")
