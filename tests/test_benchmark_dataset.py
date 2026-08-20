"""Acceptance tests for Module 5.1: Benchmark Evaluation Test Set."""

import json
from pathlib import Path
import pytest
from layer2_tools.ast_tool import analyze_structure
from layer2_tools.bandit_tool import run_bandit
from layer2_tools.radon_tool import analyze_complexity

VALID_PRINCIPLES = {
    "SRP",
    "OCP",
    "LSP",
    "ISP",
    "DIP",
    "OWASP-Injection",
    "OWASP-BrokenAuth",
    "long-function",
    "high-complexity",
    "poor-naming",
}

TEST_SET_DIR = Path("layer5_evaluation/test_set")
LABELS_PATH = TEST_SET_DIR / "labels.json"


def test_labels_file_exists_and_valid_json():
    assert LABELS_PATH.exists(), "labels.json must exist in test_set directory"
    with open(LABELS_PATH, "r", encoding="utf-8") as f:
        labels = json.load(f)
    assert isinstance(labels, dict)
    assert len(labels) == 16, f"Expected 16 test files in labels.json, got {len(labels)}"


def test_all_benchmark_files_exist_and_match_labels():
    with open(LABELS_PATH, "r", encoding="utf-8") as f:
        labels = json.load(f)

    for filename, violations in labels.items():
        file_path = TEST_SET_DIR / filename
        assert file_path.exists(), f"Benchmark file {filename} does not exist"

        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        total_lines = len(lines)
        assert 25 <= total_lines <= 120, f"{filename} has {total_lines} lines (expected 25-120)"

        assert len(violations) >= 2, f"{filename} has fewer than 2 ground truth violations"

        for v in violations:
            assert "principle" in v
            assert v["principle"] in VALID_PRINCIPLES, f"Unknown principle '{v['principle']}' in {filename}"

            assert "line_range" in v
            start, end = v["line_range"]
            assert 1 <= start <= end <= total_lines, f"Invalid line range [{start}, {end}] in {filename} (total lines: {total_lines})"

            assert "description" in v
            assert len(v["description"].strip()) > 10


def test_static_tools_signal_on_benchmark_files():
    # 1. Bandit on file_01 (SQLi)
    f1_code = (TEST_SET_DIR / "file_01.py").read_text(encoding="utf-8")
    sec_findings_f1 = run_bandit(f1_code)
    assert any("sql" in f["issue"].lower() or "injection" in f["issue"].lower() for f in sec_findings_f1)

    # 2. AST on file_04 (ISP / classes)
    f4_code = (TEST_SET_DIR / "file_04.py").read_text(encoding="utf-8")
    struct_f4 = analyze_structure(f4_code)
    assert len(struct_f4["classes"]) >= 1

    # 3. Radon on file_08 (high-complexity)
    f8_code = (TEST_SET_DIR / "file_08.py").read_text(encoding="utf-8")
    comp_f8 = analyze_complexity(f8_code)
    assert comp_f8["per_function"][0]["complexity"] > 10
