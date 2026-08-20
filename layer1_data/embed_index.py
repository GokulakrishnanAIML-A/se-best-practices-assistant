"""Module 1.2 — Chroma Vector Embedding and Indexing.

Embeds all chunks from layer1_data/processed/*.json using SentenceTransformer
and persists a Chroma collection.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer

from layer1_data.types import Chunk

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "se_best_practices"
PERSIST_DIR = "layer1_data/chroma_store"

# Global lazy-loaded embedding model cache to avoid re-loading weights repeatedly
_MODEL_CACHE: dict[str, SentenceTransformer] = {}


def get_embedding_model(model_name: str = EMBED_MODEL) -> SentenceTransformer:
    """Get or initialize cached SentenceTransformer model."""
    if model_name not in _MODEL_CACHE:
        logger.info(f"Loading embedding model '{model_name}'...")
        _MODEL_CACHE[model_name] = SentenceTransformer(model_name)
    return _MODEL_CACHE[model_name]


def load_all_chunks(processed_dir: str = "layer1_data/processed") -> list[Chunk]:
    """Concatenate every source's chunk JSON list from processed_dir into one flat list."""
    p_dir = Path(processed_dir)
    if not p_dir.exists():
        logger.warning(f"Processed directory '{processed_dir}' does not exist.")
        return []

    all_chunks: list[Chunk] = []
    for json_file in sorted(p_dir.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                source_chunks: list[Chunk] = json.load(f)
                if not source_chunks:
                    logger.warning(f"Empty chunk file for source: {json_file.name}")
                all_chunks.extend(source_chunks)
        except Exception as exc:
            logger.error(f"Error loading {json_file}: {exc}")

    return all_chunks


def build_index(
    chunks: list[Chunk],
    persist_dir: str = PERSIST_DIR,
    model_name: str = EMBED_MODEL,
    batch_size: int = 64,
) -> chromadb.Collection:
    """Embed chunks and index them into a persistent Chroma collection.

    Idempotent: Drops any existing collection before recreating it.
    """
    Path(persist_dir).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=persist_dir)

    # Delete existing collection if present to guarantee clean rebuild
    try:
        client.delete_collection(COLLECTION_NAME)
        logger.info(f"Deleted existing Chroma collection '{COLLECTION_NAME}' for clean rebuild.")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    if not chunks:
        logger.warning("No chunks provided to build_index. Returning empty collection.")
        return collection

    model = get_embedding_model(model_name)
    max_seq_len = getattr(model, "max_seq_length", 256)

    # Prepare data arrays
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []

    for c in chunks:
        ids.append(c["id"])
        text = c["text"]
        # Warn if text might exceed token length
        if len(text.split()) > max_seq_len:
            logger.warning(
                f"Chunk '{c['id']}' has ~{len(text.split())} words, which may exceed model max sequence length ({max_seq_len})."
            )
        documents.append(text)
        metadatas.append({
            "source": c["source"],
            "title": c["title"],
            "url": c.get("url", ""),
        })

    # Batch embedding computation & Chroma insertion
    total = len(chunks)
    logger.info(f"Embedding and indexing {total} chunks into Chroma (batch size: {batch_size})...")

    for start_idx in range(0, total, batch_size):
        end_idx = min(start_idx + batch_size, total)
        batch_docs = documents[start_idx:end_idx]
        batch_ids = ids[start_idx:end_idx]
        batch_metadatas = metadatas[start_idx:end_idx]

        batch_embeddings = model.encode(
            batch_docs,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).tolist()

        collection.add(
            ids=batch_ids,
            embeddings=batch_embeddings,
            documents=batch_docs,
            metadatas=batch_metadatas,
        )

    logger.info(f"Successfully indexed {collection.count()} chunks into Chroma collection '{COLLECTION_NAME}'.")
    return collection


if __name__ == "__main__":
    chunks = load_all_chunks()
    build_index(chunks)
    print(f"Indexed {len(chunks)} chunks into {PERSIST_DIR}")
