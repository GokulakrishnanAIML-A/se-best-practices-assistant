"""Acceptance tests for Module 1.1: Ingest & Chunking."""

import json
from pathlib import Path
import pytest
from layer1_data.ingest import chunk_document, count_tokens, ingest_all, load_raw_docs
from layer1_data.types import RawDoc


def test_chunk_document_respects_token_limit():
    doc: RawDoc = {
        "source": "test",
        "filepath": "x.md",
        "raw_text": "## Big Section\n" + "Software engineering best practices demand clean code. " * 80,
    }
    chunks = chunk_document(doc, target_tokens=300)
    assert len(chunks) > 1
    assert all(count_tokens(c["text"]) <= 450 for c in chunks)


def test_chunk_ids_unique_within_source():
    doc: RawDoc = {
        "source": "solid",
        "filepath": "solid.md",
        "raw_text": """# SOLID
## SRP
Single responsibility.
## OCP
Open closed principle.
## LSP
Liskov substitution.
""",
    }
    chunks = chunk_document(doc)
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids))
    assert all(cid.startswith("solid_") for cid in ids)


def test_ingest_all_writes_json_per_source(tmp_path: Path):
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"

    # Create two source directories with sample files
    src1 = raw_dir / "owasp"
    src1.mkdir(parents=True)
    (src1 / "doc.md").write_text("## SQL Injection\nNever concatenate queries.", encoding="utf-8")

    src2 = raw_dir / "clean_code"
    src2.mkdir(parents=True)
    (src2 / "doc.md").write_text("## Naming\nUse descriptive names.", encoding="utf-8")

    counts = ingest_all(raw_dir=raw_dir, out_dir=processed_dir)

    assert counts.get("owasp") == 1
    assert counts.get("clean_code") == 1

    owasp_json = processed_dir / "owasp.json"
    clean_json = processed_dir / "clean_code.json"
    assert owasp_json.exists()
    assert clean_json.exists()

    with open(owasp_json, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert len(data) == 1
        assert data[0]["source"] == "owasp"
        assert "SQL Injection" in data[0]["title"]


def test_load_raw_docs_handles_empty_and_non_utf8(tmp_path: Path):
    raw_dir = tmp_path / "raw"
    src = raw_dir / "edge_cases"
    src.mkdir(parents=True)

    # Empty file
    (src / "empty.md").write_text("", encoding="utf-8")

    # Valid file
    (src / "valid.md").write_text("## Valid\nContent here.", encoding="utf-8")

    # Non-UTF8 file
    (src / "latin.md").write_bytes("## Latin\nCafé résumé\n".encode("latin-1"))

    docs = load_raw_docs(raw_dir)
    assert len(docs) == 2  # empty.md is skipped
    filenames = [Path(d["filepath"]).name for d in docs]
    assert "empty.md" not in filenames
    assert "valid.md" in filenames
    assert "latin.md" in filenames
