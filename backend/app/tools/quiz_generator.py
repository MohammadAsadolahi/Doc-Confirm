"""
Quiz Generator — creates comprehension questions to test the user's understanding.
Produces multi-level questions including trap questions to detect blind acceptance.
"""
from __future__ import annotations
import json
import re
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.services.llm import get_llm
from app.models.schemas import AtomicFact, Question, QuestionType, Difficulty

logger = logging.getLogger(__name__)

QUIZ_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a quiz generator that creates questions to test whether a user truly understands a document.

Create a mix of question types:
- recall: basic fact recall
- analysis: interpreting implications
- application: applying knowledge from the document
- trap: plausible-sounding questions where the correct answer is that the document DOESN'T say this (to catch blind acceptance)
- scenario: practical application of the document's content

Difficulty levels: easy, medium, hard

For each question provide 4 options (A-D) and the correct answer letter.

Respond ONLY with a JSON array. Each element:
{{
  "text": "<the question text>",
  "type": "<recall|analysis|application|trap|scenario>",
  "difficulty": "<easy|medium|hard>",
  "options": ["<A>", "<B>", "<C>", "<D>"],
  "correct_answer": "<the correct option text>",
  "explanation": "<why this answer is correct>",
  "related_fact": "<the fact this question tests>"
}}

Generate {n_questions} questions with good variety across types and difficulties."""),
    ("human", """Document:
{document}

Key facts found:
{facts_text}

Verification issues found:
{issues_text}"""),
])


def _repair_truncated_json(raw: str) -> list[dict] | None:
    """Try to recover complete objects from truncated JSON array."""
    # Find the last complete object by looking for "}," or "}\n]"
    results = []
    depth = 0
    obj_start = None
    for i, ch in enumerate(raw):
        if ch == '{':
            if depth == 0:
                obj_start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and obj_start is not None:
                try:
                    obj = json.loads(raw[obj_start:i + 1])
                    results.append(obj)
                except json.JSONDecodeError:
                    pass
                obj_start = None
    return results if results else None


async def generate_quiz(
    document: str,
    facts: list[AtomicFact],
    issues_text: str = "",
    n_questions: int = 8,
) -> list[Question]:
    """Generate quiz questions from the document and its verified facts."""
    llm = get_llm(temperature=0.3, max_tokens=4096)

    # Limit input size to avoid truncated output
    facts_text = "\n".join(f"- {f.text}" for f in facts[:12])
    doc_truncated = document[:3000] if len(document) > 3000 else document
    chain = QUIZ_PROMPT | llm
    result = await chain.ainvoke({
        "document": doc_truncated,
        "facts_text": facts_text,
        "issues_text": issues_text or "No issues found.",
        "n_questions": n_questions,
    })

    raw = result.content.strip()
    # Strip markdown code fences
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    # Try to extract JSON array from anywhere in the text
    try:
        questions_data = json.loads(raw)
    except json.JSONDecodeError:
        # Try to find a JSON array in the text
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            try:
                questions_data = json.loads(match.group())
            except json.JSONDecodeError:
                # Try to repair truncated JSON by finding last complete object
                repaired = _repair_truncated_json(raw)
                if repaired:
                    questions_data = repaired
                else:
                    logger.error(
                        "Quiz generator: could not parse JSON from LLM output: %s", raw[:500])
                    return []
        else:
            logger.error(
                "Quiz generator: no JSON array found in LLM output: %s", raw[:500])
            return []

    questions: list[Question] = []
    for q in questions_data:
        try:
            qtype = QuestionType(q.get("type", "recall"))
        except ValueError:
            qtype = QuestionType.RECALL
        try:
            diff = Difficulty(q.get("difficulty", "medium"))
        except ValueError:
            diff = Difficulty.MEDIUM

        questions.append(Question(
            text=q.get("text", ""),
            type=qtype,
            difficulty=diff,
            options=q.get("options", []),
            correct_answer=q.get("correct_answer", ""),
            explanation=q.get("explanation", ""),
            related_facts=[q.get("related_fact", "")],
        ))

    return questions
