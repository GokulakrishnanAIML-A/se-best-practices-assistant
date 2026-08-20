"""Acceptance tests for Module 1.2: Chroma Vector Indexing."""

import json
from pathlib import Path
import pytest
import chromadb
from layer1_data.embed_index import (
    COLLECTION_NAME,
    build_index,
    load_all_chunks,
)
from layer1_data.types import Chunk


def make_fake_chunks(n: int = 5) -> list[Chunk]:
    return [
        Chunk(
            id=f"test_{i:04d}",
            source="test",
            title=f"Principle {i}",
            text=f"This is test document {i} explaining software engineering principle {i}.",
            url="",
        )
        for i in range(n)
    ]


def test_build_index_idempotent(tmp_path: Path):
    chunks = make_fake_chunks(5)
    persist_dir = str(tmp_path / "chroma_test")

    # Run twice
    build_index(chunks, persist_dir=persist_dir)
    build_index(chunks, persist_dir=persist_dir)

    client = chromadb.PersistentClient(path=persist_dir)
    coll = client.get_collection(COLLECTION_NAME)
    assert coll.count() == 5  # Not 10


def test_build_index_queryable(tmp_path: Path):
    chunks = [
        Chunk(
            id="solid_0001",
            source="solid",
            title="Single Responsibility",
            text="A class should have one and only one reason to change and encapsulate a single responsibility.",
            url="",
        ),
        Chunk(
            id="owasp_0001",
            source="owasp",
            title="SQL Injection",
            text="SQL injection occurs when untrusted user input is directly concatenated into SQL queries without parameterized statements.",
            url="",
        ),
    ]
    persist_dir = str(tmp_path / "chroma_query_test")
    coll = build_index(chunks, persist_dir=persist_dir)

    # Query with semantic concept
    from layer1_data.embed_index import get_embedding_model
    model = get_embedding_model()
    q_emb = model.encode(["database SQL query attack"]).tolist()

    result = coll.query(query_embeddings=q_emb, n_results=1)
    assert result["ids"][0][0] == "owasp_0001"


def test_load_all_chunks(tmp_path: Path):
    processed = tmp_path / "processed"
    processed.mkdir(parents=True)

    with open(processed / "solid.json", "w", encoding="utf-8") as f:
        json.dump([{"id": "solid_0", "source": "solid", "title": "S", "text": "t1", "url": ""}], f)

    with open(processed / "owasp.json", "w", encoding="utf-8") as f:
        json.dump([{"id": "owasp_0", "source": "owasp", "title": "O", "text": "t2", "url": ""}], f)

    chunks = load_all_chunks(str(processed))
    assert len(chunks) == 2
    sources = {c["source"] for c in chunks}
    assert sources == {"solid", "owasp"}
