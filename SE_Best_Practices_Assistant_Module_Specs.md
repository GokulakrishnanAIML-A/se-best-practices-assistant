# SE Best Practices Assistant — Module-Level Implementation Specs
### (For direct hand-off to Claude Code / Antigravity / Codex, one module per prompt)

Each module below is written as a standalone ticket: exact file path, full interface signatures, prompt text where an LLM call is involved, edge cases, and acceptance tests. Paste one module's section directly as a task to your agentic coding tool — it has everything needed to implement without referring back to earlier docs.

---

# LAYER 1 — DATA & KNOWLEDGE BASE

## Module 1.1 — `layer1_data/ingest.py`

**Purpose:** convert raw docs in `layer1_data/raw/<source>/` into normalized, chunked JSON in `layer1_data/processed/<source>.json`.

**Full interface:**
```python
from typing import TypedDict
from pathlib import Path

class RawDoc(TypedDict):
    source: str        # folder name, e.g. "owasp"
    filepath: str
    raw_text: str

class Chunk(TypedDict):
    id: str             # f"{source}_{index:04d}"
    source: str
    title: str          # heading nearest to this chunk
    text: str            # 200-400 tokens
    url: str               # empty string if local note, else source URL

def load_raw_docs(raw_dir: Path) -> list[RawDoc]:
    """Walk raw_dir/*/*.md (and .txt, .html) and return one RawDoc per file.
    HTML files: strip tags via BeautifulSoup, keep only text under <main>/<article> if present."""
    ...

def chunk_document(doc: RawDoc, target_tokens: int = 300, overlap_tokens: int = 30) -> list[Chunk]:
    """Split on markdown headings first (##, ###) — one chunk per heading section if that
    section is <= ~500 tokens, else recursively split by paragraph with the given overlap.
    Never split mid-sentence. Use tiktoken 'cl100k_base' encoding to count tokens."""
    ...

def ingest_all(raw_dir: Path = Path("layer1_data/raw"), out_dir: Path = Path("layer1_data/processed")) -> dict[str, int]:
    """Runs load_raw_docs + chunk_document for every source subfolder.
    Writes out_dir/<source>.json as a list[Chunk].
    Returns {source: chunk_count} for a sanity-check printout."""
    ...

if __name__ == "__main__":
    counts = ingest_all()
    for src, n in counts.items():
        print(f"{src}: {n} chunks")
```

**Edge cases to handle:**
- Empty files → skip, log a warning, don't crash the batch
- A single section longer than 500 tokens (e.g. one long OWASP page) → must recursively split, never emit a chunk over ~450 tokens
- Duplicate chunk IDs across re-runs → `ingest_all` must overwrite `processed/<source>.json` cleanly, not append
- Non-UTF8 files → catch `UnicodeDecodeError`, retry with `errors="replace"`, log which file

**Acceptance tests** (`tests/test_ingest.py`):
```python
def test_chunk_document_respects_token_limit():
    doc = {"source": "test", "filepath": "x.md", "raw_text": "## Heading\n" + "word " * 1000}
    chunks = chunk_document(doc, target_tokens=300)
    assert all(count_tokens(c["text"]) <= 450 for c in chunks)

def test_chunk_ids_unique_within_source():
    chunks = chunk_document(sample_doc)
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids))

def test_ingest_all_writes_json_per_source(tmp_path):
    # create tmp raw_dir with 2 sources, run ingest_all, assert 2 json files exist and are valid
    ...
```

---

## Module 1.2 — `layer1_data/embed_index.py`

**Purpose:** embed all chunks from `processed/*.json` and persist a Chroma collection.

**Full interface:**
```python
import chromadb
from sentence_transformers import SentenceTransformer

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "se_best_practices"
PERSIST_DIR = "layer1_data/chroma_store"

def load_all_chunks(processed_dir: str = "layer1_data/processed") -> list[Chunk]:
    """Concatenate every source's chunk list into one flat list."""
    ...

def build_index(chunks: list[Chunk], persist_dir: str = PERSIST_DIR) -> chromadb.Collection:
    """
    1. Instantiate chromadb.PersistentClient(path=persist_dir)
    2. get_or_create_collection(COLLECTION_NAME) — delete and recreate if it already exists
       (so re-running ingest doesn't leave stale vectors)
    3. Batch-embed chunk texts (batch size 64) with SentenceTransformer(EMBED_MODEL)
    4. collection.add(ids=[c['id'] for c in chunks], embeddings=..., documents=[c['text']...],
       metadatas=[{'source': c['source'], 'title': c['title'], 'url': c['url']} for c in chunks])
    """
    ...

if __name__ == "__main__":
    chunks = load_all_chunks()
    build_index(chunks)
    print(f"Indexed {len(chunks)} chunks into {PERSIST_DIR}")
```

**Edge cases:**
- Re-running must be idempotent — always drop and rebuild the collection, never silently duplicate
- Empty chunk list for a source (ingestion produced nothing) → warn but don't fail the whole build
- Chunk text longer than model's max sequence length (256 tokens for MiniLM) → truncate with a logged warning, since MiniLM silently truncates anyway — better to know

