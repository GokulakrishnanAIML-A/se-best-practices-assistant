"""Module 3.5: Reflection Agent for Self-Correction and Grounding Verification."""

import logging
from typing import Any
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from layer3_agents.state import Finding

logger = logging.getLogger(__name__)


class ReflectionResult(BaseModel):
    notes: list[str] = Field(
        default_factory=list,
        description="Critique notes concerning grounding, coverage, or over-confidence.",
    )
    needs_revision: bool = Field(
        default=False,
        description="True if any grounding mismatch or hallucination requires re-analysis; False otherwise.",
    )


REFLECTION_SYSTEM_PROMPT = (
    "You are a strict reviewer of a draft code review. Check three things:\n"
    "1. GROUNDING: for each finding, does the cited evidence chunk's text actually support the specific "
    "claim made (not just topically related)? Flag any mismatch by finding index.\n"
    "2. COVERAGE: do the findings collectively address all given sub_claims? List any sub_claim with "
    "zero corresponding findings AND zero indication the claim was checked-and-clean.\n"
    '3. OVER-CONFIDENCE: flag any finding using absolute language ("always", "never", "definitely wrong") '
    "without hedging appropriate to a static-analysis-grounded review.\n"
    "Set needs_revision=true if any GROUNDING mismatch is found (coverage gaps and over-confidence alone "
    "do not require another full iteration — note them but set needs_revision based on grounding only, "
    "to bound the reflection loop to genuine errors rather than style nitpicks)."
)


def reflect(
    draft_review: list[Finding],
    retrieved: dict[str, list[dict[str, Any]]],
    sub_claims: list[str],
    llm: Any,
) -> ReflectionResult:
    """Evaluate draft findings for grounding fidelity, coverage, and tone.

    Args:
        draft_review: List of findings proposed by the Analyzer.
        retrieved: Dictionary of retrieved reference chunks.
        sub_claims: Original review sub-claims from the Planner.
        llm: LangChain model instance or structured runnable.

    Returns:
        ReflectionResult with critique notes and needs_revision boolean.
    """
    # Edge case 1: Empty draft review -> short-circuit without calling LLM
    if not draft_review:
        logger.info("Draft review is empty; skipping reflection LLM call.")
        return ReflectionResult(notes=["no findings to review"], needs_revision=False)

    # Build chunk lookup table
    chunk_lookup: dict[str, str] = {}
    for chunk_list in retrieved.values():
        for chunk in chunk_list:
            if isinstance(chunk, dict) and "id" in chunk:
                chunk_lookup[chunk["id"]] = chunk.get("text", "")

    # Format findings with cited chunk texts for reflection verification
    formatted_findings: list[str] = []
    for idx, f in enumerate(draft_review, start=1):
        cid = f.get("evidence_chunk_id", "")
        if cid.startswith("tool:"):
            evidence_text = f"[Static Tool Verification: {cid}]"
        else:
            evidence_text = chunk_lookup.get(cid, "[WARNING: Evidence chunk text not found]")

        formatted_findings.append(
            f"Finding #{idx}:\n"
            f"  Principle: {f.get('principle')}\n"
            f"  Location: {f.get('location')}\n"
            f"  Severity: {f.get('severity')}\n"
            f"  Explanation: {f.get('explanation')}\n"
            f"  Fix: {f.get('suggested_fix')}\n"
            f"  Cited Chunk ID: {cid}\n"
            f"  Cited Chunk Text: {evidence_text}\n"
        )

    findings_block = "\n".join(formatted_findings)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", REFLECTION_SYSTEM_PROMPT),
            (
                "user",
                "Sub-claims to cover:\n{sub_claims}\n\n"
                "Draft Findings to Evaluate:\n{findings_block}",
            ),
        ]
    )

    if hasattr(llm, "with_structured_output"):
        structured_llm = llm.with_structured_output(ReflectionResult)
    else:
        structured_llm = llm

    messages = prompt.format_messages(
        sub_claims="\n".join(f"- {sc}" for sc in sub_claims),
        findings_block=findings_block,
    )
    result = structured_llm.invoke(messages)

    if isinstance(result, ReflectionResult):
        return result
    elif isinstance(result, dict):
        return ReflectionResult(
            notes=result.get("notes", []),
            needs_revision=bool(result.get("needs_revision", False)),
        )
    return getattr(result, "reflection_result", ReflectionResult(notes=[], needs_revision=False))
