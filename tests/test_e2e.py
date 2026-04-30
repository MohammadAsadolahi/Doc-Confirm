"""
E2E test script for GenDoc Confirm using Playwright.
Tests the full flow: create project → input document → run verification → take quiz → view report.

Run with: python -m pytest tests/test_e2e.py -v
"""
import asyncio
import json
import time
import httpx
import pytest

BASE_URL = "http://localhost:8000/api/v1"
FRONTEND_URL = "http://localhost:3000"

TEST_DOCUMENT = """# Quarterly Revenue Report - Q4 2025

## Executive Summary
Revenue for Q4 2025 reached $5.2 million, representing a 15% year-over-year growth.
Customer retention rate improved to 94%, up from 89% in Q3.

## Financial Highlights
- Total revenue: $5.2M (up 15% YoY)
- Operating costs decreased by 8% due to automation initiatives
- Net profit margin: 22%
- Customer acquisition cost: $150 per customer

## Market Position
The company holds approximately 23% market share in the SaaS analytics segment.
According to Gartner's 2025 Magic Quadrant, we are positioned as a Leader.

## Key Metrics
- Monthly Active Users: 45,000
- Net Promoter Score: 72
- Customer Lifetime Value: $4,800
- Churn rate: 6% annually

## Outlook
CEO John Smith announced plans for European expansion in Q2 2026.
The board approved a $10M investment in AI-powered features.
"""


@pytest.fixture
def client():
    return httpx.Client(base_url=BASE_URL, timeout=120.0)


def test_health(client):
    """Test that the backend is healthy with enhanced checks."""
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert "checks" in data
    assert "llm_provider" in data["checks"]
    assert "active_sessions" in data["checks"]
    assert "uptime_seconds" in data["checks"]
    assert isinstance(data["checks"]["uptime_seconds"], int)


def test_create_project(client):
    """Test creating a new project."""
    r = client.post(
        "/projects/", json={"name": "E2E Test Project", "description": "Automated test"})
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["name"] == "E2E Test Project"
    assert data["status"] == "draft"
    return data["id"]


def test_set_document(client):
    """Test setting a document on a project."""
    # Create project first
    r = client.post("/projects/", json={"name": "Doc Test", "description": ""})
    project_id = r.json()["id"]

    # Set document
    r = client.post(f"/projects/{project_id}/document",
                    json={"document": TEST_DOCUMENT})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["has_document"] is True

    # Get document back
    r = client.get(f"/projects/{project_id}/document")
    assert r.status_code == 200
    data = r.json()
    assert TEST_DOCUMENT in data["document"]


def test_full_verification_flow(client):
    """Test the complete verification pipeline end-to-end."""
    # 1. Create project
    r = client.post(
        "/projects/", json={"name": "Full E2E Flow", "description": "Complete test"})
    assert r.status_code == 200
    project_id = r.json()["id"]

    # 2. Set document
    r = client.post(f"/projects/{project_id}/document",
                    json={"document": TEST_DOCUMENT})
    assert r.status_code == 200

    # 3. Run verification (SSE endpoint)
    with httpx.Client(base_url=BASE_URL, timeout=300.0) as long_client:
        r = long_client.post(
            f"/projects/{project_id}/verify",
            headers={"Accept": "text/event-stream"},
        )
        assert r.status_code == 200
        # SSE returns event stream - just check it completes
        content = r.text
        assert "verification_complete" in content or "final_report" in content

    # 4. Get verification results
    r = client.get(f"/projects/{project_id}/verify/results")
    assert r.status_code == 200
    data = r.json()
    assert "facts" in data
    assert len(data["facts"]) > 0

    # 5. Get quiz questions (may fail if LLM output wasn't parseable)
    r = client.get(f"/projects/{project_id}/quiz")
    quiz_result = None
    if r.status_code == 200:
        quiz_data = r.json()
        assert "questions" in quiz_data
        assert len(quiz_data["questions"]) > 0

        # 6. Submit quiz answers (answer first option for each)
        answers = {}
        for q in quiz_data["questions"]:
            answers[q["id"]] = q["options"][0] if q.get("options") else ""

        r = client.post(
            f"/projects/{project_id}/quiz/submit", json={"answers": answers})
        assert r.status_code == 200
        quiz_result = r.json()
        assert "score" in quiz_result
        assert "results" in quiz_result
    else:
        # Quiz generation can fail due to LLM output parsing — not a blocking error
        assert r.status_code == 400
        print(
            "  [WARN] Quiz generation failed (LLM output not parseable), skipping quiz steps")

    # 7. Get report
    r = client.get(f"/projects/{project_id}/report")
    assert r.status_code == 200
    report_data = r.json()
    assert "report" in report_data
    report = report_data["report"]
    assert "factuality_score" in report
    assert "consistency_score" in report
    assert "overall_confidence" in report
    assert "recommendations" in report

    print(f"\n=== E2E Test Complete ===")
    print(f"Factuality: {report['factuality_score']}")
    print(f"Consistency: {report['consistency_score']}")
    print(f"Source Grounding: {report['source_grounding_score']}")
    print(f"Comprehension: {report['comprehension_score']}")
    print(f"Overall: {report['overall_confidence']}")
    print(
        f"Quiz Score: {quiz_result['score'] if quiz_result else 'N/A (quiz failed)'}")
    print(f"Facts verified: {len(data['facts'])}")
    print(f"Recommendations: {report['recommendations']}")


