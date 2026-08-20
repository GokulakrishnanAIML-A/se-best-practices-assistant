"""Module 3.6: Deterministic Report Generator."""

from typing import Any
from layer3_agents.state import Finding


def format_report(
    findings: list[Finding], retrieved: dict[str, list[dict[str, Any]]] | None = None
) -> str:
    """Format review findings into a clean, deterministic Markdown report.

    Args:
        findings: List of validated Finding dictionaries.
        retrieved: Optional mapping of sub-claims to retrieved chunk dicts for citation lookup.

    Returns:
        Deterministic Markdown string report.
    """
    if retrieved is None:
        retrieved = {}

    # Build chunk lookup table for metadata resolution
    chunk_meta: dict[str, dict[str, Any]] = {}
    for chunk_list in retrieved.values():
        for c in chunk_list:
            if isinstance(c, dict) and "id" in c:
                chunk_meta[c["id"]] = c

    # Calculate severity counts
    n_high = sum(1 for f in findings if f.get("severity", "").lower() == "high")
    n_med = sum(1 for f in findings if f.get("severity", "").lower() == "medium")
    n_low = sum(1 for f in findings if f.get("severity", "").lower() == "low")
    n_total = len(findings)

    header = f"# Code Review Report\n\n**Summary:** {n_total} findings — {n_high} high, {n_med} medium, {n_low} low\n"

    if not findings:
        return header + "\nNo best practice violations detected. Code adheres to evaluated guidelines."

    sections: list[str] = [header]

    # Group and render in order of severity
    severity_order = ["high", "medium", "low"]
    for sev in severity_order:
        group = [f for f in findings if f.get("severity", "").lower() == sev]
        if not group:
            continue

        # Sort alphabetically by principle
        group_sorted = sorted(group, key=lambda item: item.get("principle", "").lower())

        sections.append(f"## {sev.capitalize()} Severity Issues\n")

        for f in group_sorted:
            sev_tag = f.get("severity", "medium").upper()
            principle = f.get("principle", "General Practice")
            location = f.get("location", "code")
            explanation = f.get("explanation", "").strip()
            fix = f.get("suggested_fix", "").strip()
            cid = f.get("evidence_chunk_id", "").strip()

            if cid.startswith("tool:"):
                tool_name = cid.split("tool:", 1)[1] if "tool:" in cid else "tool"
                source_desc = f"static analysis ({tool_name})"
            elif cid in chunk_meta:
                c = chunk_meta[cid]
                title = c.get("title") or c.get("source", "Reference Guide")
                url = c.get("url") or "internal knowledge base"
                source_desc = f"{title} ({url})"
            elif cid:
                source_desc = f"Reference Chunk ID: {cid}"
            else:
                source_desc = "Standard Software Engineering Best Practices"

            entry = (
                f"### [{sev_tag}] {principle} — {location}\n\n"
                f"{explanation}\n\n"
                f"**Suggested fix:** {fix}\n\n"
                f"**Source:** {source_desc}\n"
            )
            sections.append(entry)

    return "\n".join(sections).strip() + "\n"
