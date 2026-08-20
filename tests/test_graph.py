"""Acceptance tests for Module 4.2: LangGraph Orchestration Workflow."""

import pytest
from layer3_agents.planner import SubClaims
from layer3_agents.analyzer import DraftReview, FindingModel
from layer3_agents.reflection import ReflectionResult
from layer4_orchestration.config import PipelineConfig
from layer4_orchestration.graph import build_graph


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
                    principle="SRP",
                    evidence_chunk_id="tool:ast",
                    severity="high",
                    location="GodClass",
                    explanation="Class handles too many responsibilities.",
                    suggested_fix="Split into separate cohesive classes.",
                )
            ]
        )


class MockAlwaysNeedsRevisionReflectionLLM:
    def __init__(self):
        self.calls = 0

    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        self.calls += 1
        return ReflectionResult(
            notes=["Forced reflection revision trigger"],
            needs_revision=True,
        )


class MockCleanReflectionLLM:
    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        return ReflectionResult(
            notes=["All findings are well-grounded"],
            needs_revision=False,
        )


def test_graph_terminates_within_max_iterations():
    cfg = PipelineConfig(max_reflection_iterations=2)
    reflection_llm = MockAlwaysNeedsRevisionReflectionLLM()

    app = build_graph(
        config=cfg,
        planner_llm=MockPlannerLLM(),
        analyzer_llm=MockAnalyzerLLM(),
        reflection_llm=reflection_llm,
    )

    sample_code = "class GodClass:\n    pass\n"
    initial_state = {
        "code": sample_code,
        "sub_claims": [],
        "retrieved": {},
        "tool_findings": {},
        "draft_review": [],
        "reflection_notes": [],
        "needs_revision": False,
        "iteration_count": 0,
        "final_review": [],
    }

    result = app.invoke(initial_state, config={"recursion_limit": 25})

    # The analyzer ran 2 times, hitting the max_reflection_iterations limit of 2
    assert result["iteration_count"] == 2
    assert len(result["final_review"]) == 1
    assert result["final_review"][0]["principle"] == "SRP"


def test_graph_full_state_trace_has_all_nodes(capsys):
    cfg = PipelineConfig(max_reflection_iterations=2)
    app = build_graph(
        config=cfg,
        planner_llm=MockPlannerLLM(),
        analyzer_llm=MockAnalyzerLLM(),
        reflection_llm=MockCleanReflectionLLM(),
    )

    sample_code = "def sample(): pass"
    initial_state = {
        "code": sample_code,
        "sub_claims": [],
        "retrieved": {},
        "tool_findings": {},
        "draft_review": [],
        "reflection_notes": [],
        "needs_revision": False,
        "iteration_count": 0,
        "final_review": [],
    }

    visited_nodes = []
    for event in app.stream(initial_state):
        node_name = list(event.keys())[0]
        visited_nodes.append(node_name)

    expected_nodes = ["planner", "retriever", "analyzer", "reflection", "reporter"]
    for node in expected_nodes:
        assert node in visited_nodes, f"Expected node '{node}' in execution stream {visited_nodes}"

    # For a clean review, analyzer ran exactly once
    assert visited_nodes.count("analyzer") == 1
