"""Module 5.3: Naive Single-Shot RAG Review Baseline."""

import logging
from typing import Any
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from layer3_agents.state import Finding
from layer1_data.retriever import KnowledgeRetriever

logger = logging.getLogger(__name__)


class NaiveRAGFinding(BaseModel):
    principle: str = Field(description="Software engineering principle or standard violated.")
    evidence_chunk_id: str = Field(
        description="Chunk ID from the retrieved context that supports this finding."
    )
    severity: str = Field(description="Severity: 'low', 'medium', or 'high'.")
    location: str = Field(description="Line number or function/class location.")
    explanation: str = Field(description="Explanation of the issue.")
    suggested_fix: str = Field(description="Concrete recommendation or fix.")


class NaiveRAGReview(BaseModel):
    findings: list[NaiveRAGFinding] = Field(
        default_factory=list,
        description="List of detected code review findings grounded in retrieved evidence.",
    )


NAIVE_RAG_SYSTEM_PROMPT = (
    "You are an expert software engineering reviewer with access to reference material. "
    "Review the provided code snippet against the retrieved reference chunks. "
    "For each finding, specify the principle, severity, location, explanation, suggested_fix, "
    "and cite the exact evidence_chunk_id from the reference chunks that supports your finding. "
    "Output ONLY the structured findings list."
)


def review_naive_rag(
    code: str, retriever: KnowledgeRetriever | None = None, llm: Any = None
) -> list[Finding]:
    """Execute baseline naive RAG review using a single dense query without decomposition or agents.

    Args:
        code: Source code string to review.
        retriever: KnowledgeRetriever instance.
        llm: LangChain ChatModel instance or structured runnable.

    Returns:
        List of Finding dicts citing retrieved chunk IDs.
    """
    if not code or not code.strip():
        return []

    if retriever is None:
        retriever = KnowledgeRetriever()

    if llm is None:
        from layer4_orchestration.config import get_llm

        llm = get_llm("claude-sonnet-4-6", temperature=0.2)

    # 1. Single retrieval call using raw code snippet (no sub-claims, no routing)
    retrieved_chunks = retriever.search(code[:2000], k=5, mode="hybrid")

    # 2. Format context block
    context_lines = []
    for c in retrieved_chunks:
        cid = c.get("id", "unknown")
        src = c.get("source", "doc")
        text = c.get("text", "").strip()
        context_lines.append(f"[{cid}] ({src}) {text}")
    context_block = "\n\n".join(context_lines) if context_lines else "No reference chunks retrieved."

    # 3. Single LLM call
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", NAIVE_RAG_SYSTEM_PROMPT),
            (
                "user",
                "Code to review:\n```python\n{code}\n```\n\n"
                "Retrieved Reference Material:\n{context_block}",
            ),
        ]
    )

    if hasattr(llm, "with_structured_output"):
        structured_llm = llm.with_structured_output(NaiveRAGReview)
    else:
        structured_llm = llm

    messages = prompt.format_messages(code=code, context_block=context_block)
    result = structured_llm.invoke(messages)

    raw_findings: list[NaiveRAGFinding | dict] = []
    if isinstance(result, NaiveRAGReview):
        raw_findings = result.findings
    elif isinstance(result, dict) and "findings" in result:
        raw_findings = result["findings"]
    elif isinstance(result, list):
        raw_findings = result
    else:
        raw_findings = getattr(result, "findings", [])

    standardized: list[Finding] = []
    for item in raw_findings:
        if isinstance(item, NaiveRAGFinding):
            standardized.append(
                {
                    "principle": item.principle,
                    "evidence_chunk_id": item.evidence_chunk_id,
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
                    "evidence_chunk_id": item.get("evidence_chunk_id", "unknown"),
                    "severity": item.get("severity", "medium").lower(),
                    "location": item.get("location", "code"),
                    "explanation": item.get("explanation", ""),
                    "suggested_fix": item.get("suggested_fix", ""),
                }
            )

    return standardized
