"""Module 6.2: Review and HITL Decision API Routes."""

import json
import logging
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Response
from layer6_api.schemas import (
    ReviewRequest,
    ReviewResponse,
    HITLDecisionRequest,
    HITLDecisionResponse,
)
from layer4_orchestration.run import run_review

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/review", tags=["Review"])

# In-memory session store
_SESSIONS: dict[str, ReviewResponse] = {}
DECISIONS_LOG_PATH = Path("layer6_api/decisions.jsonl")


@router.post("", response_model=ReviewResponse)
async def review_code(req: ReviewRequest, response: Response) -> ReviewResponse:
    """Run agentic software engineering code review on Python source code."""
    if not req.code or not req.code.strip():
        raise HTTPException(status_code=400, detail="code field is empty")

    if len(req.code) > 50_000:
        raise HTTPException(
            status_code=413, detail="code exceeds 50000 char limit for this MVP"
        )

    try:
        result = run_review(req.code)
    except Exception as exc:
        logger.error(f"Error executing code review: {exc}")
        raise HTTPException(status_code=500, detail=f"Review execution failed: {str(exc)}")

    session_id = str(uuid4())
    resp = ReviewResponse(
        findings=result["findings"],
        report_markdown=result["report_markdown"],
        iteration_count=result["iteration_count"],
    )

    _SESSIONS[session_id] = resp
    response.headers["X-Session-Id"] = session_id
    return resp


@router.post("/{session_id}/decision", response_model=HITLDecisionResponse)
async def hitl_decision(session_id: str, req: HITLDecisionRequest) -> HITLDecisionResponse:
    """Record human-in-the-loop (HITL) feedback decision (accept, edit, reject)."""
    if session_id not in _SESSIONS:
        raise HTTPException(status_code=404, detail="unknown session")

    if req.decision == "edit" and (not req.edited_text or not req.edited_text.strip()):
        raise HTTPException(status_code=400, detail="edited_text required when decision='edit'")

    # Persist decision to decisions.jsonl log
    DECISIONS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    decision_record = {
        "session_id": session_id,
        "finding_index": req.finding_index,
        "decision": req.decision,
        "edited_text": req.edited_text,
    }

    try:
        with open(DECISIONS_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(decision_record) + "\n")
    except Exception as exc:
        logger.error(f"Failed to persist HITL decision: {exc}")

    return HITLDecisionResponse(
        status="recorded",
        session_id=session_id,
        finding_index=req.finding_index,
        decision=req.decision,
    )
