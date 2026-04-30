from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.models.schemas import EvidenceDocument
from app.store import get_session

router = APIRouter()

MAX_DOCUMENT_BYTES = 500_000  # 500KB
MAX_UPLOAD_BYTES = 1_000_000  # 1MB


def _sanitize_text(text: str) -> str:
    """Strip null bytes and non-printable control chars (keep \\n \\r \\t)."""
    return "".join(
        ch for ch in text
        if ch in ("\n", "\r", "\t") or (ord(ch) >= 32)
    )


class SetDocumentBody(BaseModel):
    document: str = ""
    prompt: str = ""


@router.post("/projects/{project_id}/document")
async def set_document(project_id: UUID, body: SetDocumentBody):
    """Set the document text (paste) or generation prompt for a project."""
    session = get_session(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project not found")

    if body.document and len(body.document.encode("utf-8")) > MAX_DOCUMENT_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Document exceeds maximum size of {MAX_DOCUMENT_BYTES // 1000}KB",
        )

    if body.document:
        session.document = _sanitize_text(body.document)
    if body.prompt:
        session.prompt = _sanitize_text(body.prompt)
    return {"ok": True, "has_document": bool(session.document), "has_prompt": bool(session.prompt)}


@router.post("/projects/{project_id}/upload")
async def upload_document(project_id: UUID, file: UploadFile = File(...)):
    session = get_session(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project not found")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum upload size of {MAX_UPLOAD_BYTES // 1000}KB",
        )
    session.document = _sanitize_text(
        content.decode("utf-8", errors="replace"))
    return {"ok": True, "filename": file.filename, "size": len(content)}


@router.get("/projects/{project_id}/document")
async def get_document(project_id: UUID):
    session = get_session(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"document": session.document, "prompt": session.prompt}


# ─── Evidence / Reference Materials ─────────────────────────────────


class AddEvidenceBody(BaseModel):
    label: str = ""
    content: str


@router.post("/projects/{project_id}/evidence")
async def add_evidence(project_id: UUID, body: AddEvidenceBody):
    """Add a text-based evidence / reference document."""
    session = get_session(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project not found")

    doc = EvidenceDocument(
        label=body.label or f"Evidence {len(session.evidence) + 1}", content=body.content)
    session.evidence.append(doc)
    return {"ok": True, "evidence_id": doc.id, "total": len(session.evidence)}


@router.post("/projects/{project_id}/evidence/upload")
async def upload_evidence(project_id: UUID, file: UploadFile = File(...)):
    """Upload a text file as evidence."""
    session = get_session(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project not found")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Evidence file exceeds maximum upload size of {MAX_UPLOAD_BYTES // 1000}KB",
        )
    doc = EvidenceDocument(
        label=file.filename or f"Evidence {len(session.evidence) + 1}",
        content=_sanitize_text(content.decode("utf-8", errors="replace")),
    )
    session.evidence.append(doc)
    return {"ok": True, "evidence_id": doc.id, "filename": file.filename, "total": len(session.evidence)}


@router.get("/projects/{project_id}/evidence")
async def list_evidence(project_id: UUID):
    session = get_session(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "evidence": [
            {"id": e.id, "label": e.label, "length": len(
                e.content), "uploaded_at": e.uploaded_at.isoformat()}
            for e in session.evidence
        ]
    }


@router.delete("/projects/{project_id}/evidence/{evidence_id}")
async def delete_evidence(project_id: UUID, evidence_id: str):
    session = get_session(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project not found")
    session.evidence = [e for e in session.evidence if e.id != evidence_id]
    return {"ok": True, "total": len(session.evidence)}