**Acceptance tests:**
```python
def test_build_index_idempotent(tmp_path):
    chunks = make_fake_chunks(5)
    build_index(chunks, persist_dir=str(tmp_path))
    build_index(chunks, persist_dir=str(tmp_path))  # run twice
    client = chromadb.PersistentClient(path=str(tmp_path))
    coll = client.get_collection(COLLECTION_NAME)
    assert coll.count() == 5   # not 10

def test_build_index_queryable(tmp_path):
    chunks = make_fake_chunks(3)
    coll = build_index(chunks, persist_dir=str(tmp_path))
    result = coll.query(query_texts=[chunks[0]["text"]], n_results=1)
    assert result["ids"][0][0] == chunks[0]["id"]
```

---

## Module 1.3 — `layer1_data/bm25_index.py`

**Full interface:**
```python
from rank_bm25 import BM25Okapi
import pickle

def build_bm25(chunks: list[Chunk], out_path: str = "layer1_data/bm25_store.pkl") -> BM25Okapi:
    """
    Tokenize each chunk['text'] via simple whitespace + lowercase + strip punctuation.
    Store (BM25Okapi_object, chunk_ids_in_order, tokenized_corpus) as a pickle tuple,
    so bm25_search can map result indices back to chunk IDs.
    """
    ...

def bm25_search(query: str, index_path: str = "layer1_data/bm25_store.pkl", k: int = 5) -> list[tuple[str, float]]:
    """Returns [(chunk_id, score), ...] sorted descending by score."""
    ...
```

**Edge cases:** empty query string → return `[]` immediately, don't call BM25 on empty tokens (raises internally in some versions).

**Acceptance test:**
```python
def test_bm25_exact_keyword_ranks_high():
    chunks = [{"id": "a", "text": "Liskov Substitution Principle details"},
              {"id": "b", "text": "unrelated text about kubernetes pods"}]
    build_bm25(chunks, out_path="/tmp/test_bm25.pkl")
    results = bm25_search("Liskov Substitution", index_path="/tmp/test_bm25.pkl", k=2)
    assert results[0][0] == "a"
```

---

## Module 1.4 — `layer1_data/retriever.py`

**Purpose:** the single interface every downstream layer calls. Combines Chroma (semantic) + BM25 via reciprocal rank fusion.

**Full interface:**
```python
class KnowledgeRetriever:
    def __init__(self, chroma_dir: str = PERSIST_DIR, bm25_path: str = "layer1_data/bm25_store.pkl"):
        """Load both indices once at construction; keep in memory for the life of the process."""
        ...

    def search(self, query: str, source: str | None = None, k: int = 5, mode: str = "hybrid") -> list[Chunk]:
        """
        mode='semantic': Chroma query only, optionally filtered by metadata {'source': source}
        mode='bm25': bm25_search only, then filter results to matching source post-hoc
        mode='hybrid': run both with k*2 candidates each, fuse via reciprocal rank fusion
            (score = sum(1 / (60 + rank)) across the two rankings), return top-k by fused score
        Returns full Chunk dicts (not just IDs) by looking up metadata from Chroma.
        """
        ...
```

**Edge cases:**
- `source` filter that matches zero chunks (typo in source name) → return `[]`, log a warning listing valid source names, don't raise
- `k` larger than total chunks available → return everything available, don't error
- Query embedding vs BM25 tokenization must use the same chunk ID space — verify at init that both indices were built from the same `processed/` snapshot (compare chunk ID sets, warn if mismatched)

**Acceptance tests:**
```python
def test_hybrid_search_returns_k_chunks():
    r = KnowledgeRetriever()
    results = r.search("SQL injection prevention", k=5)
    assert len(results) <= 5

def test_source_filter_respected():
    r = KnowledgeRetriever()
    results = r.search("dependency", source="solid", k=5)
    assert all(c["source"] == "solid" for c in results)

def test_unknown_source_returns_empty_not_error():
    r = KnowledgeRetriever()
    assert r.search("test", source="not_a_real_source") == []
```

---

# LAYER 2 — TOOL LAYER

## Module 2.1 — `layer2_tools/ast_tool.py`

**Full interface:**
```python
import ast

class StructureReport(TypedDict):
    classes: list[dict]     # [{name, method_count, line_start, line_end}]
    functions: list[dict]   # [{name, line_count, nesting_depth, line_start}]
    max_nesting_depth: int
    total_lines: int

def analyze_structure(code: str) -> StructureReport:
    """
    Parse with ast.parse(code). On SyntaxError, return a StructureReport with all fields
    empty/zero and an added 'parse_error': str(e) key — callers must check for this key.
    Walk the tree:
      - ast.ClassDef -> record name, count of ast.FunctionDef children, start/end lineno
      - ast.FunctionDef (module or class level) -> record name, line_count (end_lineno - lineno),
        nesting_depth (count of enclosing For/While/If/Try blocks via parent tracking)
    """
    ...
```

**Edge cases:**
- Code with a syntax error → must not raise; return `parse_error` field, Analyzer agent checks for it and skips structural findings gracefully
- Code using `async def` → treat as a function, same as `def`
- Nested classes → still counted, `name` should be dotted e.g. `Outer.Inner`

