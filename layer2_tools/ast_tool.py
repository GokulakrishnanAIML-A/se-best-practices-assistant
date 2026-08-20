"""Module 2.1 — AST Structural Analysis Tool.

Inspects Python source code structure: class definitions, method counts
(God class detection), function line counts, and maximum nesting depths.
"""

from __future__ import annotations

import ast
from typing import Any, TypedDict


class StructureReport(TypedDict, total=False):
    classes: list[dict[str, Any]]  # [{name, method_count, line_start, line_end}]
    functions: list[dict[str, Any]]  # [{name, line_count, nesting_depth, line_start}]
    max_nesting_depth: int
    total_lines: int
    parse_error: str


# Control flow statements that increase nesting depth
_BLOCK_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.With,
    ast.AsyncWith,
)


def _compute_max_depth_inside_function(func_node: ast.AST) -> int:
    """Calculate the maximum control-flow nesting depth within a given function."""
    max_depth = 0

    def walk_block(node: ast.AST, current_depth: int) -> None:
        nonlocal max_depth
        if isinstance(node, _BLOCK_NODES):
            current_depth += 1
            if current_depth > max_depth:
                max_depth = current_depth

        for child in ast.iter_child_nodes(node):
            # Do not traverse into nested functions/classes for this function's metric
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                walk_block(child, current_depth)

    for child in ast.iter_child_nodes(func_node):
        walk_block(child, 0)

    return max_depth


def analyze_structure(code: str) -> StructureReport:
    """Parse Python code using AST and return a comprehensive StructureReport.

    Handles SyntaxError gracefully by returning zeroed fields and a 'parse_error' key.
    """
    code_str = code or ""
    lines = code_str.splitlines()
    total_lines = len(lines)

    if not code_str.strip():
        return {
            "classes": [],
            "functions": [],
            "max_nesting_depth": 0,
            "total_lines": total_lines,
        }

    try:
        tree = ast.parse(code_str)
    except SyntaxError as e:
        return {
            "classes": [],
            "functions": [],
            "max_nesting_depth": 0,
            "total_lines": total_lines,
            "parse_error": f"SyntaxError at line {e.lineno}, col {e.offset}: {e.msg}",
        }
    except Exception as e:
        return {
            "classes": [],
            "functions": [],
            "max_nesting_depth": 0,
            "total_lines": total_lines,
            "parse_error": f"Parse error: {str(e)}",
        }

    classes: list[dict[str, Any]] = []
    functions: list[dict[str, Any]] = []
    global_max_nesting = 0

    # Custom recursive visitor to support dotted names for nested classes & methods
    def visit_node(node: ast.AST, class_scope: list[str]) -> None:
        nonlocal global_max_nesting

        if isinstance(node, ast.ClassDef):
            current_class_name = ".".join(class_scope + [node.name])
            # Count methods directly or indirectly within this class
            methods = [
                n
                for n in node.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]

            line_start = node.lineno
            line_end = getattr(node, "end_lineno", line_start)

            classes.append({
                "name": current_class_name,
                "method_count": len(methods),
                "line_start": line_start,
                "line_end": line_end,
            })

            for child in node.body:
                visit_node(child, class_scope + [node.name])

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_name = (
                f"{'.'.join(class_scope)}.{node.name}"
                if class_scope
                else node.name
            )
            line_start = node.lineno
            line_end = getattr(node, "end_lineno", line_start)
            line_count = line_end - line_start + 1

            depth = _compute_max_depth_inside_function(node)
            if depth > global_max_nesting:
                global_max_nesting = depth

            functions.append({
                "name": func_name,
                "line_count": line_count,
                "nesting_depth": depth,
                "line_start": line_start,
            })

            # Check nested functions inside function body
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    visit_node(child, class_scope + [node.name])

        else:
            for child in ast.iter_child_nodes(node):
                if not isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    visit_node(child, class_scope)

    for top_node in tree.body:
        visit_node(top_node, [])

    return {
        "classes": classes,
        "functions": functions,
        "max_nesting_depth": global_max_nesting,
        "total_lines": total_lines,
    }
