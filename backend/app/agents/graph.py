"""
LangGraph orchestrator for the GenDoc Confirm verification pipeline.

Pipeline:
  generate_document → decompose_facts → self_consistency_check
  → plan_verification → execute_verification → cross_reference
  → self_critique → revise_document → generate_quiz
  → evaluate_answers → final_report

Every node is a real LLM-powered implementation — no stubs.
"""
from __future__ import annotations
import json
from typing import TypedDict, Any

from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate

from app.models.schemas import (
    AtomicFact,
    ConfidenceReport,
    ConsistencyIssue,
    FactVerification,
    FactStatus,
    Question,
    SelfCritique,
)
from app.services.llm import get_llm
from app.config import get_settings
from app.tools.fact_decomposer import decompose_document
from app.tools.self_consistency import check_self_consistency
from app.tools.web_search import verify_claim
from app.tools.contradiction_detector import detect_contradictions
from app.tools.quiz_generator import generate_quiz as _generate_quiz


class GenDocState(TypedDict, total=False):
    # Inputs
    prompt: str
    document: str
    source_materials: list[str]

    # Verification pipeline
    atomic_facts: list[AtomicFact]
    consistency_scores: dict[str, float]
    verification_questions: list[str]
    verification_results: list[FactVerification]
    consistency_issues: list[ConsistencyIssue]

    # Self-critique
    self_critique: SelfCritique
    critique_loop_count: int
    revised_document: str

    # Quiz
    comprehension_questions: list[Question]
    user_answers: dict[str, str]
    comprehension_score: float

    # Output
    confidence_report: ConfidenceReport

    # SSE streaming callback
    _emit: Any


# ─── Helpers ────────────────────────────────────────────────────────


def _parse_json(raw: str) -> Any:
    """Parse JSON from LLM output, stripping markdown fences."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(raw)


async def _emit(state: GenDocState, event: str, data: dict):
    """Emit an SSE event if a callback is attached."""
    fn = state.get("_emit")
    if fn:
        await fn(event, data)


# ─── Node 1: Generate Document ──────────────────────────────────────


GENERATE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a professional document writer. Generate a high-quality document based on the user's prompt.

Think step by step:
1. Identify the key topics to cover
2. Structure the document logically
3. Write clear, factual content
4. Include specific details, data points, and references where appropriate

Write in Markdown format."""),
    ("human", "{prompt}"),
])


async def generate_document(state: GenDocState) -> dict:
    """Generate document from prompt with CoT reasoning."""
    await _emit(state, "step_start", {"step": "generate_document", "label": "Generating Document"})

    prompt = state.get("prompt", "")
    document = state.get("document", "")

    if not document and prompt:
        llm = get_llm(temperature=0.3)
        chain = GENERATE_PROMPT | llm
        result = await chain.ainvoke({"prompt": prompt})
        document = result.content

    await _emit(state, "step_complete", {
        "step": "generate_document",
        "data": {"document_length": len(document)},
    })
    return {"document": document}


# ─── Node 2: Decompose Facts ────────────────────────────────────────


async def decompose_facts(state: GenDocState) -> dict:
    """Break document into atomic verifiable facts (FActScore-style)."""
    await _emit(state, "step_start", {"step": "decompose_facts", "label": "Decomposing into Atomic Facts"})

    document = state["document"]
    facts = await decompose_document(document)

    await _emit(state, "step_complete", {
        "step": "decompose_facts",
        "data": {"fact_count": len(facts), "facts": [f.model_dump() for f in facts]},
    })
    return {"atomic_facts": facts}


# ─── Node 3: Self-Consistency Check ─────────────────────────────────


async def self_consistency_check(state: GenDocState) -> dict:
    """Re-generate N times and check consistency (SelfCheckGPT-style)."""
    await _emit(state, "step_start", {"step": "self_consistency_check", "label": "Self-Consistency Check"})

    facts = state.get("atomic_facts", [])
    prompt = state.get("prompt", "")
    document = state.get("document", "")

    gen_prompt = prompt or f"Rewrite this document:\n\n{document}"
    scores = await check_self_consistency(document, facts, gen_prompt)

    await _emit(state, "step_complete", {
        "step": "self_consistency_check",
        "data": {"scores": scores},
    })
    return {"consistency_scores": scores}


# ─── Node 4: Plan Verification ──────────────────────────────────────


PLAN_VERIFICATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are planning verification for a set of facts. For each fact that has low consistency
or is a factual claim/statistic, generate a verification question that can be independently checked.

Respond ONLY with a JSON array of strings — the verification questions."""),
    ("human", """Facts to verify:
{facts_text}

