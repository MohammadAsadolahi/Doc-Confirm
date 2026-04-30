"""
Multi-Perspective Fact Verification — inspired by SAFE (Wei et al., 2024), Self-Contrast (Zhang et al., 2024),
and Solo Performance Prompting (Wang et al., 2024).
Verifies claims from 3 expert perspectives in a SINGLE LLM call using structured multi-perspective prompting.
"""
from __future__ import annotations
import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.services.llm import get_llm
from app.models.schemas import Evidence, FactCategory

logger = logging.getLogger(__name__)

# Single unified multi-perspective verification prompt
UNIFIED_VERIFICATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a multi-perspective fact verification system. For the claim below,
analyze it from three distinct expert perspectives, then synthesize a final verdict.

PERSPECTIVE 1 — Domain Expert:
Assess technical accuracy, correct use of terminology, and factual precision using deep domain knowledge.

PERSPECTIVE 2 — Professional Skeptic:
Actively look for reasons the claim could be WRONG. Consider edge cases, exceptions, outdated information, common misconceptions. Be tough but fair.

PERSPECTIVE 3 — Rigorous Fact Checker:
Focus on verifiable details: dates, numbers, statistics, names, locations. Cross-reference against your knowledge and flag anything that seems off.

After analyzing from all three perspectives, synthesize a final verdict.

Respond ONLY with JSON:
{{
  "perspectives": [
    {{"name": "domain_expert", "verdict": "<SUPPORTED|REFUTED|INCONCLUSIVE>", "confidence": <float 0-1>, "explanation": "<str>", "sources": ["<str>"]}},
    {{"name": "skeptic", "verdict": "<SUPPORTED|REFUTED|INCONCLUSIVE>", "confidence": <float 0-1>, "explanation": "<str>", "sources": ["<str>"]}},
    {{"name": "fact_checker", "verdict": "<SUPPORTED|REFUTED|INCONCLUSIVE>", "confidence": <float 0-1>, "explanation": "<str>", "sources": ["<str>"]}}
  ],
  "final_verdict": "<SUPPORTED|REFUTED|INCONCLUSIVE>",
  "final_confidence": <float 0-1>,
  "final_explanation": "<synthesized explanation>"
}}"""),
    ("human", "Claim to verify: {claim}"),
])

# Category-based priors — statistics and citations are harder to verify
CATEGORY_PRIORS = {
    FactCategory.FACTUAL_CLAIM: 0.80,
    FactCategory.STATISTIC: 0.60,
    FactCategory.CITATION: 0.55,
    FactCategory.DEFINITION: 0.85,
    FactCategory.OPINION: 0.70,
    FactCategory.TEMPORAL: 0.65,
}


def _aggregate_result(data: dict, category: FactCategory | None = None) -> dict:
    """
    Process the unified verification result with category-aware calibration.
    """
    perspectives = data.get("perspectives", [])
    final_verdict = data.get("final_verdict", "INCONCLUSIVE")
    final_confidence = float(data.get("final_confidence", 0.5))
    final_explanation = data.get("final_explanation", "")

    # If perspectives are available, compute agreement-based calibration
    if perspectives:
        verdicts = [p.get("verdict", "INCONCLUSIVE") for p in perspectives]
        confidences = [float(p.get("confidence", 0.5)) for p in perspectives]

        supported = verdicts.count("SUPPORTED")
        refuted = verdicts.count("REFUTED")
        total = len(verdicts)
        avg_confidence = sum(confidences) / len(confidences)

        if supported == total:
            calibrated = min(1.0, avg_confidence * 1.15)
        elif refuted == total:
            calibrated = min(1.0, avg_confidence * 1.15)
        elif supported > refuted:
            agreement_ratio = supported / total
            calibrated = avg_confidence * (0.6 + 0.4 * agreement_ratio)
        elif refuted > supported:
            agreement_ratio = refuted / total
            calibrated = avg_confidence * (0.6 + 0.4 * agreement_ratio)
        else:
            calibrated = avg_confidence * 0.5

        # Blend with LLM's own final_confidence
        calibrated = 0.5 * calibrated + 0.5 * final_confidence
    else:
        calibrated = final_confidence

    # Apply category-based prior if available
    if category:
        prior = CATEGORY_PRIORS.get(category, 0.75)
        calibrated = 0.3 * prior + 0.7 * calibrated

    # Collect all sources
    all_sources = []
    for p in perspectives:
        all_sources.extend(p.get("sources", []))
    all_sources = list(set(all_sources))

    # Build explanation from perspectives
    explanations = []
    for p in perspectives:
        if isinstance(p, dict):
            explanations.append(
                f"[{p.get('name', '?')}] {p.get('explanation', '')}")
    combined_explanation = " | ".join(
        explanations) if explanations else final_explanation

    return {
        "verdict": final_verdict,
        "confidence": round(calibrated, 3),
        "explanation": combined_explanation,
        "sources": all_sources,
        "perspectives": perspectives,
    }


async def verify_claim(claim: str, category: FactCategory | None = None) -> dict:
    """
    Verify a single claim using multi-perspective verification in a SINGLE LLM call.
    Returns aggregated verdict + evidence.
    """
    llm = get_llm(temperature=0)
    chain = UNIFIED_VERIFICATION_PROMPT | llm
    result = await chain.ainvoke({"claim": claim})

    raw = result.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"final_verdict": "INCONCLUSIVE", "final_confidence": 0.5,
                "final_explanation": "Parse error", "perspectives": []}

    aggregated = _aggregate_result(data, category)

    evidence_list = [
        Evidence(source=s, text=aggregated.get("explanation", ""), url="")
        for s in aggregated.get("sources", [])
    ]

    return {
        "verdict": aggregated["verdict"],
        "confidence": aggregated["confidence"],
        "explanation": aggregated["explanation"],
        "evidence": evidence_list,
        "perspectives": aggregated.get("perspectives", []),
    }
