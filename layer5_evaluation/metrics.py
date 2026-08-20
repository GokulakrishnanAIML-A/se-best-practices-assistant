"""Module 5.4: Quantitative Evaluation Metrics."""

import re
import logging
from typing import Any
from layer3_agents.state import Finding

logger = logging.getLogger(__name__)

# Principle alias dictionary for robust matching
PRINCIPLE_ALIASES: dict[str, str] = {
    # SOLID
    "srp": "SRP",
    "single responsibility": "SRP",
    "single responsibility principle": "SRP",
    "single_responsibility": "SRP",
    "ocp": "OCP",
    "open closed": "OCP",
    "open-closed": "OCP",
    "open/closed": "OCP",
    "open closed principle": "OCP",
    "open-closed principle": "OCP",
    "lsp": "LSP",
    "liskov": "LSP",
    "liskov substitution": "LSP",
    "liskov substitution principle": "LSP",
    "isp": "ISP",
    "interface segregation": "ISP",
    "interface segregation principle": "ISP",
    "dip": "DIP",
    "dependency inversion": "DIP",
    "dependency inversion principle": "DIP",
    "dependency injection": "DIP",
    # OWASP & Security
    "owasp-injection": "OWASP-Injection",
    "injection": "OWASP-Injection",
    "sql injection": "OWASP-Injection",
    "sqli": "OWASP-Injection",
    "command injection": "OWASP-Injection",
    "os command injection": "OWASP-Injection",
    "path traversal": "OWASP-Injection",
    "owasp a03": "OWASP-Injection",
    "owasp-brokenauth": "OWASP-BrokenAuth",
    "broken auth": "OWASP-BrokenAuth",
    "broken authentication": "OWASP-BrokenAuth",
    "authentication": "OWASP-BrokenAuth",
    "hardcoded secret": "OWASP-BrokenAuth",
    "hardcoded credentials": "OWASP-BrokenAuth",
    "owasp a01": "OWASP-BrokenAuth",
    "owasp a07": "OWASP-BrokenAuth",
    "security/sqli": "OWASP-Injection",
    "security/brokenauth": "OWASP-BrokenAuth",
    # Code Quality & Clean Code
    "long-function": "long-function",
    "long function": "long-function",
    "function length": "long-function",
    "large function": "long-function",
    "high-complexity": "high-complexity",
    "high complexity": "high-complexity",
    "cyclomatic complexity": "high-complexity",
    "complex method": "high-complexity",
    "poor-naming": "poor-naming",
    "poor naming": "poor-naming",
    "naming": "poor-naming",
    "pep8-naming": "poor-naming",
    "pep 8": "poor-naming",
    "cryptic variable": "poor-naming",
}


def normalize_principle(principle: str) -> str:
    """Normalize principle string to standard canonical tag."""
    if not principle:
        return "Unknown"
    norm = principle.lower().strip()
    # Check exact alias match
    if norm in PRINCIPLE_ALIASES:
        return PRINCIPLE_ALIASES[norm]
    # Check substring containment
    for alias, canonical in PRINCIPLE_ALIASES.items():
        if alias in norm:
            return canonical
    return principle.strip()


def extract_line_range(location: str) -> tuple[int, int] | None:
    """Extract line range (start, end) from location string."""
    if not location:
        return None
    # Match patterns like "line 12", "lines 10-25", "10:25", "line 12 to 20"
    numbers = [int(n) for n in re.findall(r"\b\d+\b", location)]
    if len(numbers) >= 2:
        return (min(numbers[0], numbers[1]), max(numbers[0], numbers[1]))
    elif len(numbers) == 1:
        return (numbers[0], numbers[0])
    return None


def is_finding_match(pred: Finding, gt: dict[str, Any]) -> bool:
    """Determine whether a predicted finding matches a ground-truth violation."""
    pred_principle = normalize_principle(pred.get("principle", ""))
    gt_principle = normalize_principle(gt.get("principle", ""))

    if pred_principle != gt_principle:
        return False

    gt_range = gt.get("line_range")
    if not gt_range:
        return True

    gt_start, gt_end = gt_range
    pred_location = pred.get("location", "")
    pred_range = extract_line_range(pred_location)

    if pred_range:
        p_start, p_end = pred_range
        # Check overlap with tolerance of +-3 lines
        return not (p_end < gt_start - 3 or p_start > gt_end + 3)

    # If no line numbers in location, match by principle
    return True


