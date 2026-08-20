# Software Engineering Best Practices Assistant
### Agentic RAG-based Code & Architecture Review System
**Course:** Foundations of Agentic AI (AD23731) — Mini Project Implementation Plan

---

## 1. Problem Definition

**Problem statement:** Developers — especially junior ones and students — routinely violate SOLID principles, clean code conventions, and OWASP security guidelines without realizing it, because getting expert review is slow, expensive, and inconsistent. Static linters (pylint, ESLint) catch syntax-level issues but can't reason about *architectural* quality — is this class violating Single Responsibility? Is this endpoint vulnerable to OWASP A01 (Broken Access Control)? Should this be split into a factory pattern?

**Business case:** An agentic system that ingests a codebase or a design description, retrieves relevant guidance from an authoritative knowledge base (Clean Code, SOLID, OWASP, Google Engineering Practices, framework-specific docs), reasons over it, and produces an actionable, cited architecture review — with a human approving before any change is "accepted."

**Users:**
- Primary: student/junior developers wanting review before a PR
- Secondary: tech leads doing first-pass review triage
- Tertiary (stretch): your own capstone/project teams reviewing each other's code

**Expected outcome:** Given a code snippet, repo, or architecture description, the system returns a structured review — principle violated, evidence (cited source), severity, and a concrete fix — matching or exceeding a naive single-shot LLM review in precision and actionability.

---

## 2. Why This Maps Well to Every Rubric Line

| Rubric requirement | How this project satisfies it |
|---|---|
| Single vs multi-agent justification | Multi-agent: retrieval, analysis, and critique are functionally distinct and benefit from separation (see §3) |
| Reflection/self-correction | Dedicated Reflection agent critiques the first-pass review before it's shown to the user |
| Tool usage | AST parsing, static analyzers (bandit, pylint, semgrep) as callable tools |
| Stateful behavior/memory | LangGraph state graph carries code, retrieved chunks, draft review, critique across nodes; session memory across multiple files in one review |
| Agentic RAG (mandatory) | Query-decomposed, multi-source, iterative retrieval vs single-shot baseline (see §5) |
| Collaboration/HITL | Human approves/edits the final review before it's marked "applied"; optionally a second Analyzer agent cross-checks the first |
| Evaluation | Retrieval quality + LLM comparison (see §7) |

---

## 3. Agent Architecture

### 3.1 Design choice: multi-agent, LangGraph-orchestrated

Justification: a single agent doing retrieval + analysis + critique in one prompt tends to skip the self-correction step under token pressure and blends retrieval-grounding with reasoning, making it hard to evaluate each independently (a rubric requirement). Splitting into role-specialized agents also gives you a natural comparison point for the "reasoning, planning, reflection" evaluation criterion in Review 2.

```
User submits code/architecture description
        │
        ▼
   ┌─────────┐
   │ Planner │  → decomposes request into sub-queries
   └────┬────┘     e.g. "check SRP", "check OWASP injection risk",
        │           "check REST resource naming"
        ▼
   ┌─────────────┐
   │  Retriever   │  → agent-driven, per-domain retrieval (§5)
   │  (multi-src) │     OWASP / SOLID / Clean Code / framework docs
   └──────┬───────┘
          ▼
   ┌──────────────┐
   │   Analyzer    │  → runs static tools (AST, bandit, pylint) +
   │   (code+RAG)  │     grounds findings in retrieved passages
   └──────┬────────┘
          ▼
   ┌──────────────┐
   │  Reflection   │  → critiques draft: unsupported claims? missed
   │  (self-check) │     violation? contradicts retrieved source?
   └──────┬────────┘
          │ loop back to Analyzer if issues found (max 2 iterations)
          ▼
   ┌──────────────┐
   │ Report Writer │  → structured, cited final review
   └──────┬────────┘
          ▼
   ┌──────────────┐
   │  Human (HITL) │  → approve / edit / reject each finding
   └──────────────┘
```

### 3.2 Agent responsibilities

| Agent | Model role | Tools | Memory |
|---|---|---|---|
| Planner | Decompose the review request into checkable sub-claims | none (pure reasoning) | current session state |
| Retriever | Per sub-claim, choose which knowledge source(s) to query and how (semantic vs keyword) | vector search (FAISS/Chroma), BM25 | retrieval cache (avoid re-querying same sub-claim) |
| Analyzer | Ground code against retrieved passages; run static tools | AST parser, bandit (security), pylint/radon (complexity), semgrep (pattern rules) | full code + retrieved chunks for this session |
| Reflection | Score draft review for unsupported claims, missed violations, over-confidence | none, or a cheaper/smaller model for cost control | draft review + original retrieved evidence |
| Report Writer | Produce final structured output with citations | markdown formatter | approved findings across the session |

