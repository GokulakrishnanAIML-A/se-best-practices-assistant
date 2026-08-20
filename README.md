# 🛡️ Software Engineering Best Practices Assistant

An enterprise-grade, agentic code review assistant that combines **Agentic RAG**, **Static Analysis Tools (Bandit, AST, Radon)**, and a **Self-Correction Reflection Loop** to evaluate Python code against industry standards:
- **SOLID Principles** (SRP, OCP, LSP, ISP, DIP)
- **OWASP Top 10 Security Risks** (SQL Injection, Command Injection, Broken Authentication)
- **Clean Code & PEP 8 Standards** (Naming conventions, function length, cyclomatic complexity)

---

## 🏗️ System Architecture

```
                                  ┌───────────────────────┐
                                  │   User Source Code    │
                                  └──────────┬────────────┘
                                             │
                                     [1. Planner Agent]
                                (Decomposes into 3-6 claims)
                                             │
                                             ▼
                                [2. Retriever Agent / Router]
                            (Keyword router -> Hybrid RRF search)
                                             │
                                             ▼
                                  [Static Tool Findings]
                             (Bandit + AST + Radon metrics)
                                             │
                                             ▼
                                     [3. Analyzer Agent]
                             (Grounding citations + Hallucination guard)
                                             │
                                             ▼
                                    [4. Reflection Agent]
                             (Grounding verification & self-critique)
                                   │                     ▲
                         (needs_revision=True)           │
                                   └─────────────────────┘
                                             │ (clean / max iterations)
                                             ▼
                                     [5. Reporter Module]
                               (Deterministic Markdown synthesis)
```

---

## 🚀 Quick Start

### 1. Local Environment Setup

```bash
# Clone the repository
git clone <repo-url>
cd "Agentic AI"

# Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env and supply your preferred API key (e.g. ANTHROPIC_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY)
```

### 3. Run the Backend API

```bash
uvicorn layer6_api.main:app --host 0.0.0.0 --port 8000 --reload
```
- API Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### 4. Run the Streamlit Frontend

In a separate terminal:
```bash
streamlit run layer7_frontend/app.py
```
- Frontend UI: `http://localhost:8501`

---

## 🐳 Docker Deployment

Run both the FastAPI backend and Streamlit frontend in orchestrated Docker containers:

```bash
# Build and start all services
docker compose -f layer8_deployment/docker-compose.yml up --build

# Access Services:
# - Streamlit Web Dashboard: http://localhost:8501
# - FastAPI REST API & Swagger: http://localhost:8000/docs
```

---

## 🧪 Test Suite Execution

Run the complete 70-test acceptance suite across all layers:

```bash
pytest tests/ -v
```

### Test Coverage Map:
- `tests/test_ingest.py`: Chunking, token limits, metadata extraction.
- `tests/test_embed_index.py`: ChromaDB dense indexing and querying.
- `tests/test_bm25_index.py`: BM25 sparse keyword ranking.
- `tests/test_retriever.py`: Hybrid Reciprocal Rank Fusion (RRF) search.
- `tests/test_ast_tool.py`: AST structural and God-class analysis.
- `tests/test_bandit_tool.py`: Bandit security scanning.
- `tests/test_radon_tool.py`: Radon cyclomatic complexity and Maintainability Index.
- `tests/test_tool_registry.py`: LangChain `@tool` callable registry.
- `tests/test_planner.py`: Review claim decomposition and retry logic.
- `tests/test_retriever_agent.py`: Keyword source routing and fallback search.
- `tests/test_analyzer.py`: Grounded finding extraction and hallucination filtering.
- `tests/test_reflection.py`: Grounding verification and revision loop routing.
- `tests/test_reporter.py`: Deterministic Markdown synthesis.
- `tests/test_graph.py`: LangGraph StateGraph cycle and termination guards.
- `tests/test_run.py`: End-to-end `run_review` pipeline execution.
- `tests/test_benchmark_dataset.py`: 16-file benchmark test set and `labels.json` validation.
- `tests/test_baselines.py`: No-RAG and Naive-RAG comparative baselines.
- `tests/test_metrics.py`: Detection Recall, Precision, F1, Groundedness, and Consistency metrics.
- `tests/test_eval_harness.py`: Multi-run evaluation benchmark harness.
- `tests/test_api.py`: FastAPI REST endpoints and Human-in-the-Loop (HITL) decision persistence.
- `tests/test_frontend.py`: Streamlit frontend components and payload serialization.

---

## 📊 Benchmark Evaluation Harness

To execute the quantitative comparison across **No-RAG**, **Naive RAG**, and **Agentic RAG**:

```python
from layer5_evaluation.run_eval import run_full_eval

results = run_full_eval(
    test_set_dir="layer5_evaluation/test_set",
    backends=["claude-sonnet-4-6"],
    out_csv="layer5_evaluation/results.csv",
    num_runs=3,
)
```

---

## 📁 Repository Structure

```
├── layer1_data/               # Knowledge Base & Hybrid RAG (Chroma + BM25)
├── layer2_tools/              # Static Analysis Tools (AST, Bandit, Radon)
├── layer3_agents/             # Planner, Retriever Agent, Analyzer, Reflection, Reporter
├── layer4_orchestration/      # LangGraph Review StateGraph & Runner
├── layer5_evaluation/         # Benchmark Dataset (16 files), Baselines, Metrics Engine
├── layer6_api/                # FastAPI REST API & HITL Decision endpoints
├── layer7_frontend/           # Streamlit Interactive Web Application
├── layer8_deployment/         # Dockerfile.api, Dockerfile.frontend, docker-compose.yml
├── .github/workflows/         # GitHub Actions CI Workflow
└── tests/                     # 70 Automated Acceptance Tests
```
