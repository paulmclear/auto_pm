"""API routes for structured report data."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query

from project_manager_agent.core.services import ProjectService

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("")
async def list_reports(project_id: int = Query(...)):
    """Return list of available report dates (newest first)."""
    svc = ProjectService(project_id=project_id)
    try:
        names = svc.list_report_names()
    finally:
        svc.close()

    dates = []
    for name in names:
        # Report stems look like "2026-03-20-status-report"
        date_str = name[:10] if len(name) >= 10 else name
        dates.append({"date": date_str, "name": name})

    return {"reports": dates}


@router.get("/{date}")
async def get_report(date: str, project_id: int = Query(...)):
    """Return structured JSON for a given report date."""
    svc = ProjectService(project_id=project_id)
    try:
        content = svc.get_report_json(date)
    finally:
        svc.close()

    if content is None:
        raise HTTPException(
            status_code=404,
            detail=f"No structured report found for {date}",
        )

    return json.loads(content)
