"""
In-memory session store for verification pipeline state.
Holds documents, verification results, quiz data, and reports per project.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4
from typing import Any

from app.models.schemas import (
    ProjectStatus, VerificationResult, Question, ConfidenceReport,
)


class ProjectSession:
    """Holds all state for a single verification project."""

    def __init__(self, name: str, description: str = ""):
        self.id: UUID = uuid4()
        self.name = name
        self.description = description
        self.status: ProjectStatus = ProjectStatus.DRAFT
        self.created_at: datetime = datetime.utcnow()
        self.updated_at: datetime = datetime.utcnow()

        # Document
        self.document: str = ""
        self.prompt: str = ""

        # Verification
        self.verification_result: VerificationResult | None = None
        self.graph_state: dict[str, Any] = {}

        # Quiz
        self.questions: list[Question] = []

        # Report
        self.report: ConfidenceReport | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# Global in-memory store
_sessions: dict[UUID, ProjectSession] = {}


def create_session(name: str, description: str = "") -> ProjectSession:
    session = ProjectSession(name, description)
    _sessions[session.id] = session
    return session


def get_session(project_id: UUID) -> ProjectSession | None:
    return _sessions.get(project_id)


def list_sessions() -> list[ProjectSession]:
    return list(_sessions.values())
