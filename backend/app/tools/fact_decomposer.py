"""
Atomic Fact Decomposer — breaks document text into individually verifiable claims.
Inspired by FActScore (Min et al., 2023) and SAFE (Wei et al., 2024).
"""
from __future__ import annotations
import json

from langchain_core.prompts import ChatPromptTemplate

from app.services.llm import get_llm
from app.models.schemas import AtomicFact, FactCategory

DECOMPOSE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a fact decomposition engine. Given a document, break it into atomic facts.

Each atomic fact is a single, independently verifiable claim.

Rules:
- One fact per entry
- Each fact must be independently verifiable
- Categorize each as: factual_claim | statistic | citation | definition | opinion | temporal
- Preserve the exact wording from the source

Respond ONLY with a JSON array. Each element:
{{"text": "...", "category": "factual_claim", "section": "..."}}"""),
    ("human", "Document:\n\n{document}"),
])


async def decompose_document(document: str) -> list[AtomicFact]:
    """Decompose a document into atomic facts."""
    llm = get_llm(temperature=0)
    chain = DECOMPOSE_PROMPT | llm
    result = await chain.ainvoke({"document": document})

    raw = result.content.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        facts_data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    facts: list[AtomicFact] = []
    for i, f in enumerate(facts_data):
        cat = f.get("category", "factual_claim")
        try:
            category = FactCategory(cat)
        except ValueError:
            category = FactCategory.FACTUAL_CLAIM
        text = f.get("text", "")
        start = document.find(text)
        facts.append(AtomicFact(
            text=text,
            category=category,
            position_start=max(start, 0),
            position_end=max(start, 0) + len(text),
            section=f.get("section", ""),
        ))
    return facts
