"""Module 1.3 — BM25 Sparse Keyword Indexing and Search.

Builds and queries BM25Okapi index over chunk texts for high-precision
keyword retrieval (e.g. "Liskov", "A01", "PEP 8", "SRP").
"""

from __future__ import annotations

import logging
from pathlib import Path
import pickle
import re
from typing import Any

from rank_bm25 import BM25Okapi

from layer1_data.embed_index import load_all_chunks
from layer1_data.types import Chunk

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_BM25_PATH = "layer1_data/bm25_store.pkl"

# Global memory cache for loaded BM25 index tuple
_BM25_CACHE: dict[str, tuple[BM25Okapi, list[str], list[list[str]], dict[str, Chunk]]] = {}


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase alphanumeric tokens, stripping punctuation."""
    if not text:
        return []
    return re.findall(r"[a-z0-9_]+", text.lower())


def build_bm25(
    chunks: list[Chunk],
    out_path: str = DEFAULT_BM25_PATH,
) -> BM25Okapi:
    """Build BM25Okapi index from chunk texts and persist index payload to out_path.

    Saves a tuple of (bm25_obj, chunk_ids, tokenized_corpus, chunks_by_id).
    """
    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    if not chunks:
        logger.warning("No chunks provided to build_bm25. Creating dummy empty index.")
        tokenized_corpus = [["empty"]]
        chunk_ids = [""]
        bm25_obj = BM25Okapi(tokenized_corpus)
        chunks_by_id = {}
    else:
        chunk_ids = [c["id"] for c in chunks]
        tokenized_corpus = [tokenize(f"{c['title']} {c['text']}") for c in chunks]
        bm25_obj = BM25Okapi(tokenized_corpus)
        chunks_by_id = {c["id"]: c for c in chunks}

    payload = (bm25_obj, chunk_ids, tokenized_corpus, chunks_by_id)

    with open(out_file, "wb") as f:
        pickle.dump(payload, f)

    # Invalidate cache
    _BM25_CACHE[str(out_file.resolve())] = payload
    logger.info(f"Built and saved BM25 index with {len(chunks)} documents to '{out_path}'.")

    return bm25_obj


def load_bm25_index(index_path: str = DEFAULT_BM25_PATH):
    """Load BM25 tuple from disk with in-memory caching."""
    resolved_path = str(Path(index_path).resolve())
    if resolved_path not in _BM25_CACHE:
        if not Path(index_path).exists():
            raise FileNotFoundError(f"BM25 index file not found at '{index_path}'.")
        with open(index_path, "rb") as f:
            _BM25_CACHE[resolved_path] = pickle.load(f)
    return _BM25_CACHE[resolved_path]


def bm25_search(
    query: str,
    index_path: str = DEFAULT_BM25_PATH,
    k: int = 5,
) -> list[tuple[str, float]]:
    """Query BM25 index for matching keywords.

    Returns [(chunk_id, score), ...] sorted descending by BM25 score.
    Returns [] immediately if query has no tokens.
    """
    tokenized_query = tokenize(query)
    if not tokenized_query:
        return []

    try:
        bm25_obj, chunk_ids, _, _ = load_bm25_index(index_path)
    except FileNotFoundError:
        logger.error(f"BM25 index at '{index_path}' does not exist.")
        return []

    if not chunk_ids or chunk_ids == [""]:
        return []

    scores = bm25_obj.get_scores(tokenized_query)

    # Pair chunk_id with score
    scored_results: list[tuple[str, float]] = []
    for idx, score in enumerate(scores):
        if idx < len(chunk_ids) and chunk_ids[idx]:
            scored_results.append((chunk_ids[idx], float(score)))

    # Sort descending by score
    scored_results.sort(key=lambda item: item[1], reverse=True)

    return scored_results[:k]


if __name__ == "__main__":
    chunks = load_all_chunks()
    build_bm25(chunks)
    print(f"Indexed {len(chunks)} chunks into {DEFAULT_BM25_PATH}")
