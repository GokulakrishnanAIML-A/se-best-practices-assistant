from typing import TypedDict


class RawDoc(TypedDict):
    source: str  # folder name, e.g. "owasp"
    filepath: str
    raw_text: str


class Chunk(TypedDict):
    id: str  # f"{source}_{index:04d}"
    source: str
    title: str  # heading nearest to this chunk
    text: str  # 200-400 tokens
    url: str  # empty string if local note, else source URL
