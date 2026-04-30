"""
Web Search Verification — inspired by SAFE (Wei et al., 2024).
Uses the LLM to verify claims against its own training knowledge (no Tavily needed).
"""
from __future__ import annotations
import json

from langchain_core.prompts import ChatPromptTemplate

from app.services.llm import get_llm
from app.models.schemas import Evidence

VERIFY_CLAIM_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a rigorous fact checker. Given a claim, determine:
1. Is the claim SUPPORTED, REFUTED, or INCONCLUSIVE based on your knowledge?
2. Your confidence (0.0-1.0)
3. What evidence supports or refutes it?
4. Provide source references if you know them.

Respond ONLY with JSON:
{{"verdict": "<SUPPORTED|REFUTED|INCONCLUSIVE>", "confidence": <float>, "explanation": "<str>", "sources": ["<str>", ...]}}"""),
    ("human", "Claim to verify: {claim}"),
])


async def verify_claim(claim: str) -> dict:
    """Verify a single claim using the LLM. Returns verdict + evidence."""
    llm = get_llm(temperature=0)
    chain = VERIFY_CLAIM_PROMPT | llm
    result = await chain.ainvoke({"claim": claim})

    raw = result.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"verdict": "INCONCLUSIVE", "confidence": 0.5,
                "explanation": "Parse error", "sources": []}

    evidence_list = [
        Evidence(source=s, text=data.get("explanation", ""), url="")
        for s in data.get("sources", [])
    ]

    return {
        "verdict": data.get("verdict", "INCONCLUSIVE"),
        "confidence": float(data.get("confidence", 0.5)),
        "explanation": data.get("explanation", ""),
        "evidence": evidence_list,
    }
