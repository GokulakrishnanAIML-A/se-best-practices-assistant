"""Acceptance tests for Module 3.6: Deterministic Reporter."""

from layer3_agents.reporter import format_report
from layer3_agents.state import Finding


def make_finding(severity: str, principle: str = "SRP", location: str = "line 10", cid: str = "chunk_01") -> Finding:
    return {
        "principle": principle,
        "evidence_chunk_id": cid,
        "severity": severity,
        "location": location,
        "explanation": f"Explanation for {principle}",
        "suggested_fix": f"Fix for {principle}",
    }


def test_format_report_groups_by_severity_and_counts_correctly():
    findings = [
        make_finding(severity="high", principle="OWASP-Injection"),
        make_finding(severity="low", principle="PEP8-Naming"),
        make_finding(severity="high", principle="DIP"),
        make_finding(severity="medium", principle="SRP"),
    ]
    report = format_report(findings, retrieved={})

    # Summary checks
    assert "4 findings — 2 high, 1 medium, 1 low" in report

    # Ordering check: High severity comes before Medium, and Medium comes before Low
    high_idx = report.index("## High Severity Issues")
    med_idx = report.index("## Medium Severity Issues")
    low_idx = report.index("## Low Severity Issues")
    assert high_idx < med_idx < low_idx

    # Alphabetical sorting within group: DIP before OWASP-Injection
    dip_idx = report.index("[HIGH] DIP")
    owasp_idx = report.index("[HIGH] OWASP-Injection")
    assert dip_idx < owasp_idx


def test_format_report_resolves_chunk_metadata_and_tool_sources():
    findings = [
        make_finding(severity="high", principle="OWASP-Injection", cid="chunk_sql"),
        make_finding(severity="medium", principle="SRP", cid="tool:ast"),
    ]
    retrieved = {
        "claim1": [
            {
                "id": "chunk_sql",
                "title": "OWASP A03 Injection Prevention",
                "url": "https://owasp.org/Top10/A03_2021-Injection/",
                "source": "owasp",
            }
        ]
    }
    report = format_report(findings, retrieved=retrieved)

    # Chunk citation check
    assert "OWASP A03 Injection Prevention" in report
    assert "https://owasp.org/Top10/A03_2021-Injection/" in report

    # Tool citation check
    assert "static analysis (ast)" in report


def test_format_report_handles_empty_findings():
    report = format_report([])
    assert "0 findings — 0 high, 0 medium, 0 low" in report
    assert "No best practice violations detected" in report
