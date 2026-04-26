from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import f1_score, precision_score, recall_score

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from neurvinch.audit import NLIAuditor
from neurvinch.config import settings
from neurvinch.models import DocumentChunk


def load_chunks(chunks_path: Path) -> dict[str, DocumentChunk]:
    with chunks_path.open("r", encoding="utf-8") as f:
        rows = json.load(f)
    return {row["id"]: DocumentChunk(**row) for row in rows}


def load_ground_truth(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def contradiction_probability(
    auditor: NLIAuditor,
    chunk_a: DocumentChunk,
    chunk_b: DocumentChunk,
) -> tuple[float, str]:
    if auditor.nli_backend == "cross-encoder":
        try:
            probs_list = auditor._cross_encoder_probabilities([chunk_a, chunk_b], [(0, 1)])
            if probs_list is not None:
                probs = probs_list[0]
                return float(auditor._contradiction_probability(probs)), "cross-encoder"
        except Exception:
            pass

        probs = auditor._heuristic_probs(chunk_a.text, chunk_b.text)
        return float(auditor._contradiction_probability(probs)), "heuristic-fallback"

    probs = auditor._heuristic_probs(chunk_a.text, chunk_b.text)
    return float(auditor._contradiction_probability(probs)), "heuristic"


def evaluate_backend(
    backend: str,
    chunks_by_id: dict[str, DocumentChunk],
    truth_rows: list[dict[str, object]],
) -> dict[str, object]:
    auditor = NLIAuditor(
        embedding_model_name=settings.embedding_model,
        embedding_backend=settings.embedding_backend,
        nli_model_name=settings.nli_model,
        nli_backend=backend,
        contradiction_threshold=settings.contradiction_threshold,
    )

    y_true: list[int] = []
    y_pred: list[int] = []
    pair_traces: list[dict[str, object]] = []
    backends_used: list[str] = []

    for row in truth_rows:
        chunk_a_id = str(row["chunk_a_id"])
        chunk_b_id = str(row["chunk_b_id"])
        label = int(row["label"])

        if chunk_a_id not in chunks_by_id or chunk_b_id not in chunks_by_id:
            continue

        prob, used_backend = contradiction_probability(
            auditor,
            chunks_by_id[chunk_a_id],
            chunks_by_id[chunk_b_id],
        )
        prediction = int(prob >= settings.contradiction_threshold)

        y_true.append(label)
        y_pred.append(prediction)
        backends_used.append(used_backend)
        pair_traces.append(
            {
                "chunk_a_id": chunk_a_id,
                "chunk_b_id": chunk_b_id,
                "label": label,
                "prediction": prediction,
                "contradiction_probability": round(prob, 4),
                "backend_used": used_backend,
                "note": row.get("note", ""),
            }
        )

    if not y_true:
        return {
            "configured_backend": backend,
            "samples": 0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "threshold": settings.contradiction_threshold,
            "backend_usage": {},
            "pairs": [],
        }

    precision = float(precision_score(y_true, y_pred, zero_division=0))
    recall = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    usage: dict[str, int] = {}
    for item in backends_used:
        usage[item] = usage.get(item, 0) + 1

    return {
        "configured_backend": backend,
        "samples": len(y_true),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "threshold": settings.contradiction_threshold,
        "backend_usage": usage,
        "pairs": pair_traces,
    }


def main() -> None:
    chunks_path = ROOT / "outputs" / "chunks.json"
    truth_path = ROOT / "data" / "eval" / "contradiction_ground_truth.json"
    output_path = ROOT / "outputs" / "eval" / "contradiction_benchmark.json"

    if not chunks_path.exists():
        raise FileNotFoundError("outputs/chunks.json is missing. Run `python run_pipeline.py` first.")
    if not truth_path.exists():
        raise FileNotFoundError("data/eval/contradiction_ground_truth.json is missing.")

    chunks_by_id = load_chunks(chunks_path)
    truth_rows = load_ground_truth(truth_path)

    heuristic_result = evaluate_backend("heuristic", chunks_by_id, truth_rows)
    transformer_result = evaluate_backend("cross-encoder", chunks_by_id, truth_rows)

    summary = {
        "threshold": settings.contradiction_threshold,
        "comparison": {
            "heuristic": {
                "precision": heuristic_result["precision"],
                "recall": heuristic_result["recall"],
                "f1": heuristic_result["f1"],
            },
            "cross_encoder": {
                "precision": transformer_result["precision"],
                "recall": transformer_result["recall"],
                "f1": transformer_result["f1"],
            },
        },
        "details": {
            "heuristic": heuristic_result,
            "cross_encoder": transformer_result,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("Contradiction benchmark completed.")
    print(f"- threshold: {settings.contradiction_threshold}")
    print(
        "- heuristic  : "
        f"precision={heuristic_result['precision']}, "
        f"recall={heuristic_result['recall']}, f1={heuristic_result['f1']}"
    )
    print(
        "- cross-encoder: "
        f"precision={transformer_result['precision']}, "
        f"recall={transformer_result['recall']}, f1={transformer_result['f1']}"
    )
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
