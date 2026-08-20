"""Acceptance tests for Module 2.2: Bandit Tool."""

import pytest
from layer2_tools.bandit_tool import run_bandit


def test_bandit_detects_sql_injection():
    code = """
import sqlite3

def get_user(user_input):
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE id=" + user_input
    cursor.execute(query)
    return cursor.fetchall()
"""
    findings = run_bandit(code)
    assert len(findings) > 0
    assert any("sql" in f["issue"].lower() or "injection" in f["issue"].lower() for f in findings)
    assert all("severity" in f and "line" in f for f in findings)


def test_bandit_clean_code_returns_empty():
    code = """
def add(a: int, b: int) -> int:
    return a + b
"""
    findings = run_bandit(code)
    assert findings == []


def test_bandit_handles_empty_input():
    assert run_bandit("") == []
    assert run_bandit("   ") == []
