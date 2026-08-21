"""Pytest configuration and session-wide test fixtures."""

import pytest
from start import ensure_knowledge_base


@pytest.fixture(scope="session", autouse=True)
def setup_test_knowledge_base():
    """Ensure ChromaDB vector store and BM25 index exist before running test suite."""
    ensure_knowledge_base()
