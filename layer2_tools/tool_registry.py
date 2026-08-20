"""Module 2.4 — LangChain Tool Registry for Code Quality and Security Analysis.

Exports LangChain @tool decorated functions callable autonomously by the Analyzer agent.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from layer2_tools.ast_tool import analyze_structure
from layer2_tools.bandit_tool import run_bandit
from layer2_tools.radon_tool import analyze_complexity


@tool
def check_structure(code: str) -> dict[str, Any]:
    """Analyze class/function structure: method counts, nesting depth, line counts.

    Use to detect God classes (>7-8 methods) or long functions (>50 lines).
    """
    return dict(analyze_structure(code))


@tool
def check_security(code: str) -> list[dict[str, Any]]:
    """Run static security analysis on Python code.

    Returns list of security findings with severity, issue description, line number, and CWE.
    """
    return [dict(f) for f in run_bandit(code)]


@tool
def check_complexity(code: str) -> dict[str, Any]:
    """Return cyclomatic complexity per function and overall maintainability index."""
    return dict(analyze_complexity(code))


ALL_TOOLS = [check_structure, check_security, check_complexity]

TOOL_MAP = {
    "check_structure": check_structure,
    "check_security": check_security,
    "check_complexity": check_complexity,
}
