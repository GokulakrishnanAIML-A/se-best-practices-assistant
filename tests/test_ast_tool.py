"""Acceptance tests for Module 2.1: AST Tool."""

import pytest
from layer2_tools.ast_tool import analyze_structure


def test_analyze_structure_detects_god_class():
    code = "class Big:\n" + "\n".join(f"    def m{i}(self): pass" for i in range(20))
    report = analyze_structure(code)
    assert len(report["classes"]) == 1
    assert report["classes"][0]["name"] == "Big"
    assert report["classes"][0]["method_count"] == 20


def test_analyze_structure_handles_syntax_error_gracefully():
    report = analyze_structure("def broken(:\n  pass")
    assert "parse_error" in report
    assert report["classes"] == []
    assert report["functions"] == []


def test_analyze_structure_nesting_depth_and_line_count():
    code = """
def complex_fn(a, b):
    if a > 0:
        for i in range(10):
            while b > 0:
                try:
                    b -= 1
                except Exception:
                    pass
    return b
"""
    report = analyze_structure(code)
    assert len(report["functions"]) == 1
    assert report["functions"][0]["name"] == "complex_fn"
    assert report["functions"][0]["nesting_depth"] == 4  # if -> for -> while -> try
    assert report["max_nesting_depth"] == 4


def test_analyze_structure_nested_classes_and_async():
    code = """
class Outer:
    class Inner:
        async def do_async(self):
            pass
"""
    report = analyze_structure(code)
    class_names = [c["name"] for c in report["classes"]]
    assert "Outer" in class_names
    assert "Outer.Inner" in class_names
    assert report["classes"][1]["method_count"] == 1
