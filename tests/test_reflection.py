"""Acceptance tests for Module 3.5: Reflection Agent."""

import pytest
from layer3_agents.reflection import ReflectionResult, reflect
from layer3_agents.state import Finding


class MockLLMForReflection:
    def __init__(self, notes: list[str], needs_revision: bool):
        self.notes = notes
        self.needs_revision = needs_revision
        self.calls = 0

    def with_structured_output(self, schema):
        return self

    def invoke(self, inputs):
        self.calls += 1
        return ReflectionResult(notes=self.notes, needs_revision=self.needs_revision)


def test_reflect_catches_grounding_mismatch():
    draft: list[Finding] = [
        {
            "principle": "SRP",
            "evidence_chunk_id": "chunk_001",
            "severity": "medium",
            "location": "line 10",
            "explanation": "Violates SRP",
            "suggested_fix": "Split class",
        }
    ]
    retrieved = {
        "claim1": [
            {
                "id": "chunk_001",
                "text": "This chunk is about OWASP Injection and input validation, unrelated to SRP.",
            }
        ]
    }
    mock_llm = MockLLMForReflection(
        notes=["Finding #1 cited chunk_001 which discusses OWASP injection rather than Single Responsibility."],
        needs_revision=True,
    )

    result = reflect(draft, retrieved, ["claim1"], llm=mock_llm)
    assert result.needs_revision is True
    assert len(result.notes) == 1
    assert mock_llm.calls == 1


def test_reflect_skips_llm_call_on_empty_draft():
    # Should never call LLM when draft is empty
    class FailingLLM:
        def with_structured_output(self, schema):
            return self

        def invoke(self, inputs):
            pytest.fail("LLM should not be called on empty draft")

    result = reflect([], {}, [], llm=FailingLLM())
    assert result.needs_revision is False
    assert "no findings to review" in result.notes[0]


def test_reflect_handles_tool_findings():
    draft: list[Finding] = [
        {
            "principle": "Security/SQLi",
            "evidence_chunk_id": "tool:bandit",
            "severity": "high",
            "location": "line 5",
            "explanation": "B608 SQL injection detected by bandit",
            "suggested_fix": "Use parameters",
        }
    ]
    mock_llm = MockLLMForReflection(
        notes=["Tool-based finding is grounded in static analysis scanner."],
        needs_revision=False,
    )
    result = reflect(draft, {}, ["check security"], llm=mock_llm)
    assert result.needs_revision is False
    assert mock_llm.calls == 1