### 3.3 Framework choice

**LangGraph** is the right fit here — not CrewAI/AutoGen — because your flow has an explicit conditional loop (Reflection → back to Analyzer) and shared typed state, which LangGraph's graph-with-state model handles natively and cleanly, versus CrewAI's more linear task-handoff style. Use LangChain for the retriever/tool wrappers underneath.

---

## 4. Knowledge Base Construction

| Source | Format | Chunking strategy |
|---|---|---|
| Clean Code (Martin) — chapter summaries, not verbatim text (copyright) | your own notes/summaries | ~300 token chunks, one principle per chunk |
| SOLID principles | authoritative blog/doc summaries | one chunk per principle + examples |
| OWASP Top 10 (2021/2025) | OWASP official docs | one chunk per risk category (A01–A10) |
| Google Engineering Practices (public GitHub docs) | markdown from google/eng-practices repo | section-based chunking |
| Kubernetes docs | official docs (concepts + best practices sections only) | section-based |
| Spring Boot docs | official reference docs | section-based |
| Python docs / PEP 8 | official | section-based |

**Important:** don't scrape and store full copyrighted book text (e.g. Clean Code) verbatim in your vector store — summarize/paraphrase into your own notes for the corpus, and cite the source name + section, not reproduced text. This is also just good practice for your eval report's "data integrity" criterion.

**Embedding + store:** `sentence-transformers/all-MiniLM-L6-v2` (free, fast, good enough for this domain) or `text-embedding-3-small` if you want higher quality and don't mind API cost. Store in **Chroma** (simplest local setup) or FAISS if you want to reuse infra from your FinVerifyRAG capstone.

**Hybrid retrieval:** BM25 + semantic, same as your capstone — OWASP/SOLID terminology is precise enough that keyword matching genuinely helps (e.g. "A01" or "Liskov Substitution" should hit deterministically).

---

## 5. Agentic RAG Design (Mandatory Section — Weight This Heavily)

This is graded explicitly (Review 2: "Agentic RAG implementation and retrieval quality," 10 marks) and is your strongest differentiator vs a naive chatbot.

### 5.1 What makes it "agentic" vs naive RAG

| | Naive/Baseline RAG | Your Agentic RAG |
|---|---|---|
| Query | Whole user request embedded as-is | Planner decomposes into sub-claims, each retrieved separately |
| Retrieval calls | 1 (top-k once) | Multiple, targeted per sub-claim, per source |
| Source routing | Single vector index over everything | Router decides which corpus (OWASP vs SOLID vs framework docs) per sub-claim |
| Adaptivity | None | If Reflection agent flags a gap, Retriever re-queries with a refined query |
| Verification | None | Analyzer checks whether retrieved passage actually supports the claim before including it |

### 5.2 Baseline you must build for comparison (rubric requires it)

Build a **naive RAG baseline**: single retrieval call over the entire merged knowledge base, top-5 chunks, one-shot LLM review, no reflection loop. This is ~1 day of work reusing the same knowledge base and gives you a clean before/after comparison table for your report.

Also build a **no-RAG baseline**: LLM reviews code from parametric knowledge alone, no retrieval — this demonstrates hallucination rate and lack of citations, which is an easy, visually convincing comparison for your viva.

### 5.3 Metrics to report (ties into §7)

- **Retrieval precision@k** — of the retrieved chunks, how many were actually used/cited in the final review (manually label ~30–50 review outputs)
- **Groundedness** — % of findings in the final review that trace to an actual retrieved passage vs unsupported LLM claims
- **Coverage** — % of known-injected violations in your test codebase that were caught (see §7.1)

---

## 6. Core Agent Capabilities — Implementation Notes

### 6.1 Reflection / self-correction
Reflection agent prompt should explicitly check three things against the draft review: (1) every finding cites a retrieved passage, (2) the passage actually supports the specific claim (not just topically related), (3) no obvious violation category was skipped given the Planner's sub-claims. If any fail, route back to Analyzer with the specific gap — cap at 2 iterations to bound cost/latency.

### 6.2 Tool usage
- `ast` module (Python) or `tree-sitter` (multi-language) for structural facts (class/function boundaries, cyclomatic complexity)
- `bandit` for Python security static analysis (maps naturally to OWASP findings)
- `radon` for complexity/maintainability metrics
- Wrap each as a LangChain `@tool` so the Analyzer agent can call them autonomously rather than you hardcoding a pipeline