**Acceptance tests:**
```python
def test_analyze_structure_detects_god_class():
    code = "class Big:\n" + "\n".join(f"    def m{i}(self): pass" for i in range(20))
    report = analyze_structure(code)
    assert report["classes"][0]["method_count"] == 20

def test_analyze_structure_handles_syntax_error_gracefully():
    report = analyze_structure("def broken(:\n  pass")
    assert "parse_error" in report
```

## Module 2.2 — `layer2_tools/bandit_tool.py`

**Full interface:**
```python
import subprocess, json, tempfile

class SecurityFinding(TypedDict):
    severity: str    # LOW/MEDIUM/HIGH
    confidence: str
    issue: str
    line: int
    cwe: str | None

def run_bandit(code: str) -> list[SecurityFinding]:
    """
    Write code to a NamedTemporaryFile(suffix='.py'), run:
    ['bandit', '-f', 'json', '-q', <tmp_path>]
    capture stdout, parse JSON, map bandit's 'results' list into SecurityFinding.
    Bandit exits non-zero when it finds issues — that is EXPECTED, do not treat
    non-zero exit code as failure; only treat empty/invalid stdout as failure.
    Always clean up the temp file in a finally block.
    """
    ...
```

**Edge cases:** bandit not installed / not on PATH → catch `FileNotFoundError`, return `[]` with a logged error rather than crashing the whole Analyzer step. Code with zero findings → bandit returns valid JSON with empty `results` — must return `[]`, not error.

**Acceptance test:**
```python
def test_bandit_detects_sql_injection():
    code = 'query = "SELECT * FROM users WHERE id=" + user_input\ncursor.execute(query)'
    findings = run_bandit(code)
    assert any("sql" in f["issue"].lower() or "injection" in f["issue"].lower() for f in findings)
```

## Module 2.3 — `layer2_tools/radon_tool.py`

**Full interface:**
```python
from radon.complexity import cc_visit
from radon.metrics import mi_visit

class ComplexityReport(TypedDict):
    per_function: list[dict]   # [{name, complexity, rank}]
    maintainability_index: float

def analyze_complexity(code: str) -> ComplexityReport:
    """Use radon's cc_visit(code) for per-function cyclomatic complexity + letter rank (A-F),
    and mi_visit(code, multi=True) for maintainability index. Wrap both in try/except
    SyntaxError -> return empty per_function and maintainability_index=0.0."""
    ...
```

**Acceptance test:**
```python
def test_analyze_complexity_flags_high_complexity_function():
    code = "def f(x):\n" + "\n".join(f"    if x == {i}: return {i}" for i in range(15))
    report = analyze_complexity(code)
    assert report["per_function"][0]["complexity"] > 10
```

## Module 2.4 — `layer2_tools/tool_registry.py`

**Full interface:**
```python
from langchain_core.tools import tool
from layer2_tools.ast_tool import analyze_structure
from layer2_tools.bandit_tool import run_bandit
from layer2_tools.radon_tool import analyze_complexity

@tool
def check_structure(code: str) -> dict:
    """Analyze class/function structure: method counts, nesting depth, line counts.
    Use to detect God classes (>7-8 methods) or long functions (>50 lines)."""
    return analyze_structure(code)

@tool
def check_security(code: str) -> list[dict]:
    """Run static security analysis. Returns list of findings with severity, issue, line."""
    return run_bandit(code)

@tool
def check_complexity(code: str) -> dict:
    """Return cyclomatic complexity per function and overall maintainability index."""
    return analyze_complexity(code)

ALL_TOOLS = [check_structure, check_security, check_complexity]
```

