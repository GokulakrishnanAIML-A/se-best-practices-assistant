"""Module 3.4: Analyzer Agent with Evidence Grounding and Hallucination Filtering."""

import logging
from typing import Any
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from layer3_agents.state import Finding

logger = logging.getLogger(__name__)


class FindingModel(BaseModel):
    principle: str = Field(description="Software engineering principle or rule violated.")
    evidence_chunk_id: str = Field(
        description="Exact chunk ID from retrieved context, or 'tool:<tool_name>'."
    )
    severity: str = Field(description="Severity level: 'low', 'medium', or 'high'.")
    location: str = Field(description="Code location, e.g., 'line 12' or 'ClassName.method_name'.")
    explanation: str = Field(description="Detailed explanation of the issue.")
    suggested_fix: str = Field(description="Concrete recommendation or refactored code example.")


class DraftReview(BaseModel):
    findings: list[FindingModel] = Field(
        default_factory=list,
        description="List of detected code review findings grounded in retrieved evidence or static tools.",
    )


ANALYZER_SYSTEM_PROMPT = (
    "You are a code analyzer grounding findings in retrieved reference material and static tool output. "
    "For EVERY finding you produce, you MUST cite an evidence_chunk_id from the provided retrieved chunks "
    "— do not state a principle violation without a matching chunk id. "
    "If tool_findings indicate a security or complexity issue with no matching retrieved chunk, still "
    'report it but set evidence_chunk_id to the string "tool:<tool_name>" instead of a chunk id. '
    "Cover every sub_claim provided; if a sub_claim has no issues, do not fabricate one — simply omit it "
    "from findings. Output ONLY the structured findings list."
)


def format_context_block(retrieved: dict[str, list[dict[str, Any]]]) -> str:
    """Format retrieved chunks into a numbered context block for LLM prompt grounding."""
    lines: list[str] = []
    for claim, chunks in retrieved.items():
        lines.append(f"Sub-claim: {claim}")
        for c in chunks:
            cid = c.get("id", "unknown")
            src = c.get("source", "knowledge_base")
            text = c.get("text", "").strip()
            lines.append(f"  [{cid}] ({src}) {text}")
    return "\n".join(lines) if lines else "No reference chunks retrieved."


def analyze(
    code: str,
    sub_claims: list[str],
    retrieved: dict[str, list[dict[str, Any]]],
    tool_findings: dict[str, Any],
    llm: Any,
) -> list[Finding]:
    """Analyze code against sub-claims, retrieved evidence, and static tool outputs.

    Args:
        code: Source code snippet to review.
        sub_claims: List of review sub-claims.
        retrieved: Dictionary mapping sub-claims to retrieved chunk dicts.
        tool_findings: Dictionary containing static analysis tool outputs (AST, Bandit, Radon).
        llm: LangChain model or structured runnable.

    Returns:
        List of validated Finding dictionaries.
    """
    if not code or not code.strip():
        return []

    # 1. Collect all valid chunk IDs across all retrieved claims
    valid_chunk_ids: set[str] = set()
    for chunk_list in retrieved.values():
        for chunk in chunk_list:
            if isinstance(chunk, dict) and "id" in chunk:
                valid_chunk_ids.add(chunk["id"])

    # 2. Build context block
    context_block = format_context_block(retrieved)

    # 3. Build prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", ANALYZER_SYSTEM_PROMPT),
            (
                "user",
                "Code to review:\n```python\n{code}\n```\n\n"
                "Review Sub-claims:\n{sub_claims}\n\n"
                "Retrieved Knowledge Evidence:\n{context_block}\n\n"
                "Static Tool Findings:\n{tool_findings}",
            ),
        ]
    )

    if hasattr(llm, "with_structured_output"):
        structured_llm = llm.with_structured_output(DraftReview)
    else:
        structured_llm = llm

    messages = prompt.format_messages(
        code=code,
        sub_claims="\n".join(f"- {sc}" for sc in sub_claims),
        context_block=context_block,
        tool_findings=str(tool_findings),
    )
    result = structured_llm.invoke(messages)

    # 4. Extract raw findings
    raw_findings: list[FindingModel | dict] = []
    if isinstance(result, DraftReview):
        raw_findings = result.findings
    elif isinstance(result, dict) and "findings" in result:
        raw_findings = result["findings"]
    elif isinstance(result, list):
        raw_findings = result
    else:
        raw_findings = getattr(result, "findings", [])

    # 5. Post-validation / Hallucination Guard
    validated: list[Finding] = []
    for f in raw_findings:
        if isinstance(f, FindingModel):
            finding_dict: Finding = {
                "principle": f.principle,
                "evidence_chunk_id": f.evidence_chunk_id,
                "severity": f.severity.lower() if f.severity.lower() in {"low", "medium", "high"} else "medium",
                "location": f.location,
                "explanation": f.explanation,
                "suggested_fix": f.suggested_fix,
            }
        elif isinstance(f, dict):
            finding_dict = {
                "principle": f.get("principle", "General Practice"),
                "evidence_chunk_id": f.get("evidence_chunk_id", ""),
                "severity": f.get("severity", "medium").lower(),
                "location": f.get("location", "unknown"),
                "explanation": f.get("explanation", ""),
                "suggested_fix": f.get("suggested_fix", ""),
            }
        else:
            continue

        cid = finding_dict["evidence_chunk_id"]

        # Check citation validity: must either start with "tool:" or match a real chunk ID
        if cid.startswith("tool:") or cid in valid_chunk_ids:
            validated.append(finding_dict)
        else:
            logger.warning(
                f"Hallucination guard dropped finding '{finding_dict['principle']}' with fabricated evidence_chunk_id '{cid}'"
            )

    return validated
