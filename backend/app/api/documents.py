from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.store import get_session

router = APIRouter()


class SetDocumentBody(BaseModel):
    document: str = ""
    prompt: str = ""


@router.post("/projects/{project_id}/document")
async def set_document(project_id: UUID, body: SetDocumentBody):
    """Set the document text (paste) or generation prompt for a project."""
    session = get_session(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project not found")

    if body.document:
        session.document = body.document
    if body.prompt:
        session.prompt = body.prompt
    return {"ok": True, "has_document": bool(session.document), "has_prompt": bool(session.prompt)}


@router.post("/projects/{project_id}/upload")
async def upload_document(project_id: UUID, file: UploadFile = File(...)):
    session = get_session(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project not found")

    content = await file.read()
    session.document = content.decode("utf-8", errors="replace")
    return {"ok": True, "filename": file.filename, "size": len(content)}


@router.get("/projects/{project_id}/document")
async def get_document(project_id: UUID):
    session = get_session(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"document": session.document, "prompt": session.prompt}