**Acceptance test:** verify each tool is callable via `.invoke({"code": sample})` (LangChain's tool-calling interface) and returns JSON-serializable output — `json.dumps(result)` must not raise.

---

# LAYER 3 — AGENT LAYER

## Module 3.1 — `layer3_agents/state.py`

**Full interface:**
```python
from typing_extensions import TypedDict

class Finding(TypedDict):
    principle: str
    evidence_chunk_id: str
    severity: str          # 'low' | 'medium' | 'high'
    location: str            # "line 12" or "ClassName.method_name"
    explanation: str
    suggested_fix: str

class ReviewState(TypedDict):
    code: str
    sub_claims: list[str]
    retrieved: dict[str, list[dict]]     # sub_claim -> list[Chunk]
    tool_findings: dict                     # {structure, security, complexity}
    draft_review: list[Finding]
    reflection_notes: list[str]
    needs_revision: bool
    iteration_count: int
    final_review: list[Finding]
```
No logic here — pure schema. This file is imported by every agent and the graph; getting it stable first avoids churn later.

---

## Module 3.2 — `layer3_agents/planner.py`

**Full interface:**
```python
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate

class SubClaims(BaseModel):
    sub_claims: list[str]

PLANNER_SYSTEM_PROMPT = """You are a code review planner. Given a code snippet, produce a list \
of 3 to 6 specific, checkable review sub-claims covering: SOLID principles, security risks \
(OWASP-style), naming/readability, and complexity. Each sub-claim must be specific enough to \
map to a single retrieval query, e.g. "check for Single Responsibility Principle violations in \
class X" not "check code quality". Do not include claims unrelated to the code shown. \
Output ONLY the structured list, no commentary."""

def plan(code: str, llm) -> list[str]:
    """
    Build ChatPromptTemplate.from_messages([("system", PLANNER_SYSTEM_PROMPT), ("user", "{code}")])
    Bind llm.with_structured_output(SubClaims), invoke with {"code": code}, temperature=0.2.
    Return result.sub_claims. If the model returns fewer than 2 claims, retry once with an
    added user message: "Provide at least 3 distinct sub-claims."
    """
    ...
```

**Edge cases:** empty/whitespace-only code input → return a single sub_claim `["no code provided to review"]` without calling the LLM (save the API call). Code over ~8000 tokens → truncate to first 6000 tokens for the Planner call specifically (it only needs a broad view, not every line) and note truncation in a log.

**Acceptance tests:**
```python
def test_plan_returns_multiple_distinct_claims():
    claims = plan(sample_code_with_god_class, llm=get_test_llm())
    assert 3 <= len(claims) <= 6
    assert len(set(claims)) == len(claims)  # no duplicates

def test_plan_empty_code_short_circuits(monkeypatch):
    monkeypatch.setattr("layer3_agents.planner.llm_call_count", lambda: pytest.fail("should not call LLM"))
    claims = plan("", llm=None)
    assert claims == ["no code provided to review"]
```

---

## Module 3.3 — `layer3_agents/retriever_agent.py`

**Full interface:**
```python
SOURCE_KEYWORDS = {
    "owasp": ["injection", "security", "authentication", "access control", "vulnerability", "xss", "csrf"],
    "solid": ["responsibility", "srp", "open/closed", "liskov", "interface segregation", "dependency inversion", "solid"],
    "clean_code": ["naming", "readability", "function length", "clean code", "comment"],
    "python": ["pep 8", "pythonic", "convention"],
}

def route_source(sub_claim: str) -> str | None:
    """Lowercase sub_claim, check for keyword overlap against SOURCE_KEYWORDS.
    Return the source with the most keyword hits; if no keywords match, return None
    (search across all sources unfiltered)."""
    ...

def retrieve_for_claims(sub_claims: list[str], retriever: KnowledgeRetriever, k: int = 3) -> dict[str, list[dict]]:
    """
    For each sub_claim:
      1. source = route_source(sub_claim)
      2. chunks = retriever.search(sub_claim, source=source, k=k, mode='hybrid')
      3. LOG the routing decision: print/log f"'{sub_claim}' -> source={source}, {len(chunks)} chunks"
         (this log is your rubric evidence for 'agent-driven retrieval strategy' — keep it)
    Return {sub_claim: chunks}.
    """
    ...
```

**Edge cases:** a sub_claim that routes to a source with zero results → fall back to an unfiltered `mode='hybrid'` search across all sources before giving up, so a routing miss doesn't produce zero evidence for that claim.

**Acceptance test:**
```python
def test_route_source_picks_owasp_for_security_claim():
    assert route_source("check for SQL injection vulnerabilities") == "owasp"

def test_route_source_returns_none_for_ambiguous_claim():
    assert route_source("general code quality check") is None

def test_retrieve_for_claims_falls_back_on_empty_source_match():
    # mock retriever.search to return [] for source='solid', non-empty for source=None
    result = retrieve_for_claims(["check SRP"], mock_retriever)
    assert len(result["check SRP"]) > 0
```

---

## Module 3.4 — `layer3_agents/analyzer.py`

**Full interface:**
```python
from pydantic import BaseModel, field_validator

class DraftReview(BaseModel):
    findings: list[Finding]

    @field_validator("findings")
    def evidence_must_be_present(cls, findings, info):
        valid_ids = info.data.get("_valid_chunk_ids", set())
        for f in findings:
            if not f["evidence_chunk_id"]:
                raise ValueError(f"Finding on '{f['principle']}' has no evidence_chunk_id")
        return findings

ANALYZER_SYSTEM_PROMPT = """You are a code analyzer grounding findings in retrieved reference \
material and static tool output. For EVERY finding you produce, you MUST cite an evidence_chunk_id \
from the provided retrieved chunks — do not state a principle violation without a matching chunk id. \
If tool_findings indicate a security or complexity issue with no matching retrieved chunk, still \
report it but set evidence_chunk_id to the string "tool:<tool_name>" instead of a chunk id. \
Cover every sub_claim provided; if a sub_claim has no issues, do not fabricate one — simply omit it \
from findings. Output ONLY the structured findings list."""

def analyze(code: str, sub_claims: list[str], retrieved: dict, tool_findings: dict, llm) -> list[Finding]:
    """
    1. Flatten retrieved into a numbered context block: for each sub_claim, list its chunks
       as "[{chunk_id}] ({source}) {text}"
    2. Build prompt: system=ANALYZER_SYSTEM_PROMPT, user=f"Code:\n{code}\n\nSub-claims:\n{sub_claims}\n
       \nRetrieved evidence:\n{context_block}\n\nTool findings:\n{tool_findings}"
    3. llm.with_structured_output(DraftReview), temperature=0.3
    4. Post-validate: for every finding with evidence_chunk_id not starting with 'tool:',
       confirm the id exists in the flattened retrieved chunk id set. Drop (with a logged
       warning) any finding whose chunk id doesn't actually exist — this is a hallucination
       guard independent of the LLM's own honesty.
    Return the validated findings list.
    """
    ...
```

**Edge cases:** LLM returns a finding citing a chunk_id from a *different* sub_claim's retrieval set than the one it's discussing — still valid as long as the id exists somewhere in `retrieved`; don't over-constrain to per-claim matching. LLM returns zero findings on clearly flawed code (under-triggering) → this is a legitimate outcome to log for your consistency metric, not an error to retry.

**Acceptance tests:**
```python
def test_analyze_drops_findings_with_fabricated_chunk_id(monkeypatch):
    # mock llm to return a finding with evidence_chunk_id="does_not_exist_123"
    findings = analyze(code, sub_claims, retrieved={"claim1": [{"id": "real_001", ...}]}, tool_findings={}, llm=mock_llm)
    assert all(f["evidence_chunk_id"] in {"real_001"} or f["evidence_chunk_id"].startswith("tool:") for f in findings)

def test_analyze_accepts_tool_prefixed_evidence():
    findings = analyze(code, [], retrieved={}, tool_findings={"security": [{"issue": "SQLi", "line": 5}]}, llm=mock_llm_that_cites_tool)
    assert any(f["evidence_chunk_id"].startswith("tool:") for f in findings)
```

---

## Module 3.5 — `layer3_agents/reflection.py`

**Full interface:**
```python
class ReflectionResult(BaseModel):
    notes: list[str]
    needs_revision: bool

REFLECTION_SYSTEM_PROMPT = """You are a strict reviewer of a draft code review. Check three things:
1. GROUNDING: for each finding, does the cited evidence chunk's text actually support the specific
   claim made (not just topically related)? Flag any mismatch by finding index.
2. COVERAGE: do the findings collectively address all given sub_claims? List any sub_claim with
   zero corresponding findings AND zero indication the claim was checked-and-clean.
3. OVER-CONFIDENCE: flag any finding using absolute language ("always", "never", "definitely wrong")
   without hedging appropriate to a static-analysis-grounded review.
Set needs_revision=true if any GROUNDING mismatch is found (coverage gaps and over-confidence alone
do not require another full iteration — note them but set needs_revision based on grounding only,
to bound the reflection loop to genuine errors rather than style nitpicks)."""

def reflect(draft_review: list[Finding], retrieved: dict, sub_claims: list[str], llm) -> ReflectionResult:
    """
    Pass the draft findings AND the full text of every cited evidence chunk (look up by id from
    retrieved) so the reflection LLM can actually verify grounding, not just re-read the claim.
    Use a smaller/cheaper model here if configured (see config.py in Layer 4) — this agent's
    task is narrower and doesn't need the strongest model.
    """
    ...
```

**Edge cases:** `draft_review` is empty (Analyzer found nothing) → skip the LLM call, return `ReflectionResult(notes=["no findings to review"], needs_revision=False)` directly — don't spend a call reflecting on nothing. A finding citing `tool:*` evidence → skip grounding-check for that finding (there's no chunk text to verify against), only check it isn't over-confident.