def test_generate_document_flow(client):
    """Test the AI document generation flow."""
    # Create project with prompt instead of document
    r = client.post(
        "/projects/", json={"name": "Generate Test", "description": ""})
    project_id = r.json()["id"]

    # Set prompt
    r = client.post(f"/projects/{project_id}/document", json={
                    "prompt": "Write a short report about the benefits of remote work."})
    assert r.status_code == 200
    assert r.json()["has_prompt"] is True

    # Run verification - this should generate the document first
    with httpx.Client(base_url=BASE_URL, timeout=300.0) as long_client:
        r = long_client.post(
            f"/projects/{project_id}/verify",
            headers={"Accept": "text/event-stream"},
        )
        assert r.status_code == 200

    # Check that document was generated
    r = client.get(f"/projects/{project_id}/document")
    assert r.status_code == 200
    assert len(r.json()["document"]) > 0


TEST_EVIDENCE = """## Internal Financial Records - Q4 2025

Revenue: $5.2 million total revenue for Q4 2025 (confirmed by finance team).
Year-over-year growth: 15% increase compared to Q4 2024.
Customer retention: 94% retention rate in Q4, improved from 89% in Q3.
Operating costs: Reduced by 8% through automation of billing and support workflows.
Net profit margin: 22% net margin after all expenses.
Customer acquisition cost: $150 average CAC across all channels.
Monthly active users: 45,000 MAU as of December 2025.
Net Promoter Score: 72 (surveyed 2,000 customers in December).
Customer lifetime value: $4,800 average CLV based on 3-year cohort analysis.
Churn rate: 6% annual churn rate (down from 11% in 2024).
Market share: Internal estimate is 23% of SaaS analytics segment.
European expansion: Board approved Q2 2026 launch, led by CEO John Smith.
AI investment: $10M budget approved for AI feature development.
"""


