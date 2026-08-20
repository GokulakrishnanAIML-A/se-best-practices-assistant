"""Module 1.1 — Document Ingestion and Chunking.

Converts raw documents in layer1_data/raw/<source>/ into normalized,
chunked JSON in layer1_data/processed/<source>.json.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import re
from typing import Any

from bs4 import BeautifulSoup
import tiktoken

from layer1_data.types import Chunk, RawDoc

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Tokenizer encoding
_ENCODER = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Return token count using cl100k_base encoding."""
    if not text:
        return 0
    return len(_ENCODER.encode(text))


def load_raw_docs(raw_dir: Path) -> list[RawDoc]:
    """Walk raw_dir/*/*.md (and .txt, .html) and return one RawDoc per file.

    HTML files: strip tags via BeautifulSoup, keep only text under <main>/<article> if present.
    Non-UTF8 files: catch UnicodeDecodeError, retry with errors='replace', log which file.
    Empty files: skipped with a warning.
    """
    raw_dir = Path(raw_dir)
    if not raw_dir.exists():
        logger.warning(f"Raw directory '{raw_dir}' does not exist.")
        return []

    docs: list[RawDoc] = []
    # Match all files in source subfolders
    for path in sorted(raw_dir.glob("*/*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".txt", ".html", ".htm"}:
            continue

        source = path.parent.name
        raw_text = ""

        try:
            raw_text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            logger.warning(f"Non-UTF8 file encountered: {path}. Retrying with errors='replace'.")
            try:
                raw_text = path.read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                logger.error(f"Failed to read file {path}: {exc}")
                continue
        except Exception as exc:
            logger.error(f"Error reading {path}: {exc}")
            continue

        if not raw_text.strip():
            logger.warning(f"Empty file skipped: {path}")
            continue

        if path.suffix.lower() in {".html", ".htm"}:
            soup = BeautifulSoup(raw_text, "html.parser")
            main_content = soup.find(["main", "article"])
            if main_content:
                raw_text = main_content.get_text(separator="\n", strip=True)
            else:
                raw_text = soup.get_text(separator="\n", strip=True)

            if not raw_text.strip():
                logger.warning(f"HTML file contains no extractable text: {path}")
                continue

        docs.append(
            RawDoc(
                source=source,
                filepath=str(path.as_posix()),
                raw_text=raw_text.strip(),
            )
        )

    return docs


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences while preserving sentence boundaries."""
    # Split on periods/exclamations/questions followed by whitespace, or newlines
    sentence_endings = re.compile(r"(?<=[.!?])\s+|\n+")
    parts = sentence_endings.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


def _chunk_large_section(
    section_text: str,
    title: str,
    source: str,
    start_index: int,
    target_tokens: int = 300,
    overlap_tokens: int = 30,
) -> list[Chunk]:
    """Recursively split a section exceeding token limits into smaller chunks."""
    sentences = _split_into_sentences(section_text)
    if not sentences:
        return []

    chunks: list[Chunk] = []
    current_sentences: list[str] = []
    current_token_count = 0
    idx = start_index

    i = 0
    while i < len(sentences):
        sent = sentences[i]
        sent_tokens = count_tokens(sent)

        # If a single sentence is excessively long, add it directly or truncate safely
        if sent_tokens > 450:
            if current_sentences:
                chunk_text = " ".join(current_sentences)
                chunks.append(
                    Chunk(
                        id=f"{source}_{idx:04d}",
                        source=source,
                        title=title,
                        text=chunk_text,
                        url="",
                    )
                )
                idx += 1
                current_sentences = []
                current_token_count = 0

            chunks.append(
                Chunk(
                    id=f"{source}_{idx:04d}",
                    source=source,
                    title=title,
                    text=sent[:1500],  # bounded text length
                    url="",
                )
            )
            idx += 1
            i += 1
            continue

        if current_token_count + sent_tokens > target_tokens and current_sentences:
            chunk_text = " ".join(current_sentences)
            chunks.append(
                Chunk(
                    id=f"{source}_{idx:04d}",
                    source=source,
                    title=title,
                    text=chunk_text,
                    url="",
                )
            )
            idx += 1

            # Compute overlap by stepping back sentences
            overlap_count = 0
            overlap_sentences: list[str] = []
            for prev_sent in reversed(current_sentences):
                prev_tokens = count_tokens(prev_sent)
                if overlap_count + prev_tokens <= overlap_tokens:
                    overlap_sentences.insert(0, prev_sent)
                    overlap_count += prev_tokens
                else:
                    break

            current_sentences = list(overlap_sentences)
            current_token_count = sum(count_tokens(s) for s in current_sentences)

        current_sentences.append(sent)
        current_token_count += sent_tokens
        i += 1

    if current_sentences:
        chunk_text = " ".join(current_sentences)
        chunks.append(
            Chunk(
                id=f"{source}_{idx:04d}",
                source=source,
                title=title,
                text=chunk_text,
                url="",
            )
        )

    return chunks


def chunk_document(
    doc: RawDoc,
    target_tokens: int = 300,
    overlap_tokens: int = 30,
) -> list[Chunk]:
    """Split on markdown headings first (##, ###) — one chunk per heading section if that

    section is <= ~450 tokens, else recursively split by paragraph with the given overlap.
    Never split mid-sentence. Use tiktoken 'cl100k_base' encoding to count tokens.
    """
    raw_text = doc["raw_text"].strip()
    if not raw_text:
        return []

    source = doc["source"]

    # Extract default document title from first # heading or filename
    doc_title_match = re.search(r"^#\s+(.+)$", raw_text, re.MULTILINE)
    default_title = doc_title_match.group(1).strip() if doc_title_match else Path(doc["filepath"]).stem

    # Split into sections based on ## or ### markdown headings
    heading_pattern = re.compile(r"^(#{2,3}\s+.+)$", re.MULTILINE)
    splits = heading_pattern.split(raw_text)

    # If no ## headings found, treat entire text as one section
    if len(splits) == 1:
        sections = [(default_title, raw_text)]
    else:
        sections: list[tuple[str, str]] = []
        lead_in = splits[0].strip()
        if lead_in:
            sections.append((default_title, lead_in))

        for i in range(1, len(splits), 2):
            heading_line = splits[i].strip()
            heading_title = re.sub(r"^#{2,3}\s+", "", heading_line).strip()
            section_body = splits[i + 1].strip() if i + 1 < len(splits) else ""
            full_section_text = f"{heading_line}\n\n{section_body}".strip()
            sections.append((heading_title, full_section_text))

    chunks: list[Chunk] = []
    chunk_index = 0

    for title, section_text in sections:
        if not section_text.strip():
            continue

        tokens = count_tokens(section_text)
        if tokens <= 450:
            chunks.append(
                Chunk(
                    id=f"{source}_{chunk_index:04d}",
                    source=source,
                    title=title,
                    text=section_text,
                    url="",
                )
            )
            chunk_index += 1
        else:
            sub_chunks = _chunk_large_section(
                section_text=section_text,
                title=title,
                source=source,
                start_index=chunk_index,
                target_tokens=target_tokens,
                overlap_tokens=overlap_tokens,
            )
            chunks.extend(sub_chunks)
            chunk_index += len(sub_chunks)

    # Re-index to ensure strictly consecutive, unique IDs per document
    for i, c in enumerate(chunks):
        c["id"] = f"{source}_{i:04d}"

    return chunks


def ingest_all(
    raw_dir: Path = Path("layer1_data/raw"),
    out_dir: Path = Path("layer1_data/processed"),
) -> dict[str, int]:
    """Runs load_raw_docs + chunk_document for every source subfolder.

    Writes out_dir/<source>.json as a list[Chunk].
    Returns {source: chunk_count} for a sanity-check printout.
    """
    raw_dir = Path(raw_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    docs = load_raw_docs(raw_dir)
    docs_by_source: dict[str, list[RawDoc]] = {}
    for doc in docs:
        docs_by_source.setdefault(doc["source"], []).append(doc)

    counts: dict[str, int] = {}

    for source, source_docs in docs_by_source.items():
        all_chunks: list[Chunk] = []
        for doc in source_docs:
            chunks = chunk_document(doc)
            all_chunks.extend(chunks)

        # Normalize chunk IDs across all docs in the same source
        for idx, chunk in enumerate(all_chunks):
            chunk["id"] = f"{source}_{idx:04d}"

        out_path = out_dir / f"{source}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f, indent=2, ensure_ascii=False)

        counts[source] = len(all_chunks)
        logger.info(f"Ingested {len(all_chunks)} chunks for source '{source}' -> {out_path}")

    return counts


if __name__ == "__main__":
    counts = ingest_all()
    for src, n in counts.items():
        print(f"{src}: {n} chunks")
