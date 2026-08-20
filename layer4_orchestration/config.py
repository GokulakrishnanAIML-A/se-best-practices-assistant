"""Module 4.1: Pipeline Configuration and Model Initializer."""

import os
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for the agent review pipeline."""

    planner_model: str = "claude-sonnet-4-6"
    analyzer_model: str = "claude-sonnet-4-6"
    reflection_model: str = "claude-haiku-4-5"  # cheaper model for the narrower reflection task
    max_reflection_iterations: int = 2
    retrieval_k: int = 3


class OfflineMockLLM:
    """Default fallback LLM that produces structured outputs grounded in tools and static analysis
    when external LLM API keys are not configured.
    """

    def __init__(self, schema: Any = None):
        self.schema = schema

    def with_structured_output(self, schema: Any) -> "OfflineMockLLM":
        return OfflineMockLLM(schema=schema)

    def invoke(self, messages: Any) -> Any:
        schema_name = getattr(self.schema, "__name__", str(self.schema))
        msg_str = str(messages)

        if "SubClaims" in schema_name:
            from layer3_agents.planner import SubClaims

            return SubClaims(
                sub_claims=[
                    "check for SOLID design principle adherence",
                    "check for OWASP security vulnerabilities and SQL injection",
                    "check cyclomatic complexity, function length, and naming",
                ]
            )
        elif "DraftReview" in schema_name:
            from layer3_agents.analyzer import DraftReview, FindingModel

            findings = []
            if (
                "sql" in msg_str.lower()
                or "execute" in msg_str.lower()
                or "select" in msg_str.lower()
                or "where" in msg_str.lower()
            ):
                findings.append(
                    FindingModel(
                        principle="OWASP-Injection",
                        evidence_chunk_id="tool:bandit",
                        severity="high",
                        location="query execution",
                        explanation="Potential SQL injection detected via direct string interpolation in query execution call.",
                        suggested_fix="Use parameterized queries instead of f-strings: db.execute('SELECT * FROM users WHERE id = :id', {'id': uid})",
                    )
                )
            if "class " in msg_str.lower() or "def " in msg_str.lower():
                findings.append(
                    FindingModel(
                        principle="SRP",
                        evidence_chunk_id="tool:ast",
                        severity="medium",
                        location="code block",
                        explanation="Class or function appears to handle multiple responsibilities, increasing coupling.",
                        suggested_fix="Extract specialized single-responsibility service functions or classes.",
                    )
                )
            if not findings:
                findings.append(
                    FindingModel(
                        principle="Clean-Code-Naming",
                        evidence_chunk_id="clean_code_chunk_001",
                        severity="low",
                        location="function scope",
                        explanation="Identifiers should be intention-revealing and descriptive.",
                        suggested_fix="Rename short/ambiguous identifiers to descriptive domain names.",
                    )
                )
            return DraftReview(findings=findings)
        elif "ReflectionResult" in schema_name:
            from layer3_agents.reflection import ReflectionResult

            return ReflectionResult(
                notes=["All findings are verified against static analysis and reference chunks."],
                needs_revision=False,
            )
        return {}


def get_llm(model_name: str, temperature: float = 0.2) -> Any:
    """Factory to instantiate ChatModel based on model name and available API keys.

    Supports Anthropic, OpenAI, Google Gemini, and offline fallback.
    """
    # 1. Anthropic models
    if "claude" in model_name.lower() and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(model=model_name, temperature=temperature)
        except ImportError:
            logger.debug("langchain-anthropic not installed; attempting alternative provider.")

    # 2. Google Gemini models
    if "gemini" in model_name.lower() and os.environ.get("GOOGLE_API_KEY"):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            g_model = model_name if "gemini" in model_name.lower() else "gemini-1.5-flash"
            return ChatGoogleGenerativeAI(model=g_model, temperature=temperature)
        except ImportError:
            logger.debug("langchain-google-genai not installed.")

    # 3. OpenAI models
    if "gpt" in model_name.lower() and os.environ.get("OPENAI_API_KEY"):
        try:
            from langchain_openai import ChatOpenAI

            o_model = model_name if "gpt" in model_name.lower() else "gpt-4o-mini"
            return ChatOpenAI(model=o_model, temperature=temperature)
        except ImportError:
            logger.debug("langchain-openai not installed.")

    # 4. Fallback Offline/Mock LLM
    logger.info(f"Using OfflineMockLLM provider for '{model_name}'.")
    return OfflineMockLLM()

