"""Module 3.2: Planner Agent for generating review sub-claims."""

import logging
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

# Diagnostic counter used in tests
llm_call_count = 0


class SubClaims(BaseModel):
    sub_claims: list[str] = Field(
        description="List of 3 to 6 specific, verifiable sub-claims for reviewing the code."
    )


PLANNER_SYSTEM_PROMPT = (
    "You are a code review planner. Given a code snippet, produce a list of 3 to 6 specific, "
    "checkable review sub-claims covering: SOLID principles, security risks (OWASP-style), "
    "naming/readability, and complexity. Each sub-claim must be specific enough to map to a single "
    'retrieval query, e.g. "check for Single Responsibility Principle violations in class X" '
    'not "check code quality". Do not include claims unrelated to the code shown. '
    "Output ONLY the structured list, no commentary."
)


def plan(code: str, llm=None) -> list[str]:
    """Generate structured review sub-claims for a code snippet.

    Args:
        code: Python source code snippet to review.
        llm: A LangChain ChatModel instance or structured output runnable.

    Returns:
        A list of 3 to 6 distinct review sub-claims.
    """
    global llm_call_count

    # Edge case 1: Empty or whitespace-only code
    if not code or not code.strip():
        logger.info("Empty code snippet provided to planner; short-circuiting.")
        return ["no code provided to review"]

    # Edge case 2: Very long code input -> truncate for broad planner view
    # Approximate 6000 tokens by character count (24000 chars)
    max_chars = 24000
    if len(code) > max_chars:
        logger.warning(
            f"Code length ({len(code)} chars) exceeds planner threshold ({max_chars} chars); truncating."
        )
        code = code[:max_chars] + "\n# ... [truncated for planning]"

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", PLANNER_SYSTEM_PROMPT),
            ("user", "{code}"),
        ]
    )

    if llm is None:
        raise ValueError("An LLM instance must be provided to planner.plan() when code is non-empty.")

    # Configure structured model
    if hasattr(llm, "with_structured_output"):
        structured_llm = llm.with_structured_output(SubClaims)
    else:
        structured_llm = llm

    messages = prompt.format_messages(code=code)
    llm_call_count += 1
    result = structured_llm.invoke(messages)

    # Extract sub_claims
    if isinstance(result, SubClaims):
        raw_claims = result.sub_claims
    elif isinstance(result, dict) and "sub_claims" in result:
        raw_claims = result["sub_claims"]
    elif isinstance(result, list):
        raw_claims = result
    else:
        raw_claims = getattr(result, "sub_claims", [])

    # Retry once if model returned fewer than 2 claims
    if len(raw_claims) < 2:
        logger.info("Planner returned fewer than 2 claims; retrying with explicit guidance.")
        retry_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", PLANNER_SYSTEM_PROMPT),
                ("user", "{code}"),
                (
                    "user",
                    "Provide at least 3 distinct sub-claims covering SOLID, security, readability, or complexity.",
                ),
            ]
        )
        retry_messages = retry_prompt.format_messages(code=code)
        llm_call_count += 1
        retry_result = structured_llm.invoke(retry_messages)

        if isinstance(retry_result, SubClaims):
            raw_claims = retry_result.sub_claims
        elif isinstance(retry_result, dict) and "sub_claims" in retry_result:
            raw_claims = retry_result["sub_claims"]
        elif isinstance(retry_result, list):
            raw_claims = retry_result
        else:
            raw_claims = getattr(retry_result, "sub_claims", raw_claims)

    # Deduplicate while preserving order
    deduped: list[str] = []
    seen = set()
    for claim in raw_claims:
        cleaned = claim.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            deduped.append(cleaned)

    return deduped
