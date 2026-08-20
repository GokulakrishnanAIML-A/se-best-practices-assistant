"""Acceptance tests for Module 3.4: Analyzer Agent & Hallucination Guard."""

import pytest
from layer3_agents.analyzer import DraftReview, FindingModel, analyze


class MockLLMForAnalyzer:
    def __init__(self, findings: list[FindingModel]):
        self.findings = findings

    def with_structured_output(self, schema):
        return self

    def invoke(self, inputs):
        return DraftReview(findings=self.findings)


def test_analyze_drops_findings_with_fabricated_chunk_id():
    code = "def query_db(user_input): return db.execute(f'SELECT * FROM users WHERE id={user_input}')"
    sub_claims = ["check for SQL injection"]
    retrieved = {
        "check for SQL injection": [
            {"id": "owasp_chunk_001", "source": "owasp", "text": "Avoid string concatenation in SQL queries."}
        ]
    }
    tool_findings = {}

    # Mock LLM returns one valid chunk ID and one hallucinated chunk ID
    mock_llm = MockLLMForAnalyzer(
        [
            FindingModel(
                principle="OWASP-Injection",
                evidence_chunk_id="owasp_chunk_001",
                severity="high",
                location="line 1",
                explanation="Raw SQL concatenation detected.",
                suggested_fix="Use parameterized queries.",
            ),
            FindingModel(
                principle="Fabricated Rule",
                evidence_chunk_id="fake_chunk_999_never_existed",
                severity="medium",
                location="line 1",
                explanation="This should be dropped by hallucination guard.",
                suggested_fix="None.",
            ),
        ]
    )

    findings = analyze(code, sub_claims, retrieved, tool_findings, llm=mock_llm)
    assert len(findings) == 1
    assert findings[0]["evidence_chunk_id"] == "owasp_chunk_001"
    assert findings[0]["principle"] == "OWASP-Injection"


def test_analyze_accepts_tool_prefixed_evidence():
    code = "class GodClass:\n    pass"
    sub_claims = ["check class size"]
    retrieved = {}
    tool_findings = {"structure": {"classes": [{"name": "GodClass", "method_count": 25}]}}

    mock_llm = MockLLMForAnalyzer(
        [
            FindingModel(
                principle="SRP",
                evidence_chunk_id="tool:ast",
                severity="high",
                location="GodClass",
                explanation="Class has too many methods.",
                suggested_fix="Decompose into specialized components.",
            )
        ]
    )

    findings = analyze(code, sub_claims, retrieved, tool_findings, llm=mock_llm)
    assert len(findings) == 1
    assert findings[0]["evidence_chunk_id"] == "tool:ast"


def test_analyze_empty_code_returns_empty():
    findings = analyze("", [], {}, {}, llm=None)
    assert findings == []
