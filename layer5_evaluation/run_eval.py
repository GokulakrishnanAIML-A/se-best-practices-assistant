"""Module 5.5: Evaluation Benchmark Runner and Comparative Reporter."""

import os
import csv
import json
import time
import logging
from pathlib import Path
from typing import Any

from layer1_data.retriever import KnowledgeRetriever
from layer4_orchestration.config import PipelineConfig, get_llm
from layer4_orchestration.graph import build_graph
from layer4_orchestration.run import run_review
from layer5_evaluation.baseline_no_rag import review_no_rag
from layer5_evaluation.baseline_naive_rag import review_naive_rag
from layer5_evaluation.metrics import (
    detection_recall,
    detection_precision,
    f1_score,
    groundedness,
    consistency,
)

logger = logging.getLogger(__name__)


def run_single_system(
    system_name: str,
    code: str,
    retriever: KnowledgeRetriever,
    llm: Any,
    app: Any = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Execute a single run for a given system variant."""
    if system_name == "no_rag":
        findings = review_no_rag(code=code, llm=llm)
        return findings, {}
    elif system_name == "naive_rag":
        findings = review_naive_rag(code=code, retriever=retriever, llm=llm)
        # Load flat chunks for groundedness evaluation
        chunks = retriever.search(code[:2000], k=5, mode="hybrid")
        return findings, {"naive_chunks": chunks}
    elif system_name == "agentic":
        if app is None:
            app = build_graph(retriever=retriever, planner_llm=llm, analyzer_llm=llm, reflection_llm=llm)
        review_res = run_review(code=code, app=app)
        return review_res["findings"], review_res.get("state", {}).get("retrieved", {})
    else:
        raise ValueError(f"Unknown system name: {system_name}")


def run_full_eval(
    test_set_dir: str = "layer5_evaluation/test_set",
    backends: list[str] | None = None,
    out_csv: str = "layer5_evaluation/results.csv",
    num_runs: int = 3,
    systems: list[str] | None = None,
    llm_factory: Any = None,
    file_subset: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Execute complete benchmark evaluation comparing No-RAG, Naive RAG, and Agentic RAG.

    Args:
        test_set_dir: Path to benchmark test set directory.
        backends: List of model identifiers to test.
        out_csv: Destination CSV file path.
        num_runs: Number of repeated runs per file for consistency measurement.
        systems: List of systems to evaluate (['no_rag', 'naive_rag', 'agentic']).
        llm_factory: Optional callable(model_name) -> LLM instance for testing.
        file_subset: Optional list of filenames to restrict evaluation to.

    Returns:
        Aggregated summary rows across all evaluated systems and backends.
    """
    if backends is None:
        backends = ["claude-sonnet-4-6"]
    if systems is None:
        systems = ["no_rag", "naive_rag", "agentic"]

    test_dir = Path(test_set_dir)
    if not test_dir.is_absolute():
        test_dir = (Path(__file__).resolve().parent.parent / test_set_dir).resolve()

    labels_file = test_dir / "labels.json"

    if not labels_file.exists():
        raise FileNotFoundError(f"labels.json not found in {test_dir}")

    with open(labels_file, "r", encoding="utf-8") as f:
        labels_map = json.load(f)

    if file_subset:
        labels_map = {k: v for k, v in labels_map.items() if k in file_subset}

    retriever = KnowledgeRetriever()
    results_summary: list[dict[str, Any]] = []

    for backend in backends:
        llm = llm_factory(backend) if llm_factory else get_llm(backend)

        for sys_name in systems:
            logger.info(f"--- Benchmarking System: {sys_name} | Backend: {backend} ---")

            file_recalls: list[float] = []
            file_precisions: list[float] = []
            file_f1s: list[float] = []
            file_groundedness: list[float] = []
            file_consistencies: list[float] = []
            file_latencies: list[float] = []

            for filename, gt_violations in labels_map.items():
                file_path = test_dir / filename
                if not file_path.exists():
                    continue

                code = file_path.read_text(encoding="utf-8")
                runs_findings: list[list[dict[str, Any]]] = []
                runs_latencies: list[float] = []
                runs_retrieved: list[dict[str, Any]] = []

                # Build pre-compiled graph for agentic system if needed
                agentic_app = None
                if sys_name == "agentic":
                    agentic_app = build_graph(
                        retriever=retriever,
                        planner_llm=llm,
                        analyzer_llm=llm,
                        reflection_llm=llm,
                    )

                for run_idx in range(num_runs):
                    t0 = time.perf_counter()
                    findings, retrieved = run_single_system(
                        system_name=sys_name,
                        code=code,
                        retriever=retriever,
                        llm=llm,
                        app=agentic_app,
                    )
                    latency = time.perf_counter() - t0

                    runs_findings.append(findings)
                    runs_latencies.append(latency)
                    runs_retrieved.append(retrieved)

                    # Compute single-run metrics
                    rec = detection_recall(findings, gt_violations)
                    prec = detection_precision(findings, gt_violations)
                    f1 = f1_score(prec, rec)

                    file_recalls.append(rec)
                    file_precisions.append(prec)
                    file_f1s.append(f1)
                    file_latencies.append(latency)

                    if sys_name == "no_rag":
                        file_groundedness.append(0.0)  # No citations in no-RAG baseline
                    else:
                        g_score = groundedness(findings, retrieved)
                        file_groundedness.append(g_score)

                # Compute consistency across the repeated runs for this file
                file_consistency = consistency(runs_findings)
                file_consistencies.append(file_consistency)

            avg_rec = sum(file_recalls) / len(file_recalls) if file_recalls else 0.0
            avg_prec = sum(file_precisions) / len(file_precisions) if file_precisions else 0.0
            avg_f1 = sum(file_f1s) / len(file_f1s) if file_f1s else 0.0
            avg_ground = sum(file_groundedness) / len(file_groundedness) if file_groundedness else 0.0
            avg_cons = sum(file_consistencies) / len(file_consistencies) if file_consistencies else 0.0
            avg_lat = sum(file_latencies) / len(file_latencies) if file_latencies else 0.0

            summary_row = {
                "system": sys_name,
                "backend": backend,
                "avg_detection_recall": round(avg_rec, 4),
                "avg_precision": round(avg_prec, 4),
                "avg_f1": round(avg_f1, 4),
                "avg_groundedness": round(avg_ground, 4),
                "avg_consistency": round(avg_cons, 4),
                "avg_latency_sec": round(avg_lat, 4),
            }
            results_summary.append(summary_row)

    # Write summary CSV
    out_path = Path(out_csv)
    if not out_path.is_absolute():
        out_path = (Path(__file__).resolve().parent.parent / out_csv).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "system",
                "backend",
                "avg_detection_recall",
                "avg_precision",
                "avg_f1",
                "avg_groundedness",
                "avg_consistency",
                "avg_latency_sec",
            ],
        )
        writer.writeheader()
        writer.writerows(results_summary)

    logger.info(f"Evaluation results written to {out_csv}")
    return results_summary