def detection_recall(predicted: list[Finding], ground_truth: list[dict[str, Any]]) -> float:
    """Calculate detection recall against ground-truth violations.

    recall = caught_violations / total_ground_truth_violations
    """
    if not ground_truth:
        return 1.0
    if not predicted:
        return 0.0

    caught = 0
    for gt in ground_truth:
        if any(is_finding_match(p, gt) for p in predicted):
            caught += 1

    return caught / len(ground_truth)


def detection_precision(predicted: list[Finding], ground_truth: list[dict[str, Any]]) -> float:
    """Calculate detection precision against ground-truth violations.

    precision = true_positive_predictions / total_predictions
    """
    if not predicted:
        return 1.0
    if not ground_truth:
        return 0.0

    true_positives = 0
    for p in predicted:
        if any(is_finding_match(p, gt) for gt in ground_truth):
            true_positives += 1

    return true_positives / len(predicted)


def f1_score(precision: float, recall: float) -> float:
    """Calculate harmonic mean F1-Score."""
    if precision + recall == 0.0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)


def groundedness(
    findings: list[Finding],
    retrieved_or_chunks_lookup: dict[str, Any],
    judge_llm: Any = None,
) -> float:
    """Calculate percentage of RAG findings with verifiable chunk support.

    Excludes static tool ('tool:') and zero-shot ('none') evidence.
    """
    rag_findings = [
        f
        for f in findings
        if f.get("evidence_chunk_id")
        and not f["evidence_chunk_id"].startswith("tool:")
        and f["evidence_chunk_id"] != "none"
    ]

    if not rag_findings:
        return 1.0

    # Build flat chunk lookup
    chunk_texts: dict[str, str] = {}
    if isinstance(retrieved_or_chunks_lookup, dict):
        for k, v in retrieved_or_chunks_lookup.items():
            if isinstance(v, list):
                for chunk in v:
                    if isinstance(chunk, dict) and "id" in chunk:
                        chunk_texts[chunk["id"]] = chunk.get("text", "")
            elif isinstance(v, dict) and "text" in v:
                chunk_texts[k] = v.get("text", "")
            elif isinstance(v, str):
                chunk_texts[k] = v

    supported = 0
    for f in rag_findings:
        cid = f.get("evidence_chunk_id", "")
        if cid in chunk_texts:
            text = chunk_texts[cid].lower()
            explanation = f.get("explanation", "").lower()
            principle = f.get("principle", "").lower()

            # Verify lexical/conceptual grounding support
            p_words = set(re.findall(r"\w+", principle))
            e_words = set(re.findall(r"\w+", explanation))
            t_words = set(re.findall(r"\w+", text))

            overlap = (p_words | e_words) & t_words
            if len(overlap) >= 2:
                supported += 1

    return supported / len(rag_findings)


def consistency(runs: list[list[Finding]]) -> float:
    """Calculate consistency across multiple repeated runs of the same input.

    Computes the average pairwise Jaccard similarity of normalized principle sets.
    """
    if len(runs) < 2:
        return 1.0

    principle_sets = [
        {normalize_principle(f.get("principle", "")) for f in run if f.get("principle")}
        for run in runs
    ]

    pairwise_jaccard: list[float] = []
    for i in range(len(principle_sets)):
        for j in range(i + 1, len(principle_sets)):
            s1 = principle_sets[i]
            s2 = principle_sets[j]
            if not s1 and not s2:
                pairwise_jaccard.append(1.0)
            else:
                jaccard = len(s1 & s2) / len(s1 | s2)
                pairwise_jaccard.append(jaccard)

    return sum(pairwise_jaccard) / len(pairwise_jaccard) if pairwise_jaccard else 1.0