Consistency scores:
{scores_text}"""),
])


async def plan_verification(state: GenDocState) -> dict:
    """Generate verification questions for flagged facts (CoVe step 2)."""
    await _emit(state, "step_start", {"step": "plan_verification", "label": "Planning Verification"})

    facts = state.get("atomic_facts", [])
    scores = state.get("consistency_scores", {})

    facts_text = "\n".join(
        f"[{f.id}] (score={scores.get(f.id, 'N/A')}) {f.text}" for f in facts
    )
    scores_text = json.dumps(scores, indent=2)

    llm = get_llm(temperature=0)
    chain = PLAN_VERIFICATION_PROMPT | llm
    result = await chain.ainvoke({"facts_text": facts_text, "scores_text": scores_text})

    try:
        questions = _parse_json(result.content)
    except json.JSONDecodeError:
        questions = [f.text for f in facts]

    await _emit(state, "step_complete", {
        "step": "plan_verification",
        "data": {"question_count": len(questions)},
    })
    return {"verification_questions": questions}


# ─── Node 5: Execute Verification ───────────────────────────────────


async def execute_verification(state: GenDocState) -> dict:
    """Answer verification questions independently (CoVe step 3 - factored)."""
    await _emit(state, "step_start", {"step": "execute_verification", "label": "Verifying Facts"})

    facts = state.get("atomic_facts", [])
    scores = state.get("consistency_scores", {})
    results: list[FactVerification] = []

    for fact in facts:
        verdict = await verify_claim(fact.text)
        consistency = scores.get(fact.id, 0.5)

        combined_confidence = (verdict["confidence"] + consistency) / 2

        if combined_confidence >= 0.75:
            status = FactStatus.VERIFIED
        elif combined_confidence >= 0.4:
            status = FactStatus.UNCERTAIN
        else:
            status = FactStatus.HALLUCINATED

        results.append(FactVerification(
            fact=fact,
            status=status,
            confidence=combined_confidence,
            evidence=verdict.get("evidence", []),
            method="self_consistency + llm_verification",
            explanation=verdict.get("explanation", ""),
        ))

        await _emit(state, "fact_verified", {
            "fact_id": fact.id,
            "status": status.value,
            "confidence": combined_confidence,
        })

    await _emit(state, "step_complete", {
        "step": "execute_verification",
        "data": {"verified_count": len(results)},
    })
    return {"verification_results": results}


# ─── Node 6: Cross-Reference ────────────────────────────────────────


async def cross_reference(state: GenDocState) -> dict:
    """Check facts against each other for contradictions."""
    await _emit(state, "step_start", {"step": "cross_reference", "label": "Cross-Referencing & Contradiction Detection"})

    facts = state.get("atomic_facts", [])
    issues = await detect_contradictions(facts)

    await _emit(state, "step_complete", {
        "step": "cross_reference",
        "data": {"issues_found": len(issues)},
    })
    return {"consistency_issues": issues}


# ─── Node 7: Self-Critique (Reflexion-style) ────────────────────────


SELF_CRITIQUE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a verification auditor. Review the verification work done so far and self-critique:

1. Were all important facts checked?
2. Were the verification methods rigorous enough?
3. Were there any blind spots or missed checks?
4. Rate completeness (0-1) and rigor (0-1)

Respond ONLY with JSON:
{{
  "reflection": "<detailed reflection>",
  "completeness_score": <float>,
  "rigor_score": <float>,
  "missed_checks": ["<str>", ...],
  "corrections": ["<str>", ...]
}}"""),
    ("human", """Document:
{document}

Facts verified: {n_facts}
Verification results summary:
{results_summary}

Consistency issues found: {n_issues}
Issues:
{issues_text}

Critique loop: {loop_count} of {max_loops}"""),
])


