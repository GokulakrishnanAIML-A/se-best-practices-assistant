"""Acceptance tests for Module 5.4: Quantitative Evaluation Metrics."""

from layer5_evaluation.metrics import (
    detection_recall,
    detection_precision,
    f1_score,
    groundedness,
    consistency,
    normalize_principle,
)
from layer3_agents.state import Finding


def test_normalize_principle():
    assert normalize_principle("Single Responsibility Principle") == "SRP"
    assert normalize_principle("sql injection") == "OWASP-Injection"
    assert normalize_principle("open/closed") == "OCP"
    assert normalize_principle("liskov substitution") == "LSP"
    assert normalize_principle("dependency inversion") == "DIP"


def test_detection_recall_perfect_match():
    gt = [{"principle": "SRP", "line_range": [1, 10]}]
    pred: list[Finding] = [
        {
            "principle": "SRP",
            "evidence_chunk_id": "none",
            "severity": "medium",
            "location": "line 5",
            "explanation": "Violates SRP",
            "suggested_fix": "Refactor",
        }
    ]
    assert detection_recall(pred, gt) == 1.0


def test_detection_recall_zero_when_nothing_predicted():
    gt = [{"principle": "SRP", "line_range": [1, 10]}]
    assert detection_recall([], gt) == 0.0


def test_detection_recall_fuzzy_principle_alias():
    gt = [{"principle": "OWASP-Injection", "line_range": [15, 20]}]
    pred: list[Finding] = [
        {
            "principle": "SQL Injection",
            "evidence_chunk_id": "tool:bandit",
            "severity": "high",
            "location": "line 17",
            "explanation": "SQL string concatenation",
            "suggested_fix": "Parameterize",
        }
    ]
    assert detection_recall(pred, gt) == 1.0


def test_detection_precision_and_f1():
    gt = [{"principle": "SRP", "line_range": [1, 10]}]
    pred: list[Finding] = [
        {
            "principle": "SRP",
            "evidence_chunk_id": "tool:ast",
            "severity": "high",
            "location": "line 3",
            "explanation": "SRP violation",
            "suggested_fix": "Fix",
        },
        {
            "principle": "OCP",
            "evidence_chunk_id": "tool:ast",
            "severity": "low",
            "location": "line 20",
            "explanation": "False positive OCP",
            "suggested_fix": "Fix",
        },
    ]
    rec = detection_recall(pred, gt)
    prec = detection_precision(pred, gt)
    f1 = f1_score(prec, rec)

    assert rec == 1.0
    assert prec == 0.5
    assert round(f1, 4) == 0.6667


def test_consistency_full_overlap_scores_one():
    same_findings: list[Finding] = [
        {
            "principle": "SRP",
            "evidence_chunk_id": "none",
            "severity": "high",
            "location": "line 1",
            "explanation": "",
            "suggested_fix": "",
        },
        {
            "principle": "DIP",
            "evidence_chunk_id": "none",
            "severity": "high",
            "location": "line 10",
            "explanation": "",
            "suggested_fix": "",
        },
    ]
    assert consistency([same_findings, same_findings, same_findings]) == 1.0


def test_consistency_disjoint_scores_zero():
    run1: list[Finding] = [{"principle": "SRP", "evidence_chunk_id": "none", "severity": "m", "location": "1", "explanation": "", "suggested_fix": ""}]
    run2: list[Finding] = [{"principle": "DIP", "evidence_chunk_id": "none", "severity": "m", "location": "1", "explanation": "", "suggested_fix": ""}]
    assert consistency([run1, run2]) == 0.0


def test_groundedness_validates_chunk_evidence():
    findings: list[Finding] = [
        {
            "principle": "SQL Injection",
            "evidence_chunk_id": "owasp_chunk_001",
            "severity": "high",
            "location": "line 12",
            "explanation": "SQL query concatenation permits injection attack.",
            "suggested_fix": "Use parameters",
        },
        {
            "principle": "DIP",
            "evidence_chunk_id": "tool:ast",  # static tool, skipped from groundedness calculation
            "severity": "medium",
            "location": "line 5",
            "explanation": "Tight coupling",
            "suggested_fix": "Inject",
        },
    ]
    retrieved = {
        "claim": [
            {
                "id": "owasp_chunk_001",
                "text": "SQL Injection prevention requires parameterization of untrusted query inputs.",
            }
        ]
    }

    g_score = groundedness(findings, retrieved)
    assert g_score == 1.0
