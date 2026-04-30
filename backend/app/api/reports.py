from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.store import get_session

router = APIRouter()


@router.get("/projects/{project_id}/report")
async def get_report(project_id: UUID):
    session = get_session(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project not found")
    if not session.report:
        return {"status": "pending"}

    return {
        "report": session.report.model_dump(mode="json"),
        "document": session.document,
        "verification": session.verification_result.model_dump(mode="json") if session.verification_result else None,
    }
