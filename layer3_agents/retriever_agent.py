"""Module 3.3: Retriever Agent with Keyword Source Routing and Fallback."""

import logging
from typing import Any
from layer1_data.retriever import KnowledgeRetriever

logger = logging.getLogger(__name__)

SOURCE_KEYWORDS: dict[str, list[str]] = {
    "owasp": [
        "injection",
        "security",
        "authentication",
        "access control",
        "vulnerability",
        "xss",
        "csrf",
        "sqli",
        "credential",
        "password",
        "secret",
    ],
    "solid": [
        "responsibility",
        "srp",
        "open/closed",
        "ocp",
        "liskov",
        "lsp",
        "interface segregation",
        "isp",
        "dependency inversion",
        "dip",
        "solid",
    ],
    "clean_code": [
        "naming",
        "readability",
        "function length",
        "clean code",
        "comment",
        "complexity",
        "maintainability",
    ],
    "python": [
        "pep 8",
        "pep8",
        "pythonic",
        "convention",
        "idiom",
    ],
}


def route_source(sub_claim: str) -> str | None:
    """Determine the most relevant knowledge source based on keyword overlap.

    Args:
        sub_claim: Review claim string (e.g. "Check for SQL injection vulnerabilities").

    Returns:
        Source string (e.g. "owasp", "solid") or None if no clear match.
    """
    normalized = sub_claim.lower()
    best_source = None
    max_hits = 0

    for source, keywords in SOURCE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in normalized)
        if hits > max_hits:
            max_hits = hits
            best_source = source

    return best_source if max_hits > 0 else None


def retrieve_for_claims(
    sub_claims: list[str], retriever: KnowledgeRetriever, k: int = 3
) -> dict[str, list[dict[str, Any]]]:
    """Retrieve supporting evidence chunks for each review sub-claim.

    Args:
        sub_claims: List of sub-claims produced by the planner.
        retriever: KnowledgeRetriever instance.
        k: Number of chunks per claim.

    Returns:
        Mapping from sub_claim to list of retrieved chunk dictionaries.
    """
    results: dict[str, list[dict[str, Any]]] = {}

    for claim in sub_claims:
        if not claim or not claim.strip():
            continue

        source = route_source(claim)
        chunks = retriever.search(claim, source=source, k=k, mode="hybrid")

        # Edge case: If routed source yielded 0 results, fall back to unfiltered search
        if not chunks and source is not None:
            logger.info(
                f"Routed search for '{claim}' with source='{source}' yielded 0 chunks. Falling back to unfiltered search."
            )
            chunks = retriever.search(claim, source=None, k=k, mode="hybrid")

        # Rubric requirement: log the routing decision and chunk count
        logger.info(f"Retrieval strategy: '{claim}' -> source={source}, {len(chunks)} chunks retrieved")
        results[claim] = chunks

    return results
