"""
LangGraph orchestrator for the GenDoc Confirm verification pipeline.

Optimized pipeline (reduced LLM calls while preserving quality):
  generate_document → decompose_facts → evidence_grounding (BATCHED, 1 call)
  → execute_verification (1 call per fact) → cross_examination (SELECTIVE, only low-confidence)
  → cross_reference_and_revise → generate_quiz → evaluate_answers → final_report

Optimizations applied (backed by research):
  - Removed self_consistency_check: subsumed by multi-perspective verification (Huang et al., ICLR 2024)
  - Removed plan_verification: atomic facts ARE the verification targets (SAFE pattern)
  - Removed self_critique loop: redundant with cross-examination, can degrade quality (Huang et al.)
  - Batched evidence grounding: RAGAS NLIStatementPrompt pattern (N calls → 1 call)
  - Unified multi-perspective verification: 3 perspectives in 1 call (Self-Contrast, SPP research)
  - Optimized cross-examination: 5 calls → 2 calls per fact (CoVe Factored Lite)
  - Selective cross-examination: only facts with confidence < 0.6
  - Merged cross_reference + revise into single step

Call count: ~98 → ~18 for 10 facts (82% reduction)
"""
from __future__ import annotations
import asyncio
import json
import logging
from typing import TypedDict, Any

from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate

from app.models.schemas import (
    AtomicFact,
    ConfidenceReport,
    ConsistencyIssue,
    EvidenceDocument,
    FactVerification,
    FactStatus,
    Question,
)
from app.services.llm import get_llm
from app.tools.fact_decomposer import decompose_document
from app.tools.web_search import verify_claim
from app.tools.contradiction_detector import detect_contradictions
from app.tools.cross_examiner import cross_examine_fact
from app.tools.evidence_checker import check_evidence_grounding
from app.tools.quiz_generator import generate_quiz as _generate_quiz

logger = logging.getLogger(__name__)


class GenDocState(TypedDict, total=False):
    # Inputs
    prompt: str
    document: str
    source_materials: list[str]
    evidence_documents: list[EvidenceDocument]  # user-provided references

    # Verification pipeline
    atomic_facts: list[AtomicFact]
    evidence_grounding_results: dict[str, dict]  # fact_id -> grounding result
    verification_results: list[FactVerification]
    cross_examination_results: dict[str, dict]  # fact_id -> exam result
    consistency_issues: list[ConsistencyIssue]

    # Revision
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


# ─── Node 3: Evidence Grounding (BATCHED, 1 LLM call) ───────────────


async def evidence_grounding(state: GenDocState) -> dict:
    """Check facts against user-provided evidence/reference materials in a single batched call."""
    evidence_docs = state.get("evidence_documents", [])
    facts = state.get("atomic_facts", [])

    if not evidence_docs:
        await _emit(state, "step_start", {"step": "evidence_grounding", "label": "Evidence Grounding (skipped — no evidence provided)"})
        await _emit(state, "step_complete", {
            "step": "evidence_grounding",
            "data": {"skipped": True, "reason": "no evidence provided"},
        })
        return {"evidence_grounding_results": {}}

    await _emit(state, "step_start", {
        "step": "evidence_grounding",
        "label": f"Grounding Facts Against {len(evidence_docs)} Evidence Document(s)",
    })

    results = await check_evidence_grounding(facts, evidence_docs)

    supported = sum(1 for r in results.values()
                    if r["grounding"] == "SUPPORTED")
    contradicted = sum(1 for r in results.values()
                       if r["grounding"] == "CONTRADICTED")

    await _emit(state, "step_complete", {
        "step": "evidence_grounding",
        "data": {
            "total": len(results),
            "supported": supported,
            "contradicted": contradicted,
            "partial": sum(1 for r in results.values() if r["grounding"] == "PARTIAL"),
            "not_found": sum(1 for r in results.values() if r["grounding"] == "NOT_FOUND"),
        },
    })
    return {"evidence_grounding_results": results}


# ─── Node 4: Execute Verification (1 call per fact, unified multi-perspective) ───


