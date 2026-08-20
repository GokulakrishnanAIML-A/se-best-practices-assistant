"""Module 4.3: High-level review execution entry point."""

import logging
from typing import Any
from layer3_agents.reporter import format_report
from layer4_orchestration.config import PipelineConfig
from layer4_orchestration.graph import build_graph

logger = logging.getLogger(__name__)


def run_review(
    code: str, config: PipelineConfig | None = None, app: Any = None
) -> dict[str, Any]:
    """Execute end-to-end code review pipeline using the LangGraph StateGraph.

    Args:
        code: Source code string to review.
        config: Optional PipelineConfig override.
        app: Optional pre-compiled LangGraph runnable.

    Returns:
        Dictionary containing:
            - findings: list of final validated Finding dicts
            - report_markdown: deterministic Markdown review report
            - iteration_count: total reflection/analysis cycles executed
            - state: full final ReviewState
    """
    if config is None:
        config = PipelineConfig()

    if app is None:
        app = build_graph(config=config)

    initial_state = {
        "code": code,
        "sub_claims": [],
        "retrieved": {},
        "tool_findings": {},
        "draft_review": [],
        "reflection_notes": [],
        "needs_revision": False,
        "iteration_count": 0,
        "final_review": [],
    }

    logger.info("Invoking code review StateGraph...")
    result_state = app.invoke(initial_state)

    findings = result_state.get("final_review", [])
    retrieved = result_state.get("retrieved", {})
    report_markdown = format_report(findings=findings, retrieved=retrieved)

    return {
        "findings": findings,
        "report_markdown": report_markdown,
        "iteration_count": result_state.get("iteration_count", 0),
        "state": result_state,
    }
