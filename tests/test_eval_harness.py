"""Acceptance tests for Module 5.5: Benchmark Evaluation Harness."""

from pathlib import Path
from layer5_evaluation.baseline_no_rag import NoRAGFinding, NoRAGReview
from layer5_evaluation.baseline_naive_rag import NaiveRAGFinding, NaiveRAGReview
from layer3_agents.planner import SubClaims
from layer3_agents.analyzer import DraftReview, FindingModel
from layer3_agents.reflection import ReflectionResult
from layer5_evaluation.run_eval import run_full_eval


class MockEvalLLM:
    def __init__(self, schema=None):
        self.schema = schema

    def with_structured_output(self, schema):
        return MockEvalLLM(schema=schema)

    def invoke(self, messages):
        schema_name = getattr(self.schema, "__name__", str(self.schema))
        if "SubClaims" in schema_name:
            return SubClaims(
                sub_claims=["check Single Responsibility Principle", "check SQL injection"]
            )
        elif "NoRAG" in schema_name:
            return NoRAGReview(
                findings=[
                    NoRAGFinding(
                        principle="SRP",
                        severity="high",
                        location="line 10",
                        explanation="Handles multiple concerns",
                        suggested_fix="Split class",
                    )
                ]
            )
        elif "NaiveRAG" in schema_name:
            return NaiveRAGReview(
                findings=[
                    NaiveRAGFinding(
                        principle="SRP",
                        evidence_chunk_id="solid_chunk_001",
                        severity="high",
                        location="line 10",
                        explanation="Single responsibility violation",
                        suggested_fix="Split class",
                    )
                ]
            )
        elif "DraftReview" in schema_name:
            return DraftReview(
                findings=[
                    FindingModel(
                        principle="SRP",
                        evidence_chunk_id="tool:ast",
                        severity="high",
                        location="line 10",
                        explanation="Class violates SRP",
                        suggested_fix="Split class",
                    )
                ]
            )
        elif "ReflectionResult" in schema_name:
            return ReflectionResult(notes=["Clean findings"], needs_revision=False)

        return {}


def test_run_full_eval_generates_csv_and_metrics(tmp_path):
    out_csv = tmp_path / "test_results.csv"

    summary = run_full_eval(
        test_set_dir="layer5_evaluation/test_set",
        backends=["mock-test-model"],
        out_csv=str(out_csv),
        num_runs=2,
        systems=["no_rag", "naive_rag", "agentic"],
        llm_factory=lambda model_name: MockEvalLLM(),
        file_subset=["file_01.py", "file_02.py"],
    )

    assert len(summary) == 3  # 3 systems
    assert out_csv.exists()

    content = out_csv.read_text(encoding="utf-8")
    assert "system,backend,avg_detection_recall" in content
    assert "no_rag" in content
    assert "naive_rag" in content
    assert "agentic" in content

    for row in summary:
        assert "avg_detection_recall" in row
        assert "avg_precision" in row
        assert "avg_f1" in row
        assert "avg_consistency" in row
        assert "avg_latency_sec" in row