**Acceptance test:**
```python
def test_reflect_catches_grounding_mismatch():
    draft = [{"principle": "SRP", "evidence_chunk_id": "c1", "explanation": "violates SRP", ...}]
    retrieved = {"claim1": [{"id": "c1", "text": "This chunk is about OWASP injection, unrelated to SRP"}]}
    result = reflect(draft, retrieved, ["claim1"], llm=get_test_llm())
    assert result.needs_revision is True

def test_reflect_skips_llm_call_on_empty_draft(monkeypatch):
    monkeypatch.setattr(llm, "invoke", lambda *a: pytest.fail("should not be called"))
    result = reflect([], {}, [], llm=llm)
    assert result.needs_revision is False
```

---

## Module 3.6 — `layer3_agents/reporter.py`

**Full interface:**
```python
def format_report(findings: list[Finding], retrieved: dict) -> str:
    """
    Pure templating, NO LLM call (keeps report formatting deterministic — do not add
    variance here that would pollute the consistency metric).
    Group findings by severity (high, medium, low), within each group sort by principle name.
    For each finding, render:
        ### [{severity.upper()}] {principle} — {location}
        {explanation}
        **Suggested fix:** {suggested_fix}
        **Source:** {source_title} ({url or 'internal notes'})
    Look up source_title/url from retrieved chunks matching evidence_chunk_id; if evidence_chunk_id
    starts with 'tool:', render "**Source:** static analysis ({tool_name})" instead.
    Prepend a one-line summary: "N findings — H high, M medium, L low".
    Return the full markdown string.
    """
    ...
```