async def _verify_single_fact(fact: AtomicFact, evidence_result: dict | None, emit_fn) -> FactVerification:
    """Verify a single fact with unified multi-perspective verification + evidence grounding."""
    verdict = await verify_claim(fact.text, category=fact.category)

    combined_confidence = verdict["confidence"]

    # Integrate evidence grounding if available (evidence is PRIMARY signal)
    if evidence_result:
        grounding = evidence_result.get("grounding", "NOT_FOUND")
        ev_confidence = evidence_result.get("confidence", 0.5)
        if grounding == "SUPPORTED":
            # Evidence confirms — boost confidence significantly
            combined_confidence = 0.4 * combined_confidence + 0.6 * ev_confidence
        elif grounding == "CONTRADICTED":
            # Evidence contradicts — penalize heavily
            combined_confidence = 0.3 * combined_confidence + \
                0.7 * (1.0 - ev_confidence)
        elif grounding == "PARTIAL":
            # Partial match — slight adjustment
            combined_confidence = 0.6 * combined_confidence + 0.4 * ev_confidence

    if combined_confidence >= 0.75:
        status = FactStatus.VERIFIED
    elif combined_confidence >= 0.4:
        status = FactStatus.UNCERTAIN
    else:
        status = FactStatus.HALLUCINATED

    method = "multi_perspective"
    if evidence_result and evidence_result.get("grounding") != "NOT_FOUND":
        method += " + evidence_grounding"

    explanation = verdict.get("explanation", "")
    if evidence_result and evidence_result.get("grounding") != "NOT_FOUND":
        explanation += f" | Evidence: [{evidence_result['grounding']}] {evidence_result.get('explanation', '')}"

    result = FactVerification(
        fact=fact,
        status=status,
        confidence=combined_confidence,
        evidence=verdict.get("evidence", []),
        method=method,
        explanation=explanation,
    )

    if emit_fn:
        await emit_fn("fact_verified", {
            "fact_id": fact.id,
            "status": status.value,
            "confidence": combined_confidence,
        })

    return result


