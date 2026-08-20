"""Module 1.4 — Unified Knowledge Retriever (Hybrid Search & RRF).

Combines dense vector retrieval (Chroma) and sparse keyword retrieval (BM25)
using Reciprocal Rank Fusion (RRF), supporting source metadata filtering.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import chromadb

from layer1_data.bm25_index import DEFAULT_BM25_PATH, bm25_search, load_bm25_index
from layer1_data.embed_index import COLLECTION_NAME, EMBED_MODEL, PERSIST_DIR, get_embedding_model
from layer1_data.types import Chunk

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    """The central retrieval engine for the SE Best Practices Assistant."""

    def __init__(
        self,
        chroma_dir: str = PERSIST_DIR,
        bm25_path: str = DEFAULT_BM25_PATH,
        embed_model_name: str = EMBED_MODEL,
    ):
        """Load both Chroma and BM25 indices at construction and keep in memory."""
        self.chroma_dir = chroma_dir
        self.bm25_path = bm25_path
        self.embed_model_name = embed_model_name

        self._init_chroma()
        self._init_bm25()
        self._validate_id_alignment()

    def _init_chroma(self) -> None:
        """Initialize ChromaDB client, collection, and embedding model."""
        self.chroma_client = chromadb.PersistentClient(path=self.chroma_dir)
        try:
            self.collection = self.chroma_client.get_collection(COLLECTION_NAME)
        except Exception:
            logger.warning(
                f"Collection '{COLLECTION_NAME}' not found in Chroma store '{self.chroma_dir}'. Creating empty collection."
            )
            self.collection = self.chroma_client.create_collection(
                name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
            )
        self.embed_model = get_embedding_model(self.embed_model_name)

    def _init_bm25(self) -> None:
        """Load BM25 payload from disk if present."""
        if Path(self.bm25_path).exists():
            try:
                _, self.bm25_chunk_ids, _, self.bm25_lookup = load_bm25_index(self.bm25_path)
            except Exception as exc:
                logger.error(f"Error loading BM25 index: {exc}")
                self.bm25_chunk_ids = []
                self.bm25_lookup = {}
        else:
            logger.warning(f"BM25 index path '{self.bm25_path}' does not exist.")
            self.bm25_chunk_ids = []
            self.bm25_lookup = {}

    def _validate_id_alignment(self) -> None:
        """Verify alignment of chunk IDs between Chroma and BM25."""
        try:
            chroma_data = self.collection.get()
            chroma_ids = set(chroma_data.get("ids", []))
            bm25_ids = set(cid for cid in self.bm25_chunk_ids if cid)

            self.valid_sources: set[str] = set()
            metas = chroma_data.get("metadatas", []) or []
            for m in metas:
                if m and "source" in m:
                    self.valid_sources.add(m["source"])

            if chroma_ids and bm25_ids and chroma_ids != bm25_ids:
                diff_count = len(chroma_ids ^ bm25_ids)
                logger.warning(
                    f"Warning: Index mismatch detected! {diff_count} IDs differ between Chroma and BM25."
                )
        except Exception as exc:
            logger.warning(f"Could not validate ID alignment: {exc}")
            self.valid_sources = set()

    def _get_chunk_by_id(self, chunk_id: str) -> Chunk | None:
        """Retrieve full Chunk object given a chunk_id."""
        if chunk_id in self.bm25_lookup:
            return self.bm25_lookup[chunk_id]

        try:
            res = self.collection.get(ids=[chunk_id])
            if res and res["ids"] and len(res["ids"]) > 0:
                meta = res["metadatas"][0] if res["metadatas"] else {}
                doc = res["documents"][0] if res["documents"] else ""
                return Chunk(
                    id=chunk_id,
                    source=meta.get("source", ""),
                    title=meta.get("title", ""),
                    text=doc,
                    url=meta.get("url", ""),
                )
        except Exception as exc:
            logger.error(f"Failed to fetch chunk '{chunk_id}' from Chroma: {exc}")

        return None

    def search(
        self,
        query: str,
        source: str | None = None,
        k: int = 5,
        mode: str = "hybrid",
    ) -> list[Chunk]:
        """Search knowledge base using semantic, bm25, or hybrid mode.

        Args:
            query: User or agent search query string.
            source: Optional source domain filter (e.g. 'owasp', 'solid').
            k: Number of top results to return.
            mode: 'semantic' | 'bm25' | 'hybrid' (default).
        """
        query = (query or "").strip()
        if not query:
            return []

        # Validate source filter
        if source and self.valid_sources and source not in self.valid_sources:
            logger.warning(
                f"Source '{source}' does not match any indexed sources. Valid sources: {sorted(self.valid_sources)}"
            )
            return []

        if mode == "semantic":
            return self._search_semantic(query, source=source, k=k)
        elif mode == "bm25":
            return self._search_bm25(query, source=source, k=k)
        elif mode == "hybrid":
            return self._search_hybrid(query, source=source, k=k)
        else:
            raise ValueError(f"Unknown search mode '{mode}'. Choose 'semantic', 'bm25', or 'hybrid'.")

    def _search_semantic(self, query: str, source: str | None, k: int) -> list[Chunk]:
        """Retrieve results solely using dense semantic embeddings from Chroma."""
        query_embedding = self.embed_model.encode([query], normalize_embeddings=True).tolist()

        where_filter = {"source": source} if source else None
        try:
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=k,
                where=where_filter,
            )
        except Exception as exc:
            logger.error(f"Chroma query failed: {exc}")
            return []

        if not results or not results["ids"] or not results["ids"][0]:
            return []

        matched_chunks: list[Chunk] = []
        for i, chunk_id in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            doc_text = results["documents"][0][i] if results["documents"] else ""
            matched_chunks.append(
                Chunk(
                    id=chunk_id,
                    source=meta.get("source", ""),
                    title=meta.get("title", ""),
                    text=doc_text,
                    url=meta.get("url", ""),
                )
            )

        return matched_chunks

    def _search_bm25(self, query: str, source: str | None, k: int) -> list[Chunk]:
        """Retrieve results solely using BM25 keyword matching."""
        # Request more candidates to accommodate source filtering
        raw_results = bm25_search(query, index_path=self.bm25_path, k=max(k * 4, 20))

        matched_chunks: list[Chunk] = []
        for chunk_id, _ in raw_results:
            chunk = self._get_chunk_by_id(chunk_id)
            if not chunk:
                continue
            if source and chunk["source"] != source:
                continue
            matched_chunks.append(chunk)
            if len(matched_chunks) >= k:
                break

        return matched_chunks

    def _search_hybrid(self, query: str, source: str | None, k: int) -> list[Chunk]:
        """Fuse Chroma semantic and BM25 keyword results using Reciprocal Rank Fusion (RRF).

        RRF score = sum(1 / (60 + rank)) for each ranker where the item appears.
        """
        candidate_k = max(k * 2, 10)

        # 1. Semantic candidates
        semantic_chunks = self._search_semantic(query, source=source, k=candidate_k)
        semantic_ranks = {c["id"]: rank for rank, c in enumerate(semantic_chunks)}

        # 2. BM25 candidates
        bm25_chunks = self._search_bm25(query, source=source, k=candidate_k)
        bm25_ranks = {c["id"]: rank for rank, c in enumerate(bm25_chunks)}

        # 3. Reciprocal Rank Fusion (RRF) calculation
        all_candidate_ids = set(semantic_ranks.keys()) | set(bm25_ranks.keys())
        if not all_candidate_ids:
            return []

        rrf_scores: dict[str, float] = {}
        for cid in all_candidate_ids:
            score = 0.0
            if cid in semantic_ranks:
                score += 1.0 / (60.0 + semantic_ranks[cid] + 1)
            if cid in bm25_ranks:
                score += 1.0 / (60.0 + bm25_ranks[cid] + 1)
            rrf_scores[cid] = score

        # Sort candidate IDs descending by RRF score
        sorted_ids = sorted(all_candidate_ids, key=lambda x: rrf_scores[x], reverse=True)

        final_chunks: list[Chunk] = []
        for cid in sorted_ids[:k]:
            chunk = self._get_chunk_by_id(cid)
            if chunk:
                final_chunks.append(chunk)

        return final_chunks
