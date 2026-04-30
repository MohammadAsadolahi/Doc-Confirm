from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.models.schemas import QuizSubmission, ProjectStatus
from app.store import get_session
from app.services.llm import get_llm

router = APIRouter()


@router.get("/projects/{project_id}/quiz")
async def get_quiz(project_id: UUID):
    """Get the generated quiz questions for a project."""
    session = get_session(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project not found")
    if not session.questions:
        raise HTTPException(
            status_code=400, detail="Quiz not generated yet. Run verification first.")

    # Return questions without correct answers (user shouldn't see them before answering)
    questions_safe = []
    for q in session.questions:
        questions_safe.append({
            "id": q.id,
            "text": q.text,
            "type": q.type.value,
            "difficulty": q.difficulty.value,
            "options": q.options,
        })
    return {"project_id": str(project_id), "questions": questions_safe}


@router.post("/projects/{project_id}/quiz/submit")
async def submit_quiz(project_id: UUID, body: QuizSubmission):
    """Submit answers and get scored results."""
    session = get_session(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project not found")
    if not session.questions:
        raise HTTPException(status_code=400, detail="No quiz to submit")

    results = []
    correct_count = 0
    for q in session.questions:
        user_answer = body.answers.get(q.id, "")
        is_correct = user_answer.strip().lower() == q.correct_answer.strip().lower()
        if is_correct:
            correct_count += 1
        results.append({
            "question_id": q.id,
            "correct": is_correct,
            "user_answer": user_answer,
            "correct_answer": q.correct_answer,
            "explanation": q.explanation,
            "score": 1.0 if is_correct else 0.0,
        })

    total = max(len(session.questions), 1)
    score = correct_count / total

    # Update report with comprehension score
    if session.report:
        session.report.comprehension_score = score
        session.report.overall_confidence = (
            session.report.factuality_score * 0.35
            + session.report.consistency_score * 0.25
            + session.report.source_grounding_score * 0.2
            + score * 0.2
        )
    session.status = ProjectStatus.COMPLETE

    return {
        "project_id": str(project_id),
        "score": score,
        "total": total,
        "correct": correct_count,
        "results": results,
    }
