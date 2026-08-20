"""Acceptance tests for Module 1.4: Unified Knowledge Retriever."""

from pathlib import Path
import pytest
from layer1_data.bm25_index import build_bm25
from layer1_data.embed_index import build_index
from layer1_data.retriever import KnowledgeRetriever
from layer1_data.types import Chunk


@pytest.fixture
def sample_retriever(tmp_path: Path) -> KnowledgeRetriever:
    chunks: list[Chunk] = [
        Chunk(
            id="solid_0001",
            source="solid",
            title="Single Responsibility",
            text="Single Responsibility Principle: A class should have only one reason to change.",
            url="",
        ),
        Chunk(
            id="solid_0002",
            source="solid",
            title="Liskov Substitution",
            text="Liskov Substitution Principle: Subtypes must be substitutable for base types without breaking correctness.",
            url="",
        ),
        Chunk(
            id="owasp_0001",
            source="owasp",
            title="SQL Injection",
            text="A03 Injection: SQL injection occurs when untrusted input is passed to dynamic SQL queries without parameterized statements.",
            url="",
        ),
        Chunk(
            id="owasp_0002",
            source="owasp",
            title="Broken Access Control",
            text="A01 Broken Access Control: Failure to enforce least privilege and user permission checks.",
            url="",
        ),
        Chunk(
            id="clean_code_0001",
            source="clean_code",
            title="Small Functions",
            text="Functions should be small and do one thing well with single level of abstraction.",
            url="",
        ),
    ]

    chroma_dir = str(tmp_path / "chroma")
    bm25_file = str(tmp_path / "bm25.pkl")

    build_index(chunks, persist_dir=chroma_dir)
    build_bm25(chunks, out_path=bm25_file)

    return KnowledgeRetriever(chroma_dir=chroma_dir, bm25_path=bm25_file)


def test_hybrid_search_returns_k_chunks(sample_retriever: KnowledgeRetriever):
    results = sample_retriever.search("SQL injection prevention", k=2, mode="hybrid")
    assert len(results) <= 2
    assert any("injection" in c["text"].lower() for c in results)


def test_source_filter_respected(sample_retriever: KnowledgeRetriever):
    results = sample_retriever.search("responsibility and security", source="solid", k=5, mode="hybrid")
    assert len(results) > 0
    assert all(c["source"] == "solid" for c in results)


def test_unknown_source_returns_empty_not_error(sample_retriever: KnowledgeRetriever):
    results = sample_retriever.search("SQL injection", source="non_existent_source", k=5)
    assert results == []


def test_different_search_modes(sample_retriever: KnowledgeRetriever):
    semantic_res = sample_retriever.search("Liskov Substitution", mode="semantic", k=1)
    bm25_res = sample_retriever.search("Liskov Substitution", mode="bm25", k=1)
    hybrid_res = sample_retriever.search("Liskov Substitution", mode="hybrid", k=1)

    assert len(semantic_res) == 1
    assert len(bm25_res) == 1
    assert len(hybrid_res) == 1
    assert hybrid_res[0]["id"] == "solid_0002"
