"""
Contradiction Detector — finds logical contradictions within a document.
Cross-checks every pair of facts for mutual exclusivity.
"""
from __future__ import annotations
import json

from langchain_core.prompts import ChatPromptTemplate

from app.services.llm import get_llm
from app.models.schemas import AtomicFact, ConsistencyIssue, IssueSeverity, IssueType

CONTRADICTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a contradiction detector. Given a list of atomic facts from the same document,
find ALL pairs that contradict each other, are logically inconsistent, or present conflicting information.

Also flag any facts that are internally incoherent or self-contradictory.

Respond ONLY with a JSON array. Each element:
{{
  "fact_a_index": <int>,
  "fact_b_index": <int or null if self-contradictory>,
  "type": "<contradiction|ambiguity|unsupported_inference|temporal_inconsistency>",
  "severity": "<critical|warning|info>",
  "explanation": "<str>"
}}

Return an empty array [] if no issues found."""),
    ("human", """Facts:
{facts_text}"""),
])


async def detect_contradictions(
    facts: list[AtomicFact],
) -> list[ConsistencyIssue]:
    """Detect contradictions and inconsistencies among facts."""
    llm = get_llm(temperature=0)

    facts_text = "\n".join(f"[{i}] {f.text}" for i, f in enumerate(facts))
    chain = CONTRADICTION_PROMPT | llm
    result = await chain.ainvoke({"facts_text": facts_text})

    raw = result.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        issues_data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    issues: list[ConsistencyIssue] = []
    for issue in issues_data:
        a_idx = issue.get("fact_a_index", 0)
        b_idx = issue.get("fact_b_index")

        fact_ids = [facts[a_idx].id] if a_idx < len(facts) else []
        if b_idx is not None and b_idx < len(facts):
            fact_ids.append(facts[b_idx].id)

        sev_map = {"critical": IssueSeverity.CRITICAL,
                   "warning": IssueSeverity.WARNING, "info": IssueSeverity.INFO}
        type_map = {
            "contradiction": IssueType.CONTRADICTION,
            "ambiguity": IssueType.AMBIGUITY,
            "unsupported_inference": IssueType.UNSUPPORTED_INFERENCE,
            "temporal_inconsistency": IssueType.TEMPORAL_INCONSISTENCY,
        }

        issues.append(ConsistencyIssue(
            type=type_map.get(issue.get("type", ""), IssueType.CONTRADICTION),
            severity=sev_map.get(
                issue.get("severity", ""), IssueSeverity.INFO),
            explanation=issue.get("explanation", ""),
            facts_involved=fact_ids,
        ))

    return issues
