from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from neurvinch.config import settings
from neurvinch.generative import GroqGenerator
from neurvinch.indexing import StructuralIndexer
from neurvinch.retrieval import HybridRetriever


def load_heldout(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_traces(dataset: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexer = StructuralIndexer(settings.kb_path)
    _, chunks = indexer.index()

    retriever = HybridRetriever(
        embedding_model_name=settings.embedding_model,
        embedding_backend=settings.embedding_backend,
        top_k_candidates=settings.top_k_candidates,
        top_k_final=settings.top_k_final,
    )
    retriever.fit(chunks)

    generator = GroqGenerator(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )

    traces: list[dict[str, Any]] = []
    for sample in dataset:
        question = str(sample["question"])
        ground_truth = str(sample["ground_truth"])
        expected_source = str(sample["expected_source"])

        results = retriever.retrieve(question, top_k=4)
        answer = generator.generate(question, results)
        contexts = [item.text for item in results]
        sources = [str(item.source.path) for item in results]
        source_hit = int(any(expected_source.lower() in path.lower() for path in sources))

        traces.append(
            {
                "question": question,
                "ground_truth": ground_truth,
                "expected_source": expected_source,
                "answer": answer,
                "contexts": contexts,
                "sources": sources,
                "source_hit": source_hit,
            }
        )

    return traces


def evaluate_with_ragas(traces: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        from datasets import Dataset
        from langchain_openai import ChatOpenAI
        from ragas import evaluate
    except Exception as e:
        return {
            "status": "skipped",
            "reason": f"Missing dependency for Ragas evaluation: {e}",
            "metrics": {},
        }

    rows = [
        {
            "question": item["question"],
            "answer": item["answer"],
            "contexts": item["contexts"],
            "ground_truth": item["ground_truth"],
        }
        for item in traces
    ]
    dataset = Dataset.from_list(rows)

    # Ragas may internally expect OpenAI-style env vars even with custom llm objects.
    os.environ.setdefault("OPENAI_API_KEY", settings.llm_api_key)
    os.environ.setdefault("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")

    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.0,
    )

    metrics = []
    metric_names = []

    try:
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics.collections import Faithfulness

        metrics = [Faithfulness(llm=LangchainLLMWrapper(llm))]
        metric_names = ["faithfulness"]
    except Exception:
        try:
            from ragas.metrics import faithfulness

            metrics = [faithfulness]
            metric_names = ["faithfulness"]
        except Exception as e:
            return {
                "status": "skipped",
                "reason": f"Could not import Ragas metrics: {e}",
                "metrics": {},
            }

    try:
        result = evaluate(dataset, metrics=metrics, llm=llm)
    except Exception as e:
        return {
            "status": "failed",
            "reason": f"Ragas evaluate failed: {e}",
            "metrics": {},
            "attempted_metrics": metric_names,
        }

    metrics_dict: dict[str, Any]
    if hasattr(result, "to_dict"):
        metrics_dict = dict(result.to_dict())
    else:
        metrics_dict = {"raw": str(result)}

    return {
        "status": "ok",
        "metrics": metrics_dict,
        "attempted_metrics": metric_names,
    }


def main() -> None:
    heldout_path = ROOT / "data" / "eval" / "qa_heldout.json"
    traces_path = ROOT / "outputs" / "eval" / "qa_traces.json"
    ragas_path = ROOT / "outputs" / "eval" / "ragas_metrics.json"

    if not heldout_path.exists():
        raise FileNotFoundError("data/eval/qa_heldout.json is missing.")

    if not settings.llm_api_key:
        output = {
            "samples": 0,
            "source_hit_rate": 0.0,
            "llm_model": settings.llm_model,
            "ragas": {
                "status": "skipped",
                "reason": "GROQ_API_KEY is not configured. Set it in .env to run trace generation and ragas metrics.",
                "metrics": {},
            },
        }
        ragas_path.parent.mkdir(parents=True, exist_ok=True)
        with ragas_path.open("w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        print("Held-out QA tracing skipped.")
        print("- ragas_status: skipped")
        print("- reason: GROQ_API_KEY is not configured")
        print(f"Saved metrics: {ragas_path}")
        return

    dataset = load_heldout(heldout_path)
    traces = build_traces(dataset)

    traces_path.parent.mkdir(parents=True, exist_ok=True)
    with traces_path.open("w", encoding="utf-8") as f:
        json.dump(traces, f, indent=2)

    source_hit_rate = sum(item["source_hit"] for item in traces) / max(len(traces), 1)
    ragas_eval = evaluate_with_ragas(traces)

    output = {
        "samples": len(traces),
        "source_hit_rate": round(source_hit_rate, 4),
        "llm_model": settings.llm_model,
        "ragas": ragas_eval,
    }

    with ragas_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print("Held-out QA tracing completed.")
    print(f"- samples: {len(traces)}")
    print(f"- source_hit_rate: {round(source_hit_rate, 4)}")
    print(f"- ragas_status: {ragas_eval.get('status')}")
    if ragas_eval.get("status") != "ok":
        print(f"- ragas_reason: {ragas_eval.get('reason', 'n/a')}")
    print(f"Saved traces: {traces_path}")
    print(f"Saved metrics: {ragas_path}")


if __name__ == "__main__":
    main()
