from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    VERIFYING = "verifying"
    QUIZ = "quiz"
    COMPLETE = "complete"


class FactCategory(str, Enum):
    FACTUAL_CLAIM = "factual_claim"
    STATISTIC = "statistic"
    CITATION = "citation"
    DEFINITION = "definition"
    OPINION = "opinion"
    TEMPORAL = "temporal"


class FactStatus(str, Enum):
    VERIFIED = "verified"
    UNCERTAIN = "uncertain"
    HALLUCINATED = "hallucinated"
    UNVERIFIABLE = "unverifiable"


class IssueSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class IssueType(str, Enum):
    CONTRADICTION = "contradiction"
    AMBIGUITY = "ambiguity"
    UNSUPPORTED_INFERENCE = "unsupported_inference"
    TEMPORAL_INCONSISTENCY = "temporal_inconsistency"


class QuestionType(str, Enum):
    RECALL = "recall"
    ANALYSIS = "analysis"
    APPLICATION = "application"
    TRAP = "trap"
    SCENARIO = "scenario"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


# ─── Request / Response Models ───────────────────────────────────────


class ProjectCreate(BaseModel):
    name: str
    description: str = ""


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime


class DocumentCreate(BaseModel):
    content: str
    format: str = "markdown"


class DocumentGenerateRequest(BaseModel):
    prompt: str
    style: str = "professional"
    document_type: str = "report"
    additional_context: str = ""


class AtomicFact(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    text: str
    category: FactCategory
    position_start: int
    position_end: int
    section: str = ""


class Evidence(BaseModel):
    source: str
    text: str
    url: str = ""
    relevance: float = 1.0


class FactVerification(BaseModel):
    fact: AtomicFact
    status: FactStatus
    confidence: float
    evidence: list[Evidence] = []
    method: str = ""
    explanation: str = ""


class ConsistencyIssue(BaseModel):
    type: IssueType
    facts_involved: list[str]
    explanation: str
    severity: IssueSeverity


class SelfCritique(BaseModel):
    reflection: str
    completeness_score: float
    rigor_score: float
    missed_checks: list[str]
    corrections: list[str]


class VerificationResult(BaseModel):
    facts: list[FactVerification] = []
    consistency_issues: list[ConsistencyIssue] = []
    self_critique: SelfCritique | None = None
    revised_document: str = ""
    scores: dict = {}


class Question(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    text: str
    type: QuestionType
    related_facts: list[str] = []
    options: list[str] | None = None
    correct_answer: str = ""
    explanation: str = ""
    difficulty: Difficulty = Difficulty.MEDIUM


class QuizSubmission(BaseModel):
    answers: dict[str, str]  # question_id -> user answer


class QuizResult(BaseModel):
    question_id: str
    correct: bool
    user_answer: str
    correct_answer: str
    explanation: str
    score: float


class ConfidenceReport(BaseModel):
    factuality_score: float
    consistency_score: float
    source_grounding_score: float
    comprehension_score: float
    overall_confidence: float
    risk_areas: list[dict] = []
    recommendations: list[str] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)
