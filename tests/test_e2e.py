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

BASE_URL = "http://localhost:8000/api"
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
    """Test that the backend is healthy."""
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"


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

    # 5. Get quiz questions
    r = client.get(f"/projects/{project_id}/quiz")
    assert r.status_code == 200
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
    print(f"Quiz Score: {quiz_result['score']}")
    print(f"Facts verified: {len(data['facts'])}")
    print(f"Questions: {len(quiz_data['questions'])}")
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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
