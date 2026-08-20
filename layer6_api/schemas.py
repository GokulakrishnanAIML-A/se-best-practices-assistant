"""Module 6.1: API Request and Response Schemas."""

from typing import Literal
from pydantic import BaseModel, Field
from layer3_agents.state import Finding


class ReviewRequest(BaseModel):
    code: str = Field(..., description="Python source code to review.")
    filename: str | None = Field(default=None, description="Optional filename or module path.")


class ReviewResponse(BaseModel):
    findings: list[Finding] = Field(
        default_factory=list, description="Validated software engineering findings."
    )
    report_markdown: str = Field(description="Deterministic formatted Markdown review report.")
    iteration_count: int = Field(
        default=1, description="Total agent reflection iterations executed."
    )


class HITLDecisionRequest(BaseModel):
    finding_index: int = Field(..., ge=0, description="Zero-based index of the target finding.")
    decision: Literal["accept", "edit", "reject"] = Field(
        ..., description="Human review decision."
    )
    edited_text: str | None = Field(
        default=None, description="Updated explanation or fix (required when decision='edit')."
    )


class HITLDecisionResponse(BaseModel):
    status: str = Field(default="recorded", description="Status of decision persistence.")
    session_id: str = Field(description="Unique review session identifier.")
    finding_index: int = Field(description="Target finding index.")
    decision: str = Field(description="Action recorded.")
