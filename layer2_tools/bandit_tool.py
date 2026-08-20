"""Module 2.2 — Bandit Security Scanner Tool.

Executes Bandit static analysis on Python code snippets to identify
security vulnerabilities (e.g. SQL injection, shell injection, hardcoded passwords).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import TypedDict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class SecurityFinding(TypedDict):
    severity: str  # LOW/MEDIUM/HIGH
    confidence: str  # LOW/MEDIUM/HIGH
    issue: str
    line: int
    cwe: str | None


def run_bandit(code: str) -> list[SecurityFinding]:
    """Run Bandit static security analysis on the provided Python code string.

    Captures stdout, parses JSON, and maps results to SecurityFinding dictionaries.
    Does not crash on non-zero exit codes (since Bandit exits non-zero when issues are found).
    """
    code_str = code or ""
    if not code_str.strip():
        return []

    tmp_file = tempfile.NamedTemporaryFile(suffix=".py", mode="w", encoding="utf-8", delete=False)
    tmp_path = tmp_file.name

    try:
        tmp_file.write(code_str)
        tmp_file.flush()
        tmp_file.close()

        # Run bandit via current Python interpreter to ensure venv isolation
        cmd = [sys.executable, "-m", "bandit", "-f", "json", "-q", tmp_path]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        stdout = result.stdout.strip()
        if not stdout:
            # Bandit may emit empty output if code has syntax errors or no results
            return []

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as exc:
            logger.warning(f"Could not parse Bandit JSON output: {exc}. Output: {stdout[:200]}")
            return []

        findings: list[SecurityFinding] = []
        raw_results = data.get("results", [])

        for item in raw_results:
            cwe_info = item.get("issue_cwe", {})
            cwe_str = f"CWE-{cwe_info.get('id')}" if isinstance(cwe_info, dict) and cwe_info.get("id") else None

            findings.append(
                SecurityFinding(
                    severity=str(item.get("issue_severity", "MEDIUM")).upper(),
                    confidence=str(item.get("issue_confidence", "MEDIUM")).upper(),
                    issue=str(item.get("issue_text", "")),
                    line=int(item.get("line_number", 1)),
                    cwe=cwe_str,
                )
            )

        return findings

    except FileNotFoundError:
        logger.error("Bandit executable not found on system PATH.")
        return []
    except subprocess.TimeoutExpired:
        logger.error("Bandit analysis timed out.")
        return []
    except Exception as exc:
        logger.error(f"Unexpected error running Bandit: {exc}")
        return []
    finally:
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except Exception:
            pass


if __name__ == "__main__":
    sample = 'import subprocess\nsubprocess.run("ping " + user_input, shell=True)\n'
    print(run_bandit(sample))
