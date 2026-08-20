"""Module 2.3 — Radon Complexity and Maintainability Analysis Tool.

Calculates cyclomatic complexity (CC) per function and overall
Maintainability Index (MI) for Python code.
"""

from __future__ import annotations

import logging
from typing import Any, TypedDict

from radon.complexity import cc_rank, cc_visit
from radon.metrics import mi_visit

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class ComplexityReport(TypedDict):
    per_function: list[dict[str, Any]]  # [{name, complexity, rank}]
    maintainability_index: float


def analyze_complexity(code: str) -> ComplexityReport:
    """Analyze code for per-function cyclomatic complexity and maintainability index.

    Wraps radon calls in try/except SyntaxError to return a safe fallback on invalid syntax.
    """
    code_str = code or ""
    if not code_str.strip():
        return {
            "per_function": [],
            "maintainability_index": 100.0,
        }

    try:
        # Cyclomatic complexity visit
        blocks = cc_visit(code_str)

        per_function: list[dict[str, Any]] = []

        def collect_blocks(item: Any, prefix: str = "") -> None:
            # Check if block is a function or method
            if hasattr(item, "is_method") or hasattr(item, "complexity"):
                # If item is a Class block, process its methods
                if hasattr(item, "methods") and item.methods:
                    class_name = item.name
                    for method in item.methods:
                        collect_blocks(method, prefix=f"{class_name}.")
                elif hasattr(item, "complexity"):
                    full_name = f"{prefix}{item.name}"
                    rank = getattr(item, "letter_rank", None)
                    if not rank:
                        rank = cc_rank(item.complexity)

                    per_function.append({
                        "name": full_name,
                        "complexity": int(item.complexity),
                        "rank": str(rank),
                    })

        for block in blocks:
            collect_blocks(block)

        # Maintainability index
        maintainability_index = float(mi_visit(code_str, multi=True))

        return {
            "per_function": per_function,
            "maintainability_index": round(maintainability_index, 2),
        }

    except SyntaxError as e:
        logger.warning(f"Syntax error during Radon analysis: {e}")
        return {
            "per_function": [],
            "maintainability_index": 0.0,
        }
    except Exception as exc:
        logger.warning(f"Radon analysis error: {exc}")
        return {
            "per_function": [],
            "maintainability_index": 0.0,
        }


if __name__ == "__main__":
    sample = "def f(x):\n" + "\n".join(f"    if x == {i}: return {i}" for i in range(15))
    print(analyze_complexity(sample))
