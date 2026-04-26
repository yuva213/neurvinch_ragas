#!/usr/bin/env python
"""Judge/reviewer-friendly MVP verification script.

Quick mode (default):
  - validates config/imports/retrieval

Full mode (--full):
  - runs pipeline, contradiction benchmark, regression tests, and ragas trace eval
  - writes outputs/eval/reviewer_summary.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
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


def run_cmd(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    return {
        "command": " ".join(command),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "ok": completed.returncode == 0,
    }


def quick_checks() -> dict[str, Any]:
    indexer = StructuralIndexer(settings.kb_path)
    _, chunks = indexer.index()

    retriever = HybridRetriever(
        embedding_model_name=settings.embedding_model,
        embedding_backend=settings.embedding_backend,
        top_k_candidates=settings.top_k_candidates,
        top_k_final=settings.top_k_final,
    )
    retriever.fit(chunks)

    query = "What is the password reset procedure?"
    retrieval_results = retriever.retrieve(query, top_k=3)

    llm_status = {"configured": bool(settings.llm_api_key), "connected": False, "error": None}
    if settings.llm_api_key:
        try:
            GroqGenerator(
                api_key=settings.llm_api_key,
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )
            llm_status["connected"] = True
        except Exception as e:
            llm_status["error"] = str(e)

    report_path = ROOT / "outputs" / "report.json"
    report = {}
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))

    return {
        "config": {
            "llm_provider": settings.llm_provider,
            "llm_model": settings.llm_model,
            "embedding_backend": settings.embedding_backend,
            "nli_backend": settings.nli_backend,
        },
        "kb": {
            "total_chunks_indexed": len(chunks),
            "top_retrieval_result": retrieval_results[0].source.path if retrieval_results else None,
            "top_retrieval_score": round(retrieval_results[0].score, 4) if retrieval_results else 0.0,
        },
        "llm": llm_status,
        "latest_report": {
            "knowledge_health_score": report.get("knowledge_health_score"),
            "total_chunks": report.get("total_chunks"),
            "contradictions": report.get("contradictions"),
            "void_clusters": report.get("void_clusters"),
        },
    }


def full_checks() -> dict[str, Any]:
    steps = [
        ("pipeline", [sys.executable, "run_pipeline.py"]),
        ("contradiction_benchmark", [sys.executable, "run_contradiction_benchmark.py"]),
        ("regression_tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"]),
    ]

    if settings.llm_api_key:
        steps.append(("ragas_eval", [sys.executable, "run_ragas_eval.py"]))

    results = {}
    for name, command in steps:
        results[name] = run_cmd(command)

    ragas_skipped = not settings.llm_api_key
    if ragas_skipped:
        results["ragas_eval"] = {
            "command": f"{sys.executable} run_ragas_eval.py",
            "exit_code": 0,
            "stdout": "Skipped because GROQ_API_KEY is not configured.",
            "stderr": "",
            "ok": True,
            "skipped": True,
        }

    all_ok = all(item.get("ok", False) for item in results.values())
    return {"all_ok": all_ok, "steps": results}


def print_summary(summary: dict[str, Any], full: bool) -> None:
    print("=" * 68)
    print("NEURVINCH MVP REVIEW SUMMARY")
    print("=" * 68)
    print("\nCore Runtime")
    print(f"- llm_provider: {summary['quick']['config']['llm_provider']}")
    print(f"- llm_model: {summary['quick']['config']['llm_model']}")
    print(f"- embedding_backend: {summary['quick']['config']['embedding_backend']}")
    print(f"- nli_backend: {summary['quick']['config']['nli_backend']}")
    print(f"- chunks_indexed: {summary['quick']['kb']['total_chunks_indexed']}")
    print(f"- top_retrieval_result: {summary['quick']['kb']['top_retrieval_result']}")
    print(f"- llm_connected: {summary['quick']['llm']['connected']}")

    latest = summary["quick"]["latest_report"]
    print("\nLatest Report")
    print(f"- knowledge_health_score: {latest.get('knowledge_health_score')}")
    print(f"- total_chunks: {latest.get('total_chunks')}")
    print(f"- contradictions: {latest.get('contradictions')}")
    print(f"- void_clusters: {latest.get('void_clusters')}")

    if full:
        print("\nFull Validation")
        print(f"- overall_status: {'PASS' if summary['full']['all_ok'] else 'FAIL'}")
        for name, result in summary["full"]["steps"].items():
            state = "PASS" if result.get("ok") else "FAIL"
            if result.get("skipped"):
                state = "SKIP"
            print(f"- {name}: {state} (exit_code={result.get('exit_code')})")

    print("\nArtifacts")
    print("- outputs/report.json")
    print("- outputs/eval/contradiction_benchmark.json")
    print("- outputs/eval/qa_traces.json")
    print("- outputs/eval/ragas_metrics.json")
    print("- outputs/eval/reviewer_summary.json")
    print("=" * 68)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Neurvinch MVP for judge/reviewer submission.")
    parser.add_argument("--full", action="store_true", help="Run pipeline, benchmark, tests, and ragas eval.")
    args = parser.parse_args()

    summary: dict[str, Any] = {
        "quick": quick_checks(),
    }
    if args.full:
        summary["full"] = full_checks()

    out_path = ROOT / "outputs" / "eval" / "reviewer_summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print_summary(summary, full=args.full)

    if args.full and not summary["full"]["all_ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