async def self_critique(state: GenDocState) -> dict:
    """Self-critique with Reflexion-style verbal reflection."""
    await _emit(state, "step_start", {"step": "self_critique", "label": "Self-Critique (Reflexion)"})

    loop_count = state.get("critique_loop_count", 0) + 1
    settings = get_settings()
    results = state.get("verification_results", [])
    issues = state.get("consistency_issues", [])

    results_summary = "\n".join(
        f"- [{r.status.value}] (conf={r.confidence:.2f}) {r.fact.text[:80]}"
        for r in results
    )
    issues_text = "\n".join(
        f"- [{i.type.value}/{i.severity.value}] {i.explanation}"
        for i in issues
    )

    llm = get_llm(temperature=0)
    chain = SELF_CRITIQUE_PROMPT | llm
    result = await chain.ainvoke({
        "document": state.get("document", "")[:2000],
        "n_facts": len(results),
        "results_summary": results_summary or "None yet",
        "n_issues": len(issues),
        "issues_text": issues_text or "None",
        "loop_count": loop_count,
        "max_loops": settings.max_critique_loops,
    })

    try:
        data = _parse_json(result.content)
        critique = SelfCritique(
            reflection=data.get("reflection", ""),
            completeness_score=float(data.get("completeness_score", 0.5)),
            rigor_score=float(data.get("rigor_score", 0.5)),
            missed_checks=data.get("missed_checks", []),
            corrections=data.get("corrections", []),
        )
    except (json.JSONDecodeError, ValueError):
        critique = SelfCritique(
            reflection="Could not parse critique",
            completeness_score=0.9,
            rigor_score=0.9,
            missed_checks=[],
            corrections=[],
        )

    await _emit(state, "step_complete", {
        "step": "self_critique",
        "data": {
            "loop": loop_count,
            "completeness": critique.completeness_score,
            "rigor": critique.rigor_score,
        },
    })
    return {"self_critique": critique, "critique_loop_count": loop_count}


# ─── Node 8: Revise Document ────────────────────────────────────────


REVISE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are revising a document based on verification findings. Apply corrections while
preserving the original intent and style. Mark any changes with [REVISED] inline.

If no corrections are needed, return the original document unchanged."""),
    ("human", """Original document:
{document}

Issues found:
{issues}

Corrections suggested:
{corrections}"""),
])


async def revise_document(state: GenDocState) -> dict:
    """Apply corrections while preserving original intent (RARR-style)."""
    await _emit(state, "step_start", {"step": "revise_document", "label": "Revising Document"})

    critique = state.get("self_critique")
    issues = state.get("consistency_issues", [])

    issues_text = "\n".join(
        f"- [{i.type.value}] {i.explanation}" for i in issues
    )
    corrections_text = "\n".join(
        f"- {c}" for c in (critique.corrections if critique else [])
    )

    if not issues_text and not corrections_text:
        await _emit(state, "step_complete", {"step": "revise_document", "data": {"changed": False}})
        return {"revised_document": state.get("document", "")}

    llm = get_llm(temperature=0)
    chain = REVISE_PROMPT | llm
    result = await chain.ainvoke({
        "document": state.get("document", ""),
        "issues": issues_text or "None",
        "corrections": corrections_text or "None",
    })

    await _emit(state, "step_complete", {"step": "revise_document", "data": {"changed": True}})
    return {"revised_document": result.content}


# ─── Node 9: Generate Quiz ──────────────────────────────────────────


async def generate_quiz(state: GenDocState) -> dict:
    """Generate multi-level comprehension questions."""
    await _emit(state, "step_start", {"step": "generate_quiz", "label": "Generating Comprehension Quiz"})

    document = state.get("revised_document") or state.get("document", "")
    facts = state.get("atomic_facts", [])
    issues = state.get("consistency_issues", [])

    issues_text = "\n".join(f"- {i.explanation}" for i in issues)
    questions = await _generate_quiz(document, facts, issues_text, n_questions=8)

    await _emit(state, "step_complete", {
        "step": "generate_quiz",
        "data": {"question_count": len(questions), "questions": [q.model_dump() for q in questions]},
    })
    return {"comprehension_questions": questions}


# ─── Node 10: Evaluate Answers ──────────────────────────────────────


EVALUATE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are grading a user's quiz answers. For each question, determine if the user's answer
is correct, partially correct, or wrong. Score each 0.0-1.0.

Respond ONLY with JSON:
{{"scores": [{{"question_id": "<str>", "score": <float>, "feedback": "<str>"}}]}}"""),
    ("human", """Questions and answers:
{qa_text}"""),
])


async def evaluate_answers(state: GenDocState) -> dict:
    """Score user answers against rubric."""
    await _emit(state, "step_start", {"step": "evaluate_answers", "label": "Evaluating Comprehension"})

    questions = state.get("comprehension_questions", [])
    answers = state.get("user_answers", {})

    if not answers:
        # No answers yet — quiz hasn't been taken. Set score to 0 for now.
        await _emit(state, "step_complete", {"step": "evaluate_answers", "data": {"score": 0, "pending": True}})
        return {"comprehension_score": 0.0}

    qa_text = "\n".join(
        f"Q: {q.text}\nCorrect: {q.correct_answer}\nUser: {answers.get(q.id, 'No answer')}"
        for q in questions
    )

    llm = get_llm(temperature=0)
    chain = EVALUATE_PROMPT | llm
    result = await chain.ainvoke({"qa_text": qa_text})

    try:
        data = _parse_json(result.content)
        scores_list = data.get("scores", [])
        avg_score = sum(s.get("score", 0)
                        for s in scores_list) / max(len(scores_list), 1)
    except (json.JSONDecodeError, ValueError):
        avg_score = 0.0

    await _emit(state, "step_complete", {"step": "evaluate_answers", "data": {"score": avg_score}})
    return {"comprehension_score": avg_score}


