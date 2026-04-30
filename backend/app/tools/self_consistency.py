"""
Self-Consistency Checker — inspired by SelfCheckGPT (Manakul et al., 2023).
Generates multiple samples and checks whether facts appear consistently.
"""
from __future__ import annotations
import json

from langchain_core.prompts import ChatPromptTemplate

from app.services.llm import get_llm
from app.config import get_settings
from app.models.schemas import AtomicFact

CONSISTENCY_CHECK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You check whether a specific claim is consistent across alternative document versions.

Given the original claim and alternative versions, determine:
1. How many versions contain this same claim (or equivalent)?
2. Do any versions contradict it?

Respond ONLY with JSON:
{{"consistency_score": <float 0-1>, "appears_in": <int>, "contradicted_by": <int>, "explanation": "<str>"}}"""),
    ("human", """Original claim: {claim}

Alternative versions:
{alternatives}"""),
])


async def check_self_consistency(
    document: str,
    facts: list[AtomicFact],
    prompt: str,
) -> dict[str, float]:
    """
    Generate alternative documents and check each fact for consistency.
    Returns a dict mapping fact IDs to consistency scores.
    """
    settings = get_settings()
    gen_llm = get_llm(temperature=settings.self_consistency_temperature)
    checker_llm = get_llm(temperature=0)
    n_samples = settings.self_consistency_samples

    # Step 1: Generate alternative samples
    alternatives: list[str] = []
    for _ in range(n_samples):
        result = await gen_llm.ainvoke(prompt)
        alternatives.append(result.content)

    alt_text = "\n---\n".join(
        f"Version {i+1}:\n{alt}" for i, alt in enumerate(alternatives)
    )

    # Step 2: Check each fact
    chain = CONSISTENCY_CHECK_PROMPT | checker_llm
    scores: dict[str, float] = {}
    for fact in facts:
        result = await chain.ainvoke({"claim": fact.text, "alternatives": alt_text})
        raw = result.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        try:
            data = json.loads(raw)
            scores[fact.id] = float(data.get("consistency_score", 0.5))
        except (json.JSONDecodeError, ValueError):
            scores[fact.id] = 0.5

    return scores
