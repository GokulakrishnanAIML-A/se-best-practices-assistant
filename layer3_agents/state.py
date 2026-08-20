"""Module 3.1: Typed state definitions for the Agent Review workflow."""

from typing import Any
from typing_extensions import TypedDict


class Finding(TypedDict):
    principle: str
    evidence_chunk_id: str
    severity: str  # 'low' | 'medium' | 'high'
    location: str  # e.g., "line 12" or "ClassName.method_name"
    explanation: str
    suggested_fix: str


class ReviewState(TypedDict):
    code: str
    sub_claims: list[str]
    retrieved: dict[str, list[dict[str, Any]]]  # sub_claim -> list[Chunk dicts]
    tool_findings: dict[str, Any]  # {structure, security, complexity}
    draft_review: list[Finding]
    reflection_notes: list[str]
    needs_revision: bool
    iteration_count: int
    final_review: list[Finding]
