"""
Self-Consistency Checker — inspired by SelfCheckGPT (Manakul et al., 2023).
Generates multiple samples and checks whether facts appear consistently.
Parallelized: samples generated concurrently, facts checked concurrently.
"""
from __future__ import annotations
import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.services.llm import get_llm
from app.services.parallel import throttled_call
from app.config import get_settings
from app.models.schemas import AtomicFact

logger = logging.getLogger(__name__)

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


async def _generate_sample(gen_llm, prompt: str) -> str:
    """Generate a single alternative document sample."""
    result = await gen_llm.ainvoke(prompt)
    return result.content


async def _check_fact(chain, fact: AtomicFact, alt_text: str) -> tuple[str, float]:
    """Check a single fact's consistency. Returns (fact_id, score)."""
    result = await chain.ainvoke({"claim": fact.text, "alternatives": alt_text})
    raw = result.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        data = json.loads(raw)
        return fact.id, float(data.get("consistency_score", 0.5))
    except (json.JSONDecodeError, ValueError):
        return fact.id, 0.5


async def check_self_consistency(
    document: str,
    facts: list[AtomicFact],
    prompt: str,
) -> dict[str, float]:
    """
    Generate alternative documents and check each fact for consistency.
    Returns a dict mapping fact IDs to consistency scores.
    PARALLELIZED: samples generated concurrently, facts checked concurrently.
    """
    import asyncio

    settings = get_settings()
    gen_llm = get_llm(temperature=settings.self_consistency_temperature)
    checker_llm = get_llm(temperature=0)
    n_samples = settings.self_consistency_samples

    # Step 1: Generate alternative samples IN PARALLEL
    logger.info("Generating %d self-consistency samples in parallel", n_samples)
    sample_tasks = [
        throttled_call(_generate_sample(gen_llm, prompt))
        for _ in range(n_samples)
    ]
    alternatives = await asyncio.gather(*sample_tasks, return_exceptions=True)
    # Filter out exceptions
    alternatives = [a for a in alternatives if isinstance(a, str)]
    logger.info("Got %d samples successfully", len(alternatives))

    alt_text = "\n---\n".join(
        f"Version {i+1}:\n{alt}" for i, alt in enumerate(alternatives)
    )

    # Step 2: Check each fact IN PARALLEL
    chain = CONSISTENCY_CHECK_PROMPT | checker_llm
    fact_tasks = [
        throttled_call(_check_fact(chain, fact, alt_text))
        for fact in facts
    ]
    results = await asyncio.gather(*fact_tasks, return_exceptions=True)

    scores: dict[str, float] = {}
    for r in results:
        if isinstance(r, tuple):
            scores[r[0]] = r[1]
    logger.info("Checked %d facts for consistency", len(scores))

    return scores