async def execute_verification(state: GenDocState) -> dict:
    """Verify all facts IN PARALLEL with unified multi-perspective verification (1 call per fact)."""
    await _emit(state, "step_start", {"step": "execute_verification", "label": "Verifying Facts (Multi-Perspective)"})

    facts = state.get("atomic_facts", [])
    ev_results = state.get("evidence_grounding_results", {})
    emit_fn = state.get("_emit")

    logger.info(
        "Verifying %d facts in parallel (1 unified call each)", len(facts))

    tasks = [
        _verify_single_fact(fact, ev_results.get(fact.id), emit_fn)
        for fact in facts
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    results: list[FactVerification] = []
    for r in raw_results:
        if isinstance(r, FactVerification):
            results.append(r)
        elif isinstance(r, Exception):
            logger.error("Fact verification failed: %s", r)

    logger.info("Verified %d/%d facts successfully", len(results), len(facts))

    await _emit(state, "step_complete", {
        "step": "execute_verification",
        "data": {"verified_count": len(results)},
    })
    return {"verification_results": results}


# ─── Node 5: Cross-Examination (SELECTIVE — only low-confidence facts) ───


async def cross_examination(state: GenDocState) -> dict:
    """Cross-examine only LOW-confidence facts (< 0.6) with 2-call CoVe Factored Lite."""
    await _emit(state, "step_start", {"step": "cross_examination", "label": "Cross-Examining Low-Confidence Facts"})

    results = state.get("verification_results", [])
    # Only cross-examine facts with confidence < 0.6 (more selective threshold)
    uncertain_facts = [r for r in results if r.confidence < 0.6]

    if not uncertain_facts:
        logger.info("No low-confidence facts to cross-examine")
        await _emit(state, "step_complete", {
            "step": "cross_examination",
            "data": {"examined_count": 0},
        })
        return {"cross_examination_results": {}}

    logger.info("Cross-examining %d low-confidence facts in parallel",
                len(uncertain_facts))

    tasks = [
        cross_examine_fact(r.fact.text)
        for r in uncertain_facts
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    exam_results: dict[str, dict] = {}
    updated_verifications = list(results)

    for r_verification, exam_result in zip(uncertain_facts, raw_results):
        if isinstance(exam_result, dict):
            fact_id = r_verification.fact.id
            exam_results[fact_id] = exam_result

            adjustment = exam_result.get("confidence_adjustment", 0)
            new_confidence = max(
                0.0, min(1.0, r_verification.confidence + adjustment))

            for i, v in enumerate(updated_verifications):
                if v.fact.id == fact_id:
                    if new_confidence >= 0.75:
                        new_status = FactStatus.VERIFIED
                    elif new_confidence >= 0.4:
                        new_status = FactStatus.UNCERTAIN
                    else:
                        new_status = FactStatus.HALLUCINATED

                    updated_verifications[i] = FactVerification(
                        fact=v.fact,
                        status=new_status,
                        confidence=new_confidence,
                        evidence=v.evidence,
                        method=v.method + " + cross_examination",
                        explanation=v.explanation +
                        f" | Cross-exam: {exam_result.get('explanation', '')}",
                    )
                    break

    logger.info("Cross-examined %d facts, %d had inconsistencies",
                len(exam_results),
                sum(1 for e in exam_results.values() if not e.get("consistent", True)))

    await _emit(state, "step_complete", {
        "step": "cross_examination",
        "data": {"examined_count": len(exam_results)},
    })
    return {
        "cross_examination_results": exam_results,
        "verification_results": updated_verifications,
    }


# ─── Node 6: Cross-Reference & Revise (MERGED) ─────────────────────


REVISE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are revising a document based on verification findings. Apply corrections while
preserving the original intent and style. Mark any changes with [REVISED] inline.

If no corrections are needed, return the original document unchanged."""),
    ("human", """Original document:
{document}

Issues found:
{issues}

Verification problems:
{verification_problems}"""),
])


async def cross_reference_and_revise(state: GenDocState) -> dict:
    """Detect contradictions and revise document in a combined step."""
    await _emit(state, "step_start", {"step": "cross_reference", "label": "Cross-Referencing & Revising Document"})

    facts = state.get("atomic_facts", [])
    results = state.get("verification_results", [])

    # Step 1: Detect contradictions (1 LLM call)
    issues = await detect_contradictions(facts)

    # Step 2: Collect verification problems for revision
    verification_problems = "\n".join(
        f"- [{r.status.value}] (conf={r.confidence:.2f}) {r.fact.text[:100]}"
        for r in results
        if r.status in (FactStatus.HALLUCINATED, FactStatus.UNCERTAIN)
    )

    issues_text = "\n".join(
        f"- [{i.type.value}] {i.explanation}" for i in issues
    )

    # Step 3: Revise if needed (1 LLM call, only if issues exist)
    if not issues_text and not verification_problems:
        await _emit(state, "step_complete", {
            "step": "cross_reference",
            "data": {"issues_found": 0, "revised": False},
        })
        return {
            "consistency_issues": issues,
            "revised_document": state.get("document", ""),
        }

    llm = get_llm(temperature=0)
    chain = REVISE_PROMPT | llm
    result = await chain.ainvoke({
        "document": state.get("document", ""),
        "issues": issues_text or "None",
        "verification_problems": verification_problems or "None",
    })

    await _emit(state, "step_complete", {
        "step": "cross_reference",
        "data": {"issues_found": len(issues), "revised": True},
    })
    return {
        "consistency_issues": issues,
        "revised_document": result.content,
    }


# ─── Node 7: Generate Quiz ──────────────────────────────────────────


async def generate_quiz(state: GenDocState) -> dict:
    """Generate multi-level comprehension questions."""
    await _emit(state, "step_start", {"step": "generate_quiz", "label": "Generating Comprehension Quiz"})

    document = state.get("revised_document") or state.get("document", "")
    facts = state.get("atomic_facts", [])
    issues = state.get("consistency_issues", [])

    issues_text = "\n".join(f"- {i.explanation}" for i in issues)
    questions = await _generate_quiz(document, facts, issues_text, n_questions=6)

    await _emit(state, "step_complete", {
        "step": "generate_quiz",
        "data": {"question_count": len(questions), "questions": [q.model_dump() for q in questions]},
    })
    return {"comprehension_questions": questions}


# ─── Node 8: Evaluate Answers ──────────────────────────────────────


async def evaluate_answers(state: GenDocState) -> dict:
    """Score user answers — uses rule-based matching (no LLM call needed)."""
    await _emit(state, "step_start", {"step": "evaluate_answers", "label": "Evaluating Comprehension"})

    questions = state.get("comprehension_questions", [])
    answers = state.get("user_answers", {})

    if not answers:
        await _emit(state, "step_complete", {"step": "evaluate_answers", "data": {"score": 0, "pending": True}})
        return {"comprehension_score": 0.0}

    # Rule-based scoring — no LLM call needed for MCQ
    correct_count = 0
    for q in questions:
        user_answer = answers.get(q.id, "")
        if user_answer.strip().lower() == q.correct_answer.strip().lower():
            correct_count += 1

    avg_score = correct_count / max(len(questions), 1)

    await _emit(state, "step_complete", {"step": "evaluate_answers", "data": {"score": avg_score}})
    return {"comprehension_score": avg_score}


# ─── Node 9: Final Report ──────────────────────────────────────────


async def final_report(state: GenDocState) -> dict:
    """Compile the final ConfidenceReport with enhanced calibration."""
    await _emit(state, "step_start", {"step": "final_report", "label": "Compiling Final Report"})

    results = state.get("verification_results", [])
    issues = state.get("consistency_issues", [])
    exam_results = state.get("cross_examination_results", {})
    ev_grounding = state.get("evidence_grounding_results", {})

    # Compute factuality
    if results:
        factuality = sum(r.confidence for r in results) / len(results)
    else:
        factuality = 0.0

    # Consistency derived from verification agreement (replaces self-consistency)
    if results:
        verified_count = sum(
            1 for r in results if r.status == FactStatus.VERIFIED)
        consistency = verified_count / len(results)
    else:
        consistency = 0.0

    # Source grounding — measures ACTUAL grounding against evidence
    critical_issues = sum(1 for i in issues if i.severity.value == "critical")
    warning_issues = sum(1 for i in issues if i.severity.value == "warning")
    issue_penalty = critical_issues * 0.2 + warning_issues * 0.1

    if ev_grounding:
        supported = sum(1 for r in ev_grounding.values()
                        if r["grounding"] == "SUPPORTED")
        partial = sum(1 for r in ev_grounding.values()
                      if r["grounding"] == "PARTIAL")
        total_ev = len(ev_grounding)
        ev_score = (supported + partial * 0.5) / max(total_ev, 1)
        source_grounding = max(0.0, min(1.0, ev_score - issue_penalty))
    else:
        source_grounding = max(0.0, min(1.0, 1.0 - issue_penalty))

    # Cross-examination bonus/penalty
    if exam_results:
        consistent_count = sum(
            1 for e in exam_results.values() if e.get("consistent", True))
        exam_ratio = consistent_count / \
            len(exam_results) if exam_results else 1.0
        factuality = 0.7 * factuality + 0.3 * exam_ratio

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

    for _fact_id, ev in ev_grounding.items():
        if ev["grounding"] == "CONTRADICTED":
            risk_areas.append({
                "fact": f"[EVIDENCE CONFLICT] {ev.get('explanation', '')[:100]}",
                "status": "contradicted_by_evidence",
                "confidence": ev.get("confidence", 0),
            })

    recommendations = []
    if factuality < 0.7:
        recommendations.append(
            "Several facts could not be verified — review highlighted sections carefully.")
    if len(issues) > 0:
        recommendations.append(
            f"{len(issues)} consistency issue(s) found — check for contradictions.")
    if ev_grounding:
        contradicted = sum(1 for r in ev_grounding.values()
                           if r["grounding"] == "CONTRADICTED")
        if contradicted > 0:
            recommendations.append(
                f"{contradicted} fact(s) contradict your provided evidence — review these carefully.")
        supported = sum(1 for r in ev_grounding.values()
                        if r["grounding"] == "SUPPORTED")
        recommendations.append(
            f"{supported}/{len(ev_grounding)} facts grounded in your evidence.")
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


def build_verification_graph() -> StateGraph:
    """Build the optimized verification LangGraph.

    Pipeline: generate_document → decompose_facts → evidence_grounding (1 batch call)
    → execute_verification (1 call/fact) → cross_examination (selective)
    → cross_reference_and_revise → generate_quiz → evaluate_answers → final_report
    """
    graph = StateGraph(GenDocState)

    graph.add_node("generate_document", generate_document)
    graph.add_node("decompose_facts", decompose_facts)
    graph.add_node("evidence_grounding", evidence_grounding)
    graph.add_node("execute_verification", execute_verification)
    graph.add_node("cross_examination", cross_examination)
    graph.add_node("cross_reference_and_revise", cross_reference_and_revise)
    graph.add_node("generate_quiz", generate_quiz)
    graph.add_node("evaluate_answers", evaluate_answers)
    graph.add_node("final_report", final_report)

    graph.set_entry_point("generate_document")
    graph.add_edge("generate_document", "decompose_facts")
    graph.add_edge("decompose_facts", "evidence_grounding")
    graph.add_edge("evidence_grounding", "execute_verification")
    graph.add_edge("execute_verification", "cross_examination")
    graph.add_edge("cross_examination", "cross_reference_and_revise")
    graph.add_edge("cross_reference_and_revise", "generate_quiz")
    graph.add_edge("generate_quiz", "evaluate_answers")
    graph.add_edge("evaluate_answers", "final_report")
    graph.add_edge("final_report", END)

    return graph