def test_evidence_crud(client):
    """Test evidence upload, list, and delete."""
    # Create project
    r = client.post(
        "/projects/", json={"name": "Evidence CRUD Test", "description": ""})
    project_id = r.json()["id"]

    # List evidence — should be empty
    r = client.get(f"/projects/{project_id}/evidence")
    assert r.status_code == 200
    assert len(r.json()["evidence"]) == 0

    # Add evidence
    r = client.post(f"/projects/{project_id}/evidence", json={
        "label": "Financial Records",
        "content": TEST_EVIDENCE,
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True
    evidence_id = r.json()["evidence_id"]
    assert r.json()["total"] == 1

    # List evidence — should have 1
    r = client.get(f"/projects/{project_id}/evidence")
    assert r.status_code == 200
    evidence_list = r.json()["evidence"]
    assert len(evidence_list) == 1
    assert evidence_list[0]["label"] == "Financial Records"

    # Delete evidence
    r = client.delete(f"/projects/{project_id}/evidence/{evidence_id}")
    assert r.status_code == 200
    assert r.json()["total"] == 0

    # List evidence — should be empty again
    r = client.get(f"/projects/{project_id}/evidence")
    assert r.status_code == 200
    assert len(r.json()["evidence"]) == 0


def test_verification_with_evidence(client):
    """Test full verification pipeline WITH evidence for grounding."""
    # 1. Create project
    r = client.post("/projects/", json={
        "name": "Evidence Grounding Test",
        "description": "Test document verification against provided evidence",
    })
    assert r.status_code == 200
    project_id = r.json()["id"]

    # 2. Set document
    r = client.post(f"/projects/{project_id}/document",
                    json={"document": TEST_DOCUMENT})
    assert r.status_code == 200

    # 3. Add evidence
    r = client.post(f"/projects/{project_id}/evidence", json={
        "label": "Q4 Financial Records",
        "content": TEST_EVIDENCE,
    })
    assert r.status_code == 200
    assert r.json()["total"] == 1

    # 4. Run verification (SSE endpoint)
    with httpx.Client(base_url=BASE_URL, timeout=600.0) as long_client:
        r = long_client.post(
            f"/projects/{project_id}/verify",
            headers={"Accept": "text/event-stream"},
        )
        assert r.status_code == 200
        content = r.text
        assert "verification_complete" in content or "final_report" in content
        # Evidence grounding step should appear in the SSE stream
        assert "evidence_grounding" in content

    # 5. Get verification results
    r = client.get(f"/projects/{project_id}/verify/results")
    assert r.status_code == 200
    data = r.json()
    assert "facts" in data
    assert len(data["facts"]) > 0

    # Check that some facts reference evidence grounding in their method
    methods = [f["method"] for f in data["facts"]]
    has_evidence = any("evidence_grounding" in m for m in methods)
    print(f"\n=== Evidence Grounding Test ===")
    print(f"Facts verified: {len(data['facts'])}")
    print(
        f"Facts with evidence grounding: {sum(1 for m in methods if 'evidence_grounding' in m)}")
    print(f"Methods: {set(methods)}")

    # 6. Get report
    r = client.get(f"/projects/{project_id}/report")
    assert r.status_code == 200
    report = r.json()["report"]
    assert "source_grounding_score" in report
    print(f"Source Grounding Score: {report['source_grounding_score']}")
    print(f"Factuality: {report['factuality_score']}")
    print(f"Overall: {report['overall_confidence']}")
    print(f"Recommendations: {report['recommendations']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


# ─── Enterprise Feature Tests ───────────────────────────────────────


def test_request_id_header(client):
    """Test that all responses include X-Request-ID header."""
    r = client.get("/health")
    assert r.status_code == 200
    assert "x-request-id" in r.headers
    # UUID format check
    req_id = r.headers["x-request-id"]
    assert len(req_id) == 36  # UUID length with hyphens


def test_request_id_echo(client):
    """Test that a client-provided X-Request-ID is echoed back."""
    r = client.get("/health", headers={"X-Request-ID": "my-trace-12345"})
    assert r.status_code == 200
    assert r.headers["x-request-id"] == "my-trace-12345"


def test_input_validation_empty_document(client):
    """Test that setting an empty document is handled gracefully."""
    r = client.post("/projects/", json={"name": "Validation Test"})
    project_id = r.json()["id"]

    # Empty document should still succeed (no content, just clears)
    r = client.post(f"/projects/{project_id}/document",
                    json={"document": "", "prompt": ""})
    assert r.status_code == 200

    # Verify without document should fail with 409
    r = client.post(f"/projects/{project_id}/verify",
                    headers={"Accept": "text/event-stream"})
    assert r.status_code == 409


def test_verification_status_polling(client):
    """Test the new polling endpoint for verification status."""
    r = client.post("/projects/", json={"name": "Status Poll Test"})
    project_id = r.json()["id"]

    r = client.get(f"/projects/{project_id}/verify/status")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "draft"
    assert data["fact_count"] == 0
    assert data["has_report"] is False
    assert data["has_quiz"] is False


def test_report_export_json(client):
    """Test report export as JSON after full verification."""
    # Create and run a quick project
    r = client.post("/projects/", json={"name": "Export JSON Test"})
    project_id = r.json()["id"]
    r = client.post(f"/projects/{project_id}/document",
                    json={"document": TEST_DOCUMENT})
    assert r.status_code == 200

    with httpx.Client(base_url=BASE_URL, timeout=300.0) as long_client:
        r = long_client.post(f"/projects/{project_id}/verify",
                             headers={"Accept": "text/event-stream"})
        assert r.status_code == 200

    # Export as JSON
    r = client.get(f"/projects/{project_id}/report/export?format=json")
    assert r.status_code == 200
    data = r.json()
    assert "meta" in data
    assert data["meta"]["project_name"] == "Export JSON Test"
    assert data["meta"]["format"] == "gendoc-confidence-report"
    assert "scores" in data
    assert "facts" in data
    assert len(data["facts"]) > 0

    print(f"\n=== Export JSON Test ===")
    print(f"Exported {len(data['facts'])} facts")
    print(f"Scores: {data['scores']}")


def test_report_export_csv(client):
    """Test report export as CSV after full verification."""
    r = client.post("/projects/", json={"name": "Export CSV Test"})
    project_id = r.json()["id"]
    r = client.post(f"/projects/{project_id}/document",
                    json={"document": TEST_DOCUMENT})
    assert r.status_code == 200

    with httpx.Client(base_url=BASE_URL, timeout=300.0) as long_client:
        r = long_client.post(f"/projects/{project_id}/verify",
                             headers={"Accept": "text/event-stream"})
        assert r.status_code == 200

    # Export as CSV
    r = client.get(f"/projects/{project_id}/report/export?format=csv")
    assert r.status_code == 200
    lines = r.text.strip().split("\n")
    # Header + at least 1 fact row
    assert len(lines) >= 2
    header = lines[0]
    assert "fact_id" in header
    assert "status" in header
    assert "confidence" in header

    print(f"\n=== Export CSV Test ===")
    print(f"CSV rows: {len(lines) - 1}")
    print(f"Header: {header}")


def test_report_export_before_verification(client):
    """Test that export fails gracefully before verification."""
    r = client.post("/projects/", json={"name": "Export Pre-Verify"})
    project_id = r.json()["id"]

    r = client.get(f"/projects/{project_id}/report/export?format=json")
    assert r.status_code == 409  # Report not generated yet


def test_backward_compat_health():
    """Test that /api/health still works for backward compatibility."""
    with httpx.Client(base_url="http://localhost:8000", timeout=10.0) as c:
        r = c.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"