**Acceptance test:**
```python
def test_format_report_groups_by_severity_and_counts_correctly():
    findings = [make_finding(severity="high"), make_finding(severity="low"), make_finding(severity="high")]
    report = format_report(findings, retrieved={})
    assert "2 high" in report or "H high" in report.lower()
    assert report.index("HIGH") < report.index("LOW")  # high-severity section comes first
```

---

# LAYER 4 — ORCHESTRATION

## Module 4.1 — `layer4_orchestration/config.py`

```python
from dataclasses import dataclass

@dataclass
class PipelineConfig:
    planner_model: str = "claude-sonnet-4-6"
    analyzer_model: str = "claude-sonnet-4-6"
    reflection_model: str = "claude-haiku-4-5"   # cheaper model for the narrower reflection task
    max_reflection_iterations: int = 2
    retrieval_k: int = 3
```

## Module 4.2 — `layer4_orchestration/graph.py`

**Full interface:**
```python
from langgraph.graph import StateGraph, END
from layer3_agents.state import ReviewState

def planner_node(state: ReviewState) -> dict:
    """Calls plan(), returns {'sub_claims': ..., 'iteration_count': 0}"""
    ...

def retriever_node(state: ReviewState) -> dict:
    """Calls retrieve_for_claims(), returns {'retrieved': ...}"""
    ...

def analyzer_node(state: ReviewState) -> dict:
    """Calls check_structure/check_security/check_complexity tools if not already in state,
    then calls analyze(), returns {'draft_review': ..., 'tool_findings': ...,
    'iteration_count': state['iteration_count'] + 1}"""
    ...

def reflection_node(state: ReviewState) -> dict:
    """Calls reflect(), returns {'reflection_notes': ..., 'needs_revision': ...}"""
    ...

def reporter_node(state: ReviewState) -> dict:
    """Calls format_report(), returns {'final_review': state['draft_review']}
    (report text itself returned separately by run(), not stored in state)"""
    ...

def route_after_reflection(state: ReviewState) -> str:
    if state["needs_revision"] and state["iteration_count"] < config.max_reflection_iterations:
        return "analyzer"
    return "reporter"

def build_graph() -> "CompiledGraph":
    g = StateGraph(ReviewState)
    g.add_node("planner", planner_node)
    g.add_node("retriever", retriever_node)
    g.add_node("analyzer", analyzer_node)
    g.add_node("reflection", reflection_node)
    g.add_node("reporter", reporter_node)
    g.set_entry_point("planner")
    g.add_edge("planner", "retriever")
    g.add_edge("retriever", "analyzer")
    g.add_edge("analyzer", "reflection")
    g.add_conditional_edges("reflection", route_after_reflection, {"analyzer": "analyzer", "reporter": "reporter"})
    g.add_edge("reporter", END)
    return g.compile()
```

**Edge cases:** `iteration_count` must be incremented in `analyzer_node`, not `reflection_node` — otherwise the loop-guard counts reflections instead of analyzer passes and can off-by-one the max-iteration cap. Test this explicitly (see below), it's the most common bug in this kind of graph.

**Acceptance tests:**
```python
def test_graph_terminates_within_max_iterations():
    app = build_graph()
    # use a mock reflection that ALWAYS returns needs_revision=True
    result = app.invoke({"code": sample_code, "iteration_count": 0}, config={"recursion_limit": 20})
    assert result["iteration_count"] <= config.max_reflection_iterations

def test_graph_full_state_trace_has_all_nodes(capsys):
    app = build_graph()
    for event in app.stream({"code": sample_code}):
        print(list(event.keys())[0])
    out = capsys.readouterr().out
    for node in ["planner", "retriever", "analyzer", "reflection", "reporter"]:
        assert node in out
```

## Module 4.3 — `layer4_orchestration/run.py`

```python
def run_review(code: str) -> dict:
    """Entry point. app = build_graph(); result = app.invoke({'code': code, 'iteration_count': 0}).
    Returns {'findings': result['final_review'], 'report_markdown': format_report(...),
    'iteration_count': result['iteration_count']}."""
    ...
```

---

# LAYER 5 — EVALUATION

## Module 5.1 — Labeled test set builder

**Deliverable:** `layer5_evaluation/test_set/labels.json`
```json
{
  "file_01.py": [
    {"principle": "SRP", "line_range": [10, 45], "description": "UserManager class handles auth, logging, and DB writes"},
    {"principle": "OWASP A03 (Injection)", "line_range": [22, 22], "description": "raw string concatenation into SQL query"}
  ]
}
```
**Build instructions for the agentic coder:** generate 15–20 Python files, each 40–120 lines, by taking small real-world-style modules (a user service, a payment handler, an API client) and deliberately injecting 2–3 violations each from this fixed list so coverage is balanced: `[SRP, OCP, LSP, ISP, DIP, OWASP-Injection, OWASP-BrokenAuth, long-function, high-complexity, poor-naming]`. Record exact line ranges in `labels.json` — these are ground truth, must be hand-verified, not LLM-generated.

## Module 5.2 — `layer5_evaluation/baseline_no_rag.py`

