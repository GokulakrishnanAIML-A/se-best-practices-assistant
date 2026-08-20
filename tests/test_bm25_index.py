"""Acceptance tests for Module 1.3: BM25 Keyword Indexing."""

from pathlib import Path
import pytest
from layer1_data.bm25_index import bm25_search, build_bm25
from layer1_data.types import Chunk


def test_bm25_exact_keyword_ranks_high(tmp_path: Path):
    chunks: list[Chunk] = [
        Chunk(
            id="a",
            source="solid",
            title="LSP",
            text="Liskov Substitution Principle details and subclass contracts.",
            url="",
        ),
        Chunk(
            id="b",
            source="infra",
            title="K8s",
            text="Unrelated text about kubernetes pods and deployment controllers.",
            url="",
        ),
    ]
    out_path = str(tmp_path / "test_bm25.pkl")
    build_bm25(chunks, out_path=out_path)

    results = bm25_search("Liskov Substitution", index_path=out_path, k=2)
    assert len(results) >= 1
    assert results[0][0] == "a"


def test_bm25_empty_query_returns_empty(tmp_path: Path):
    chunks: list[Chunk] = [
        Chunk(id="a", source="s", title="T", text="Sample content", url=""),
    ]
    out_path = str(tmp_path / "test_bm25_empty.pkl")
    build_bm25(chunks, out_path=out_path)

    assert bm25_search("", index_path=out_path) == []
    assert bm25_search("   !@#$%^&*()   ", index_path=out_path) == []
