"""Acceptance tests for Module 3.2: Planner Agent."""

import pytest
from layer3_agents.planner import SubClaims, plan


class MockLLMForPlanner:
    def __init__(self, response_claims: list[str]):
        self.response_claims = response_claims
        self.calls = 0

    def with_structured_output(self, schema):
        return self

    def invoke(self, inputs):
        self.calls += 1
        return SubClaims(sub_claims=self.response_claims)


class MockLLMWithRetry:
    def __init__(self):
        self.calls = 0

    def with_structured_output(self, schema):
        return self

    def invoke(self, inputs):
        self.calls += 1
        if self.calls == 1:
            return SubClaims(sub_claims=["check security"])
        return SubClaims(
            sub_claims=[
                "check security vulnerabilities",
                "check Single Responsibility Principle",
                "check cyclomatic complexity",
            ]
        )


def test_plan_returns_multiple_distinct_claims():
    code = "class GodClass:\n    def do_everything(self): pass\n"
    mock_llm = MockLLMForPlanner(
        [
            "check for Single Responsibility Principle violations in class GodClass",
            "check for SQL injection in do_everything",
            "check for naming convention issues",
        ]
    )
    claims = plan(code, llm=mock_llm)
    assert 3 <= len(claims) <= 6
    assert len(set(claims)) == len(claims)  # no duplicates
    assert mock_llm.calls == 1


def test_plan_empty_code_short_circuits():
    # Calling plan on empty code should never touch LLM
    claims = plan("", llm=None)
    assert claims == ["no code provided to review"]

    claims_whitespace = plan("   \n\t  ", llm=None)
    assert claims_whitespace == ["no code provided to review"]


def test_plan_retries_on_single_claim():
    code = "def foo(): pass"
    mock_llm = MockLLMWithRetry()
    claims = plan(code, llm=mock_llm)
    assert len(claims) == 3
    assert mock_llm.calls == 2  # 1 initial + 1 retry


def test_plan_truncates_very_long_code():
    long_code = "x = 1\n" * 10000
    mock_llm = MockLLMForPlanner(
        [
            "check file length",
            "check memory usage",
            "check naming conventions",
        ]
    )
    claims = plan(long_code, llm=mock_llm)
    assert len(claims) == 3
