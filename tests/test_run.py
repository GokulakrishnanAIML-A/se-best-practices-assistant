"""Acceptance tests for Module 4.3: End-to-End Review Pipeline Entry Point."""

from layer3_agents.planner import SubClaims
from layer3_agents.analyzer import DraftReview, FindingModel
from layer3_agents.reflection import ReflectionResult
from layer4_orchestration.config import PipelineConfig
from layer4_orchestration.graph import build_graph
from layer4_orchestration.run import run_review


class MockPlannerLLM:
    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        return SubClaims(
            sub_claims=[
                "check for Single Responsibility Principle violations",
                "check for SQL injection vulnerabilities",
                "check cyclomatic complexity",
            ]
        )


class MockAnalyzerLLM:
    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        return DraftReview(
            findings=[
                FindingModel(
                    principle="OWASP-Injection",
                    evidence_chunk_id="tool:bandit",
                    severity="high",
                    location="line 12",
                    explanation="Raw SQL string formatting found.",
                    suggested_fix="Use parameterized queries.",
                )
            ]
        )


class MockReflectionLLM:
    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        return ReflectionResult(
            notes=["Grounded in bandit static tool analysis."],
            needs_revision=False,
        )


def test_run_review_end_to_end():
    mock_app = build_graph(
        config=PipelineConfig(),
        planner_llm=MockPlannerLLM(),
        analyzer_llm=MockAnalyzerLLM(),
        reflection_llm=MockReflectionLLM(),
    )

    code = "def get_user(uid): return db.execute(f'SELECT * FROM users WHERE id={uid}')"
    output = run_review(code, app=mock_app)

    assert "findings" in output
    assert len(output["findings"]) == 1
    assert output["findings"][0]["principle"] == "OWASP-Injection"

    assert "report_markdown" in output
    assert "# Code Review Report" in output["report_markdown"]
    assert "1 findings — 1 high, 0 medium, 0 low" in output["report_markdown"]
    assert "static analysis (bandit)" in output["report_markdown"]

    assert output["iteration_count"] == 1