```python
def review_no_rag(code: str, llm) -> list[Finding]:
    """Single LLM call, system prompt: 'Review this code for SOLID, security, and quality
    issues. List each issue with principle, severity, location, explanation.' No tools,
    no retrieval, no evidence_chunk_id field (set to 'none' for schema compatibility with
    the same Finding type used elsewhere, so metrics.py can score all three systems uniformly)."""
    ...
```

## Module 5.3 — `layer5_evaluation/baseline_naive_rag.py`

```python
def review_naive_rag(code: str, retriever: KnowledgeRetriever, llm) -> list[Finding]:
    """ONE retrieval call: retriever.search(code[:2000], k=5, mode='hybrid') — no sub-claim
    decomposition, no source routing, no reflection loop. Single LLM call combining code +
    the 5 retrieved chunks, same output schema as review_no_rag but with real evidence_chunk_id
    values this time."""
    ...
```

## Module 5.4 — `layer5_evaluation/metrics.py`

```python
def detection_recall(predicted: list[Finding], ground_truth: list[dict]) -> float:
    """A ground-truth violation counts as 'caught' if any predicted finding's line_range
    overlaps AND principle matches (fuzzy match: 'SRP' matches 'Single Responsibility
    Principle', use a small alias dict). recall = caught / len(ground_truth)."""
    ...

def groundedness(findings: list[Finding], retrieved_or_chunks_lookup: dict) -> float:
    """% of findings (excluding 'tool:' and 'none' evidence) whose cited chunk_id exists
    AND whose chunk text has non-trivial lexical/semantic overlap with the finding's
    explanation (use a cheap LLM-judge call: 'Does this evidence support this claim? yes/no',
    batch these to control cost — this is the automatable version of manual labeling)."""
    ...

def consistency(runs: list[list[Finding]]) -> float:
    """Given 3 runs of the SAME input, compute pairwise principle-set overlap
    (Jaccard on the set of {principle} across findings in each run), average across
    the 3 pairs."""
    ...
```

**Acceptance tests:**
```python
def test_detection_recall_perfect_match():
    gt = [{"principle": "SRP", "line_range": [1, 10]}]
    pred = [{"principle": "SRP", "location": "line 5", ...}]
    assert detection_recall(pred, gt) == 1.0

def test_detection_recall_zero_when_nothing_predicted():
    assert detection_recall([], [{"principle": "SRP", "line_range": [1, 10]}]) == 0.0

def test_consistency_full_overlap_scores_one():
    same_findings = [{"principle": "SRP"}, {"principle": "DIP"}]
    assert consistency([same_findings, same_findings, same_findings]) == 1.0
```

## Module 5.5 — `layer5_evaluation/run_eval.py`

```python
def run_full_eval(test_set_dir: str, backends: list[str], out_csv: str = "results.csv"):
    """
    For each file in test_set_dir, for each system in [no_rag, naive_rag, agentic],
    for each backend model, for 3 repeated runs (for consistency metric):
        run the system, collect Finding list, compute detection_recall against labels.json,
        compute groundedness (skip for no_rag), store per-run results.
    After all runs, compute consistency per (file, system, backend) triple across its 3 runs.
    Write one row per (system, backend) averaged across all files to out_csv:
    columns = [system, backend, avg_detection_recall, avg_groundedness, avg_consistency, avg_latency_sec]
    """
    ...
```

---

# LAYER 6 — API

## Module 6.1 — `layer6_api/schemas.py`

```python
from pydantic import BaseModel

class ReviewRequest(BaseModel):
    code: str
    filename: str | None = None

class ReviewResponse(BaseModel):
    findings: list[Finding]
    report_markdown: str
    iteration_count: int

class HITLDecisionRequest(BaseModel):
    finding_index: int
    decision: str    # 'accept' | 'edit' | 'reject'
    edited_text: str | None = None   # required if decision == 'edit'
```

## Module 6.2 — `layer6_api/routes/review.py`

```python
from fastapi import APIRouter, HTTPException
router = APIRouter()

# in-memory store for MVP; swap for SQLite/Postgres if you want persistence across restarts
_SESSIONS: dict[str, ReviewResponse] = {}

@router.post("/review", response_model=ReviewResponse)
async def review_code(req: ReviewRequest) -> ReviewResponse:
    if not req.code.strip():
        raise HTTPException(400, "code field is empty")
    if len(req.code) > 50_000:
        raise HTTPException(413, "code exceeds 50000 char limit for this MVP")
    result = run_review(req.code)
    session_id = str(uuid4())
    resp = ReviewResponse(**result)
    _SESSIONS[session_id] = resp
    return resp   # include session_id in a response header: X-Session-Id

@router.post("/review/{session_id}/decision")
async def hitl_decision(session_id: str, req: HITLDecisionRequest):
    if session_id not in _SESSIONS:
        raise HTTPException(404, "unknown session")
    if req.decision == "edit" and not req.edited_text:
        raise HTTPException(400, "edited_text required when decision='edit'")
    # persist decision — append to a decisions.jsonl log for later "future work" analysis
    ...
```

