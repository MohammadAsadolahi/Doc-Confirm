from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.store import get_session

router = APIRouter()


@router.get("/projects/{project_id}/report")
async def get_report(project_id: UUID):
    session = get_session(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project not found")
    if not session.report:
        return {"status": "pending"}

    return {
        "report": session.report.model_dump(mode="json"),
        "document": session.document,
        "verification": session.verification_result.model_dump(mode="json") if session.verification_result else None,
    }


@router.get("/projects/{project_id}/report/export")
async def export_report(
    project_id: UUID,
    export_format: str = Query("json", alias="format", pattern="^(json|csv)$"),
):
    """Export the verification report as JSON or CSV."""
    session = get_session(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project not found")
    if not session.report:
        raise HTTPException(status_code=409, detail="Report not generated yet")

    timestamp = datetime.now(timezone.utc).isoformat()
    filename_base = f"gendoc-report-{project_id}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"

    if export_format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "fact_id", "fact_text", "category", "status",
            "confidence", "method", "explanation",
        ])
        if session.verification_result:
            for fv in session.verification_result.facts:
                writer.writerow([
                    fv.fact.id,
                    fv.fact.text,
                    fv.fact.category.value,
                    fv.status.value,
                    round(fv.confidence, 4),
                    fv.method,
                    fv.explanation,
                ])
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename_base}.csv"'},
        )

    # JSON export — full structured report with metadata
    report_data = session.report.model_dump(mode="json")
    export_payload = {
        "meta": {
            "project_id": str(project_id),
            "project_name": session.name,
            "exported_at": timestamp,
            "version": "1.0.0",
            "format": "gendoc-confidence-report",
        },
        "scores": {
            "factuality": report_data.get("factuality_score"),
            "consistency": report_data.get("consistency_score"),
            "source_grounding": report_data.get("source_grounding_score"),
            "comprehension": report_data.get("comprehension_score"),
            "overall_confidence": report_data.get("overall_confidence"),
        },
        "risk_areas": report_data.get("risk_areas", []),
        "recommendations": report_data.get("recommendations", []),
        "facts": [],
        "document": session.document,
    }
    if session.verification_result:
        export_payload["facts"] = [
            {
                "id": fv.fact.id,
                "text": fv.fact.text,
                "category": fv.fact.category.value,
                "status": fv.status.value,
                "confidence": round(fv.confidence, 4),
                "method": fv.method,
                "explanation": fv.explanation,
                "evidence": [e.model_dump(mode="json") for e in fv.evidence],
            }
            for fv in session.verification_result.facts
        ]

    import json as json_mod
    content = json_mod.dumps(export_payload, indent=2, default=str)
    return StreamingResponse(
        io.BytesIO(content.encode()),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename_base}.json"'},
    )
