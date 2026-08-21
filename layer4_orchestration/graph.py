"""Module 4.2: LangGraph Orchestration Workflow with Self-Correction Cycle."""

import logging
from typing import Any
from langgraph.graph import StateGraph, END
from layer3_agents.state import ReviewState
from layer3_agents.planner import plan
from layer3_agents.retriever_agent import retrieve_for_claims
from layer3_agents.analyzer import analyze
from layer3_agents.reflection import reflect
from layer3_agents.reporter import format_report
from layer1_data.retriever import KnowledgeRetriever
from layer2_tools.ast_tool import analyze_structure
from layer2_tools.bandit_tool import run_bandit
from layer2_tools.radon_tool import analyze_complexity
from layer4_orchestration.config import PipelineConfig, get_llm

logger = logging.getLogger(__name__)


def create_nodes(
    config: PipelineConfig,
    retriever: KnowledgeRetriever,
    planner_llm: Any,
    analyzer_llm: Any,
    reflection_llm: Any,
):
    """Factory to create LangGraph state graph nodes with bound dependencies."""

    def planner_node(state: ReviewState) -> dict[str, Any]:
        logger.info("📋 [1/5 Agent: Planner] Analyzing code requirements and breaking down evaluation claims...")
        code = state.get("code", "")
        sub_claims = plan(code, llm=planner_llm)
        logger.info(f"📋 [1/5 Agent: Planner] Generated {len(sub_claims)} sub-claims: {sub_claims}")
        return {
            "sub_claims": sub_claims,
            "iteration_count": 0,
            "reflection_notes": [],
            "needs_revision": False,
        }

    def retriever_node(state: ReviewState) -> dict[str, Any]:
        logger.info("🔍 [2/5 Agent: Retriever] Routing claims to hybrid vector/BM25 knowledge base...")
        sub_claims = state.get("sub_claims", [])
        retrieved = retrieve_for_claims(sub_claims, retriever=retriever, k=config.retrieval_k)
        total_chunks = sum(len(chunks) for chunks in retrieved.values())
        logger.info(f"🔍 [2/5 Agent: Retriever] Retrieved {total_chunks} authoritative evidence chunks across {len(retrieved)} claims.")
        return {"retrieved": retrieved}

    def analyzer_node(state: ReviewState) -> dict[str, Any]:
        current_iter = state.get("iteration_count", 0) + 1
        logger.info(f"🔬 [3/5 Agent: Analyzer] Running static tools & generating grounded review (Pass {current_iter})...")
        code = state.get("code", "")
        sub_claims = state.get("sub_claims", [])
        retrieved = state.get("retrieved", {})

        # Compute static tool findings if not already present in state
        tool_findings = state.get("tool_findings")
        if not tool_findings:
            logger.info("⚡ Executing static analysis suite: AST parser, Bandit security scanner, Radon complexity metrics...")
            structure_res = analyze_structure(code)
            security_res = run_bandit(code)
            complexity_res = analyze_complexity(code)
            tool_findings = {
                "structure": structure_res,
                "security": security_res,
                "complexity": complexity_res,
            }

        draft_review = analyze(
            code=code,
            sub_claims=sub_claims,
            retrieved=retrieved,
            tool_findings=tool_findings,
            llm=analyzer_llm,
        )
        logger.info(f"🔬 [3/5 Agent: Analyzer] Produced {len(draft_review)} candidate findings.")

        return {
            "draft_review": draft_review,
            "tool_findings": tool_findings,
            # iteration_count MUST increment in analyzer_node per spec
            "iteration_count": current_iter,
        }

    def reflection_node(state: ReviewState) -> dict[str, Any]:
        logger.info("🧐 [4/5 Agent: Reflection] Auditing findings for groundedness and hallucination suppression...")
        draft_review = state.get("draft_review", [])
        retrieved = state.get("retrieved", {})
        sub_claims = state.get("sub_claims", [])

        reflection_res = reflect(
            draft_review=draft_review,
            retrieved=retrieved,
            sub_claims=sub_claims,
            llm=reflection_llm,
        )
        logger.info(f"🧐 [4/5 Agent: Reflection] Needs revision: {reflection_res.needs_revision} | Notes: {reflection_res.notes}")

        return {
            "reflection_notes": reflection_res.notes,
            "needs_revision": reflection_res.needs_revision,
        }

    def reporter_node(state: ReviewState) -> dict[str, Any]:
        logger.info("📊 [5/5 Agent: Reporter] Compiling and formatting final structured review report...")
        draft_review = state.get("draft_review", [])
        return {
            "final_review": draft_review,
        }

    def route_after_reflection(state: ReviewState) -> str:
        needs_rev = state.get("needs_revision", False)
        iter_count = state.get("iteration_count", 0)
        logger.info(
            f"🔄 [Routing Decision] Revision needed={needs_rev} | Iteration={iter_count}/{config.max_reflection_iterations}"
        )
        if needs_rev and iter_count < config.max_reflection_iterations:
            logger.info("🔁 Re-routing to Analyzer for grounded correction cycle...")
            return "analyzer"
        logger.info("✅ Verification passed. Routing to Reporter.")
        return "reporter"


    return (
        planner_node,
        retriever_node,
        analyzer_node,
        reflection_node,
        reporter_node,
        route_after_reflection,
    )


def build_graph(
    config: PipelineConfig | None = None,
    retriever: KnowledgeRetriever | None = None,
    planner_llm: Any = None,
    analyzer_llm: Any = None,
    reflection_llm: Any = None,
) -> Any:
    """Build and compile the LangGraph Review StateGraph.

    Args:
        config: Pipeline configuration.
        retriever: Hybrid KnowledgeRetriever instance.
        planner_llm: Custom or mocked planner LLM.
        analyzer_llm: Custom or mocked analyzer LLM.
        reflection_llm: Custom or mocked reflection LLM.

    Returns:
        Compiled StateGraph executable runnable.
    """
    if config is None:
        config = PipelineConfig()

    if retriever is None:
        retriever = KnowledgeRetriever()

    if planner_llm is None:
        planner_llm = get_llm(config.planner_model, temperature=0.2)
    if analyzer_llm is None:
        analyzer_llm = get_llm(config.analyzer_model, temperature=0.3)
    if reflection_llm is None:
        reflection_llm = get_llm(config.reflection_model, temperature=0.1)

    (
        p_node,
        r_node,
        a_node,
        ref_node,
        rep_node,
        route_fn,
    ) = create_nodes(
        config=config,
        retriever=retriever,
        planner_llm=planner_llm,
        analyzer_llm=analyzer_llm,
        reflection_llm=reflection_llm,
    )

    g = StateGraph(ReviewState)
    g.add_node("planner", p_node)
    g.add_node("retriever", r_node)
    g.add_node("analyzer", a_node)
    g.add_node("reflection", ref_node)
    g.add_node("reporter", rep_node)

    g.set_entry_point("planner")
    g.add_edge("planner", "retriever")
    g.add_edge("retriever", "analyzer")
    g.add_edge("analyzer", "reflection")
    g.add_conditional_edges(
        "reflection",
        route_fn,
        {
            "analyzer": "analyzer",
            "reporter": "reporter",
        },
    )
    g.add_edge("reporter", END)

    return g.compile()
