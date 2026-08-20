"""Acceptance tests for Module 2.3: Radon Tool."""

import pytest
from layer2_tools.radon_tool import analyze_complexity


def test_analyze_complexity_flags_high_complexity_function():
    code = "def f(x):\n" + "\n".join(f"    if x == {i}: return {i}" for i in range(15))
    report = analyze_complexity(code)
    assert len(report["per_function"]) == 1
    assert report["per_function"][0]["complexity"] > 10
    assert report["per_function"][0]["rank"] in {"C", "D", "E", "F"}


def test_analyze_complexity_handles_classes():
    code = """
class Worker:
    def simple_work(self):
        return True

    def heavy_work(self, val):
        if val > 10:
            return 1
        elif val > 5:
            return 2
        return 0
"""
    report = analyze_complexity(code)
    func_names = [f["name"] for f in report["per_function"]]
    assert "Worker.simple_work" in func_names
    assert "Worker.heavy_work" in func_names
    assert report["maintainability_index"] > 0


def test_analyze_complexity_handles_syntax_error():
    report = analyze_complexity("def invalid_syntax(:")
    assert report["per_function"] == []
    assert report["maintainability_index"] == 0.0
