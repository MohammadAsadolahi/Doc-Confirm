"""
Evidence Grounding Checker — verifies facts against user-provided reference materials.
Retrieval-Augmented Verification: batches ALL facts into a single LLM call
and judges whether the evidence supports, contradicts, or is silent on each claim.
Inspired by RAGAS NLIStatementPrompt pattern for efficient batch verification.
"""
from __future__ import annotations

import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.models.schemas import AtomicFact, EvidenceDocument
from app.services.llm import get_llm

logger = logging.getLogger(__name__)

# ─── Prompts ─────────────────────────────────────────────────────────

BATCH_GROUNDING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a grounding verifier. You will receive a list of CLAIMS from a document and
EVIDENCE passages provided by the user. For EACH claim, determine whether the evidence
supports, contradicts, or is silent on it.

Rules for each claim:
- SUPPORTED: The evidence clearly confirms the claim (directly or through strong implication)
- CONTRADICTED: The evidence clearly conflicts with the claim
- NOT_FOUND: The evidence does not address this claim at all
- PARTIAL: The evidence partially supports the claim but with differences

Be precise. Do not infer beyond what the evidence states.
You MUST return a result for EVERY claim — do not skip any.

Respond ONLY with a JSON array. Each element (one per claim, in the SAME order as the input):
{{
  "claim_index": <int>,
  "grounding": "<SUPPORTED|CONTRADICTED|NOT_FOUND|PARTIAL>",
  "confidence": <float 0-1>,
  "matching_passage": "<the relevant excerpt from evidence, or empty string if NOT_FOUND>",
  "explanation": "<why you reached this conclusion>"
}}"""),
    ("human", """CLAIMS:
{claims_text}

EVIDENCE:
{evidence_text}"""),
])


# ─── Evidence chunking ──────────────────────────────────────────────


def _chunk_evidence(evidence_docs: list[EvidenceDocument], max_chars: int = 6000) -> str:
    """
    Combine all evidence into a single text block for the LLM.
    If total exceeds max_chars, truncate per document proportionally.
    """
    total = sum(len(e.content) for e in evidence_docs)

    if total <= max_chars:
        parts = []
        for e in evidence_docs:
            header = f"--- [{e.label}] ---"
            parts.append(f"{header}\n{e.content}")
        return "\n\n".join(parts)

    # Proportional truncation
    parts = []
    for e in evidence_docs:
        budget = int(max_chars * len(e.content) / total)
        header = f"--- [{e.label}] ---"
        parts.append(f"{header}\n{e.content[:budget]}")
    return "\n\n".join(parts)


# ─── Public API ──────────────────────────────────────────────────────


async def check_evidence_grounding(
    facts: list[AtomicFact],
    evidence_docs: list[EvidenceDocument],
) -> dict[str, dict]:
    """
    Check all facts against user-provided evidence in a SINGLE batched LLM call.
    Returns {fact_id: {grounding, confidence, matching_passage, explanation}}.
    """
    if not evidence_docs:
        return {}

    evidence_text = _chunk_evidence(evidence_docs)
    logger.info(
        "Checking %d facts against %d evidence documents (%d chars) in single batch call",
        len(facts), len(evidence_docs), len(evidence_text),
    )

    # Build numbered claims list
    claims_text = "\n".join(
        f"[{i}] {f.text}" for i, f in enumerate(facts)
    )

    llm = get_llm(temperature=0)
    chain = BATCH_GROUNDING_PROMPT | llm
    result = await chain.ainvoke({
        "claims_text": claims_text,
        "evidence_text": evidence_text,
    })

    raw = result.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    # Parse batch results
    results: dict[str, dict] = {}
    try:
        batch_data = json.loads(raw)
        if isinstance(batch_data, list):
            for item in batch_data:
                idx = item.get("claim_index", -1)
                if 0 <= idx < len(facts):
                    results[facts[idx].id] = {
                        "grounding": item.get("grounding", "NOT_FOUND"),
                        "confidence": float(item.get("confidence", 0.5)),
                        "matching_passage": item.get("matching_passage", ""),
                        "explanation": item.get("explanation", ""),
                    }
    except json.JSONDecodeError:
        logger.error("Failed to parse batch evidence grounding response")

    # Fill in any missing facts with defaults
    for fact in facts:
        if fact.id not in results:
            results[fact.id] = {
                "grounding": "NOT_FOUND",
                "confidence": 0.5,
                "matching_passage": "",
                "explanation": "Not included in batch response",
            }

    supported = sum(1 for r in results.values()
                    if r["grounding"] == "SUPPORTED")
    contradicted = sum(1 for r in results.values()
                       if r["grounding"] == "CONTRADICTED")
    logger.info(
        "Evidence grounding: %d supported, %d contradicted, %d not found, %d partial",
        supported, contradicted,
        sum(1 for r in results.values() if r["grounding"] == "NOT_FOUND"),
        sum(1 for r in results.values() if r["grounding"] == "PARTIAL"),
    )

    return results
