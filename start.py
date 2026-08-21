"""Entrypoint script that initializes the knowledge base, reads PORT from environment, and starts uvicorn."""
import os
import logging
from pathlib import Path
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def ensure_knowledge_base():
    """Ensure ChromaDB vector store and BM25 index are built on startup if missing."""
    base_dir = Path(__file__).resolve().parent / "layer1_data"
    bm25_file = base_dir / "bm25_store.pkl"
    raw_dir = base_dir / "raw"
    processed_dir = base_dir / "processed"
    chroma_dir = base_dir / "chroma_store"

    if not bm25_file.exists() and raw_dir.exists():
        logger.info("Initializing knowledge base indexes from raw documentation...")
        try:
            from layer1_data.ingest import ingest_all
            from layer1_data.embed_index import build_index, load_all_chunks
            from layer1_data.bm25_index import build_bm25

            ingest_all(raw_dir=raw_dir, out_dir=processed_dir)
            chunks = load_all_chunks(processed_dir=str(processed_dir))
            build_index(chunks=chunks, persist_dir=str(chroma_dir))
            build_bm25(chunks=chunks, out_path=str(bm25_file))
            logger.info("Knowledge base indexes successfully initialized!")
        except Exception as exc:
            logger.error(f"Failed to build knowledge base indexes: {exc}", exc_info=True)



if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    ensure_knowledge_base()
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🚀 Starting SE Best Practices Assistant on port {port}...")
    uvicorn.run("layer6_api.main:app", host="0.0.0.0", port=port, log_level="info")

