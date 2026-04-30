"""
Cross-Examination Verifier — inspired by LM vs LM (Cohen et al., 2023) and CoVe (Dhuliawala et al., 2023).
For uncertain facts, generates probing questions AND answers them in a single call (Factored Lite),
then judges consistency in a separate call to avoid confirmation bias.
Reduced from 5 calls to 2 calls per fact.
"""
from __future__ import annotations
import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.services.llm import get_llm

logger = logging.getLogger(__name__)

# Combined: generate probing questions AND answer them independently
PROBE_AND_ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a cross-examiner investigating a claim. Your task:

1. Generate 3 probing questions that would help determine if the claim is true or false.
   These questions should test specific details, implications, and related facts.

2. For EACH question, answer it using ONLY your own knowledge.
   Answer as if you have NOT seen the original claim — reason from first principles.
   Be specific and factual.

Respond ONLY with JSON:
{{
  "probes": [
    {{"question": "<str>", "answer": "<str>", "confidence": <float 0-1>}},
    {{"question": "<str>", "answer": "<str>", "confidence": <float 0-1>}},
    {{"question": "<str>", "answer": "<str>", "confidence": <float 0-1>}}
  ]
}}"""),
    ("human", "Claim to investigate: {claim}"),
])

# Separate judge to avoid confirmation bias (CoVe Factored insight)
CONSISTENCY_JUDGE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are judging whether a claim is consistent with independently-gathered evidence.
Given the original claim and answers to probing questions, determine if there are inconsistencies.

Respond ONLY with JSON:
{{
  "consistent": <bool>,
  "confidence_adjustment": <float -0.3 to +0.1>,
  "inconsistencies": ["<str>", ...],
  "explanation": "<str>"
}}

confidence_adjustment should be:
- Positive (up to +0.1) if evidence strongly confirms the claim
- Zero if evidence is neutral
- Negative (down to -0.3) if evidence contradicts the claim"""),
    ("human", """Original claim: {claim}

Probing questions and independent answers:
{qa_pairs}"""),
])


async def cross_examine_fact(claim: str) -> dict:
    """
    Cross-examine a single fact using 2 LLM calls (down from 5):
    Call 1: Generate probing questions + answer them
    Call 2: Judge consistency (separate context to avoid confirmation bias)
    """
    llm = get_llm(temperature=0)

    # Call 1: Generate probes + answers in one pass
    probe_chain = PROBE_AND_ANSWER_PROMPT | llm
    result = await probe_chain.ainvoke({"claim": claim})
    raw = result.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        data = json.loads(raw)
        probes = data.get("probes", [])
    except json.JSONDecodeError:
        probes = []

    if not probes:
        return {
            "consistent": True,
            "confidence_adjustment": 0,
            "inconsistencies": [],
            "explanation": "Could not generate probes",
            "probes": 0,
        }

    # Build Q&A pairs for the judge
    qa_pairs = "\n\n".join(
        f"Q: {p.get('question', '')}\nA: {p.get('answer', 'No answer')}"
        for p in probes
    )

    # Call 2: Judge consistency (separate call to avoid bias)
    judge_chain = CONSISTENCY_JUDGE_PROMPT | llm
    judge_result = await judge_chain.ainvoke({
        "claim": claim,
        "qa_pairs": qa_pairs,
    })

    raw = judge_result.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        judge_data = json.loads(raw)
        return {
            "consistent": judge_data.get("consistent", True),
            "confidence_adjustment": float(judge_data.get("confidence_adjustment", 0)),
            "inconsistencies": judge_data.get("inconsistencies", []),
            "explanation": judge_data.get("explanation", ""),
            "probes": len(probes),
        }
    except (json.JSONDecodeError, ValueError):
        return {
            "consistent": True,
            "confidence_adjustment": 0,
            "inconsistencies": [],
            "explanation": "Could not parse cross-examination result",
            "probes": len(probes),
        }