**Acceptance tests:**
```python
def test_review_endpoint_rejects_empty_code(client):
    resp = client.post("/review", json={"code": "   "})
    assert resp.status_code == 400

def test_review_endpoint_happy_path(client):
    resp = client.post("/review", json={"code": "def f(): pass"})
    assert resp.status_code == 200
    assert "findings" in resp.json()

def test_hitl_decision_requires_edited_text_for_edit(client):
    session_id = client.post("/review", json={"code": "def f(): pass"}).headers["X-Session-Id"]
    resp = client.post(f"/review/{session_id}/decision", json={"finding_index": 0, "decision": "edit"})
    assert resp.status_code == 400
```

---

# LAYER 7 — FRONTEND

## Module 7.1 — `layer7_frontend/app.py`

**Precise implementation instructions:**
```python
import streamlit as st, requests

API_BASE = "http://localhost:8000"

st.title("SE Best Practices Assistant")
uploaded = st.file_uploader("Upload a Python file", type=["py"])
code_input = st.text_area("...or paste code", height=200) if not uploaded else None

if st.button("Review") and (uploaded or code_input):
    code = uploaded.read().decode() if uploaded else code_input
    with st.spinner("Running agentic review..."):
        resp = requests.post(f"{API_BASE}/review", json={"code": code})
    if resp.status_code != 200:
        st.error(resp.json().get("detail", "review failed"))
    else:
        data = resp.json()
        session_id = resp.headers.get("X-Session-Id")
        st.session_state["findings"] = data["findings"]
        st.session_state["session_id"] = session_id

if "findings" in st.session_state:
    severity_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    for i, f in enumerate(st.session_state["findings"]):
        with st.container(border=True):
            st.markdown(f"{severity_color.get(f['severity'], '⚪')} **{f['principle']}** — `{f['location']}`")
            st.write(f["explanation"])
            st.code(f["suggested_fix"], language="python")
            col1, col2, col3 = st.columns(3)
            if col1.button("Accept", key=f"accept_{i}"):
                requests.post(f"{API_BASE}/review/{st.session_state['session_id']}/decision",
                              json={"finding_index": i, "decision": "accept"})
                st.toast("Accepted")
            if col2.button("Reject", key=f"reject_{i}"):
                requests.post(f"{API_BASE}/review/{st.session_state['session_id']}/decision",
                              json={"finding_index": i, "decision": "reject"})
                st.toast("Rejected")
            # Edit: show a text_area + confirm button, only when col3 clicked (use st.session_state
            # toggle per finding index to avoid re-render collapsing the edit box)
```

**Edge case:** API unreachable (connection refused) → wrap the `requests.post` call in try/except `requests.exceptions.ConnectionError`, show `st.error("Backend not running — start the API with uvicorn first")` instead of an unhandled traceback.

---

# LAYER 8 — DEPLOYMENT

## Module 8.1 — `layer8_deployment/Dockerfile.api`
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt
COPY layer1_data/ layer1_data/
COPY layer2_tools/ layer2_tools/
COPY layer3_agents/ layer3_agents/
COPY layer4_orchestration/ layer4_orchestration/
COPY layer6_api/ layer6_api/
EXPOSE 8000
CMD ["uvicorn", "layer6_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Module 8.2 — `layer8_deployment/Dockerfile.frontend`
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements-frontend.txt .
RUN pip install --no-cache-dir -r requirements-frontend.txt
COPY layer7_frontend/ layer7_frontend/
EXPOSE 8501
CMD ["streamlit", "run", "layer7_frontend/app.py", "--server.address=0.0.0.0"]
```

## Module 8.3 — `layer8_deployment/docker-compose.yml`
```yaml
services:
  api:
    build:
      context: ..
      dockerfile: layer8_deployment/Dockerfile.api
    ports: ["8000:8000"]
    volumes:
      - chroma_data:/app/layer1_data/chroma_store   # persist vector index across restarts
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
  frontend:
    build:
      context: ..
      dockerfile: layer8_deployment/Dockerfile.frontend
    ports: ["8501:8501"]
    environment:
      - API_BASE=http://api:8000
    depends_on: [api]
volumes:
  chroma_data:
```

**Edge case:** `frontend`'s `API_BASE` must be the docker-network service name (`http://api:8000`), not `localhost` — `localhost` inside the frontend container refers to itself, not the API container. This is the single most common docker-compose bug for this kind of two-service setup; make `app.py`'s `API_BASE` read from an environment variable (not hardcoded) specifically so this works both in local dev (`localhost`) and in compose (`http://api:8000`).

## Module 8.4 — `.github/workflows/ci.yml`
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.11"}
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest tests/ -v
      - run: ruff check .
```

---

## How to Use This With an Agentic Coding Tool

Feed one module section at a time as a task, in the build order from the previous doc (Layer 1 → 2 → 5.1 → 3 → 4 → 5.2-5.5 → 6 → 7 → 8). Each section is self-contained enough that the agent doesn't need the rest of this document in context — just paste the module's heading through its acceptance tests. After each module, run its acceptance tests before moving to the next; this catches integration bugs (like the `iteration_count` increment location in Module 4.2) at the cheapest possible point rather than during a full pipeline run.
