"""Acceptance tests for Modules 5.2 and 5.3: Baseline Review Systems."""

from layer5_evaluation.baseline_no_rag import NoRAGFinding, NoRAGReview, review_no_rag
from layer5_evaluation.baseline_naive_rag import NaiveRAGFinding, NaiveRAGReview, review_naive_rag


class MockNoRAGLLM:
    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        return NoRAGReview(
            findings=[
                NoRAGFinding(
                    principle="SRP",
                    severity="medium",
                    location="line 10",
                    explanation="Class handles too many responsibilities.",
                    suggested_fix="Split class.",
                )
            ]
        )


class MockNaiveRAGLLM:
    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        return NaiveRAGReview(
            findings=[
                NaiveRAGFinding(
                    principle="OWASP-Injection",
                    evidence_chunk_id="owasp_chunk_001",
                    severity="high",
                    location="line 15",
                    explanation="Raw SQL concatenation detected.",
                    suggested_fix="Use parameterized queries.",
                )
            ]
        )


class MockRetriever:
    def search(self, query: str, source: str | None = None, k: int = 5, mode: str = "hybrid"):
        return [
            {
                "id": "owasp_chunk_001",
                "source": "owasp",
                "text": "Prevent SQL injection by using query parameterization.",
            }
        ]


def test_review_no_rag_returns_findings_with_none_evidence():
    code = "class GodClass:\n    pass"
    findings = review_no_rag(code, llm=MockNoRAGLLM())
    assert len(findings) == 1
    assert findings[0]["principle"] == "SRP"
    assert findings[0]["evidence_chunk_id"] == "none"


def test_review_naive_rag_retrieves_single_shot_chunks():
    code = "def get_user(uid): db.execute(f'SELECT * FROM users WHERE id={uid}')"
    mock_retriever = MockRetriever()
    findings = review_naive_rag(code, retriever=mock_retriever, llm=MockNaiveRAGLLM())
    assert len(findings) == 1
    assert findings[0]["principle"] == "OWASP-Injection"
    assert findings[0]["evidence_chunk_id"] == "owasp_chunk_001"
