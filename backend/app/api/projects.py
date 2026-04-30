from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.models.schemas import ProjectCreate, ProjectResponse
from app.store import create_session, get_session, list_sessions

router = APIRouter()


@router.post("/", response_model=ProjectResponse)
async def create_project(body: ProjectCreate):
    session = create_session(body.name, body.description)
    return ProjectResponse(**session.to_dict())


@router.get("/", response_model=list[ProjectResponse])
async def list_projects():
    return [ProjectResponse(**s.to_dict()) for s in list_sessions()]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: UUID):
    session = get_session(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(**session.to_dict())