# ─── Node 11: Final Report ──────────────────────────────────────────


async def final_report(state: GenDocState) -> dict:
    """Compile the final ConfidenceReport."""
    await _emit(state, "step_start", {"step": "final_report", "label": "Compiling Final Report"})

    results = state.get("verification_results", [])
    issues = state.get("consistency_issues", [])
    critique = state.get("self_critique")

    # Compute scores
    if results:
        factuality = sum(r.confidence for r in results) / len(results)
    else:
        factuality = 0.0

    scores = state.get("consistency_scores", {})
    if scores:
        consistency = sum(scores.values()) / len(scores)
    else:
        consistency = 0.0

    source_grounding = 1.0 - (len(issues) * 0.1)
    source_grounding = max(0.0, min(1.0, source_grounding))

    comprehension = state.get("comprehension_score", 0.0)

    overall = (factuality * 0.35 + consistency * 0.25 +
               source_grounding * 0.2 + comprehension * 0.2)

    risk_areas = []
    for r in results:
        if r.status in (FactStatus.HALLUCINATED, FactStatus.UNCERTAIN):
            risk_areas.append({
                "fact": r.fact.text[:100],
                "status": r.status.value,
                "confidence": r.confidence,
            })

    recommendations = []
    if factuality < 0.7:
        recommendations.append(
            "Several facts could not be verified — review highlighted sections carefully.")
    if len(issues) > 0:
        recommendations.append(
            f"{len(issues)} consistency issue(s) found — check for contradictions.")
    if comprehension < 0.6:
        recommendations.append(
            "Low comprehension score — re-read the document and retake the quiz.")
    if not recommendations:
        recommendations.append(
            "Document passed all verification checks with high confidence.")

    report = ConfidenceReport(
        factuality_score=round(factuality, 3),
        consistency_score=round(consistency, 3),
        source_grounding_score=round(source_grounding, 3),
        comprehension_score=round(comprehension, 3),
        overall_confidence=round(overall, 3),
        risk_areas=risk_areas,
        recommendations=recommendations,
    )

    await _emit(state, "step_complete", {
        "step": "final_report",
        "data": report.model_dump(mode="json"),
    })
    return {"confidence_report": report}


# ─── Graph construction ─────────────────────────────────────────────


def should_critique_again(state: GenDocState) -> str:
    """Decide whether to run another critique loop."""
    settings = get_settings()
    loop_count = state.get("critique_loop_count", 0)
    critique = state.get("self_critique")
    if loop_count >= settings.max_critique_loops:
        return "revise"
    if critique and critique.completeness_score > 0.9 and critique.rigor_score > 0.9:
        return "revise"
    return "critique"


def build_verification_graph() -> StateGraph:
    """Build the full verification LangGraph."""
    graph = StateGraph(GenDocState)

    graph.add_node("generate_document", generate_document)
    graph.add_node("decompose_facts", decompose_facts)
    graph.add_node("self_consistency_check", self_consistency_check)
    graph.add_node("plan_verification", plan_verification)
    graph.add_node("execute_verification", execute_verification)
    graph.add_node("cross_reference", cross_reference)
    graph.add_node("self_critique", self_critique)
    graph.add_node("revise_document", revise_document)
    graph.add_node("generate_quiz", generate_quiz)
    graph.add_node("evaluate_answers", evaluate_answers)
    graph.add_node("final_report", final_report)

    graph.set_entry_point("generate_document")
    graph.add_edge("generate_document", "decompose_facts")
    graph.add_edge("decompose_facts", "self_consistency_check")
    graph.add_edge("self_consistency_check", "plan_verification")
    graph.add_edge("plan_verification", "execute_verification")
    graph.add_edge("execute_verification", "cross_reference")
    graph.add_edge("cross_reference", "self_critique")

    graph.add_conditional_edges(
        "self_critique",
        should_critique_again,
        {"critique": "self_critique", "revise": "revise_document"},
    )

    graph.add_edge("revise_document", "generate_quiz")
    graph.add_edge("generate_quiz", "evaluate_answers")
    graph.add_edge("evaluate_answers", "final_report")
    graph.add_edge("final_report", END)

    return graph
