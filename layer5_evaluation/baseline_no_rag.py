"""Module 5.2: No-RAG Direct LLM Review Baseline."""

import logging
from typing import Any
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from layer3_agents.state import Finding

logger = logging.getLogger(__name__)


class NoRAGFinding(BaseModel):
    principle: str = Field(description="Software engineering principle or standard violated.")
    severity: str = Field(description="Severity: 'low', 'medium', or 'high'.")
    location: str = Field(description="Line number or function/class location.")
    explanation: str = Field(description="Explanation of the issue.")
    suggested_fix: str = Field(description="Concrete recommendation or fix.")


class NoRAGReview(BaseModel):
    findings: list[NoRAGFinding] = Field(
        default_factory=list,
        description="List of detected code review findings.",
    )


NO_RAG_SYSTEM_PROMPT = (
    "You are an expert software engineering reviewer. Review the provided code snippet for "
    "SOLID design principles, OWASP security risks, clean code conventions, and complexity issues. "
    "List each issue with principle, severity, location, explanation, and suggested_fix. "
    "Output ONLY the structured findings."
)


def review_no_rag(code: str, llm: Any = None) -> list[Finding]:
    """Execute baseline zero-shot code review without RAG or static analysis tools.

    Args:
        code: Source code string to review.
        llm: LangChain ChatModel instance or structured runnable.

    Returns:
        List of Finding dicts with evidence_chunk_id='none' for uniform evaluation.
    """
    if not code or not code.strip():
        return []

    if llm is None:
        from layer4_orchestration.config import get_llm

        llm = get_llm("claude-sonnet-4-6", temperature=0.2)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", NO_RAG_SYSTEM_PROMPT),
            ("user", "Code to review:\n```python\n{code}\n```"),
        ]
    )

    if hasattr(llm, "with_structured_output"):
        structured_llm = llm.with_structured_output(NoRAGReview)
    else:
        structured_llm = llm

    messages = prompt.format_messages(code=code)
    result = structured_llm.invoke(messages)

    raw_findings: list[NoRAGFinding | dict] = []
    if isinstance(result, NoRAGReview):
        raw_findings = result.findings
    elif isinstance(result, dict) and "findings" in result:
        raw_findings = result["findings"]
    elif isinstance(result, list):
        raw_findings = result
    else:
        raw_findings = getattr(result, "findings", [])

    standardized: list[Finding] = []
    for item in raw_findings:
        if isinstance(item, NoRAGFinding):
            standardized.append(
                {
                    "principle": item.principle,
                    "evidence_chunk_id": "none",
                    "severity": item.severity.lower() if item.severity.lower() in {"low", "medium", "high"} else "medium",
                    "location": item.location,
                    "explanation": item.explanation,
                    "suggested_fix": item.suggested_fix,
                }
            )
        elif isinstance(item, dict):
            standardized.append(
                {
                    "principle": item.get("principle", "General Practice"),
                    "evidence_chunk_id": "none",
                    "severity": item.get("severity", "medium").lower(),
                    "location": item.get("location", "code"),
                    "explanation": item.get("explanation", ""),
                    "suggested_fix": item.get("suggested_fix", ""),
                }
            )

    return standardized
