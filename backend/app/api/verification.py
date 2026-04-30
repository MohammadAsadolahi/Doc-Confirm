from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import ProjectStatus, VerificationResult
from app.store import get_session
from app.agents.graph import build_verification_graph

logger = logging.getLogger(__name__)
router = APIRouter()


async def _run_verification(project_id: UUID):
    """SSE generator that runs the real LangGraph pipeline and streams events."""
    session = get_session(project_id)
    if not session:
        yield {"event": "error", "data": json.dumps({"error": "Project not found"})}
        return

    session.status = ProjectStatus.VERIFYING

    # Event queue for SSE streaming
    queue: asyncio.Queue = asyncio.Queue()

    async def emit(event: str, data: dict):
        await queue.put({"event": event, "data": json.dumps(data, default=str)})

    # Build and compile graph
    graph = build_verification_graph()
    compiled = graph.compile()

    initial_state = {
        "prompt": session.prompt,
        "document": session.document,
        "_emit": emit,
    }

    # Run graph in background task
    async def run_graph():
        try:
            final_state = await compiled.ainvoke(initial_state)
            # Store results in session
            session.graph_state = {
                k: v for k, v in final_state.items() if k != "_emit"
            }
            session.verification_result = VerificationResult(
                facts=[r for r in final_state.get("verification_results", [])],
                consistency_issues=final_state.get("consistency_issues", []),
                self_critique=final_state.get("self_critique"),
                revised_document=final_state.get("revised_document", ""),
                scores={
                    "factuality": final_state.get("confidence_report", {}).factuality_score
                    if final_state.get("confidence_report") else 0,
                    "consistency": final_state.get("confidence_report", {}).consistency_score
                    if final_state.get("confidence_report") else 0,
                },
            )
            session.questions = final_state.get("comprehension_questions", [])
            logger.info("Quiz questions generated: %d", len(session.questions))
            session.report = final_state.get("confidence_report")
            if session.document == "" and final_state.get("document"):
                session.document = final_state["document"]
            if final_state.get("revised_document"):
                session.document = final_state["revised_document"]
            session.status = ProjectStatus.QUIZ
            await emit("verification_complete", {"message": "Verification complete"})
        except Exception as e:
            await emit("error", {"error": str(e)})
        finally:
            await queue.put(None)  # Signal end

    task = asyncio.create_task(run_graph())

    # Yield events from queue
    while True:
        item = await queue.get()
        if item is None:
            break
        yield item

    await task


@router.post("/projects/{project_id}/verify")
async def start_verification(project_id: UUID):
    session = get_session(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project not found")
    if not session.document and not session.prompt:
        raise HTTPException(
            status_code=400, detail="No document or prompt set")
    return EventSourceResponse(_run_verification(project_id))


@router.get("/projects/{project_id}/verify/results")
async def get_verification_results(project_id: UUID):
    session = get_session(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project not found")
    if not session.verification_result:
        return {"status": "pending"}
    return session.verification_result.model_dump(mode="json")