### 6.3 Stateful behavior / memory
- LangGraph's `StateGraph` with a typed state object (code, sub_claims, retrieved_chunks, draft_review, reflection_notes, iteration_count) — this state persisting and mutating across nodes *is* your memory story for the rubric, and is easy to demo live in your viva by printing the state at each node.
- Session-level memory: if a user reviews multiple files, cache retrieved chunks per principle so repeated queries (e.g. "SOLID" comes up in every file) don't re-hit the vector store.

### 6.4 Multi-agent / HITL
Satisfy both, since you have "at least one" required but showing both is stronger for the 10-mark orchestration criterion:
- **Multi-agent**: the 5-agent pipeline above
- **HITL**: after Report Writer, present findings with Accept/Edit/Reject per finding in your UI; rejected findings get logged (useful data for a future fine-tuning angle, and a nice "future work" line in your report)

---

## 7. Evaluation Plan

### 7.1 Build a small labeled test set
Take 15–20 real or intentionally-flawed code files (inject known SOLID violations, an OWASP-style SQL injection, a God class, etc.) so you have ground truth. This is the single highest-leverage thing you can do for your report — it turns "the agent gave a review" into "the agent caught 14/17 injected violations vs 8/17 for naive RAG vs 5/17 for no-RAG," which is a concrete, defensible number for your viva.

### 7.2 Metrics
- **Detection recall** against your labeled violations (§7.1)
- **Groundedness/citation accuracy** (§5.3)
- **Reasoning quality** — rubric-based human scoring (1–5) on a sample of outputs: does the fix suggested actually solve the stated problem?
- **Response consistency** — same code, run 3x, measure finding overlap (agentic systems can be noisy; worth reporting variance honestly)

### 7.3 LLM comparison (explicitly required by rubric)
Run the full pipeline with at least 2–3 backends and report the table:
- Claude Sonnet or GPT-4o-mini (strong baseline)
- A smaller/open model (Qwen2.5-7B or Llama-3.1-8B via Ollama) — cheap, good story about cost-quality tradeoff, and reuses infra know-how from your FinVerifyRAG SLM work
- Optionally your capstone's judge-LLM pattern (few-shot API judge) to auto-score the smaller model's outputs against the strong model's, saving you manual labeling time

---

## 8. Tech Stack Summary

| Layer | Choice |
|---|---|
| Orchestration | LangGraph |
| Retrieval | LangChain + Chroma/FAISS, hybrid BM25 + semantic |
| Embeddings | all-MiniLM-L6-v2 (local, free) or text-embedding-3-small |
| Static analysis tools | ast/tree-sitter, bandit, radon |
| LLM backends | Claude/GPT-4o-mini (primary) + Qwen2.5-7B or Llama-3.1-8B local (comparison) |
| Backend | FastAPI |
| Frontend | Streamlit (fastest for a working demo) — or React if you want a portfolio-grade UI later |
| Repo/report | GitHub repo + LaTeX or Word report using your dept template |

---

## 9. Timeline Against Your Actual Review Dates

| Milestone | Target | Deliverables |
|---|---|---|
| Now → end of July | Review 1 | Problem statement, KB sourcing done (§4), architecture diagram, tool/framework selection doc, project plan. **No code required yet** but a rough Planner+Retriever skeleton strengthens your individual presentation. |
| End July → ~1 week before CAT2 | Review 2 | Functional prototype: full 5-agent pipeline working end-to-end on at least 5 test files, naive-RAG baseline built, preliminary eval numbers (even partial) |
| Post Review 2 → End Sem | Viva | Full pipeline polished, HITL UI, complete labeled eval set run across all LLM backends, deployed demo (Streamlit Cloud or local + recorded demo video as backup), report + optionally a short paper draft if results are clean enough (your capstone already gives you a template for this) |

---

## 10. Stretch Ideas (only if time allows, don't scope-creep Review 1)

- Cross-file reasoning: flag SOLID violations that only show up across files (e.g. a service class doing another class's job)
- Auto-generate a "before/after" refactored code diff, not just prose — very demo-friendly for the viva
- Second Analyzer agent as a debate/cross-check partner instead of just Reflection — gives you a stronger "multi-agent collaboration" story if you want to lean harder into that rubric line instead of HITL

---

**Bottom line for Review 1 specifically:** you can get full marks on every criterion in that first rubric table using only §1, §2 (adapted into your own words), §3, and §4 — code isn't required yet, so prioritize a clean architecture diagram and a well-justified single-vs-multi-agent argument (§3.1) over premature implementation.
