"""Acceptance tests for Module 3.3: Retriever Agent & Keyword Source Router."""

from layer3_agents.retriever_agent import route_source, retrieve_for_claims
from layer1_data.retriever import KnowledgeRetriever


class MockRetriever:
    def __init__(self):
        self.calls = []

    def search(self, query: str, source: str | None = None, k: int = 3, mode: str = "hybrid"):
        self.calls.append({"query": query, "source": source, "k": k, "mode": mode})
        if source == "solid":
            # Simulate a miss for fallback testing
            return []
        return [{"id": f"chunk_test_{query[:5]}", "text": "Test knowledge chunk content", "source": source or "all"}]


def test_route_source_picks_owasp_for_security_claim():
    assert route_source("check for SQL injection vulnerabilities in login") == "owasp"
    assert route_source("verify user authentication and password storage") == "owasp"


def test_route_source_picks_solid_for_architectural_claim():
    assert route_source("check Single Responsibility Principle in UserManager") == "solid"
    assert route_source("verify Dependency Inversion in Service layer") == "solid"


def test_route_source_picks_clean_code_and_python():
    assert route_source("check naming conventions and function length") == "clean_code"
    assert route_source("verify adherence to PEP 8 style guide") == "python"


def test_route_source_returns_none_for_ambiguous_claim():
    assert route_source("general code quality check") is None
    assert route_source("is this good code") is None


def test_retrieve_for_claims_falls_back_on_empty_source_match():
    mock = MockRetriever()
    # "check SRP" routes to 'solid', which MockRetriever returns [] for, triggering fallback to source=None
    result = retrieve_for_claims(["check SRP in class"], mock, k=3)
    assert len(result["check SRP in class"]) > 0
    # Verify two calls were made: first with source='solid', second fallback with source=None
    assert len(mock.calls) == 2
    assert mock.calls[0]["source"] == "solid"
    assert mock.calls[1]["source"] is None


def test_retrieve_for_claims_integrates_with_real_retriever():
    retriever = KnowledgeRetriever()
    claims = [
        "check for SQL injection vulnerabilities",
        "check for Single Responsibility Principle",
    ]
    results = retrieve_for_claims(claims, retriever, k=2)
    assert len(results) == 2
    for claim, chunks in results.items():
        assert len(chunks) > 0
        assert "id" in chunks[0]
        assert "text" in chunks[0]
