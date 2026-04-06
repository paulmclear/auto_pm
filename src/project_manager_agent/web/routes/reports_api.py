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


@router.get("/trends")
async def get_trends(project_id: int = Query(...)):
    """Return trend data across all report dates for charting."""
    svc = ProjectService(project_id=project_id)
    try:
        reports = svc.list_report_jsons()
    finally:
        svc.close()

    dates = []
    pct_complete = []
    open_risks = []
    overdue_count = []

    for r in reports:
        dates.append(r.get("report_date", ""))
        stats = r.get("task_statistics", {})
        total = stats.get("total", 0)
        by_status = stats.get("by_status", {})
        complete = by_status.get("complete", 0)
        pct_complete.append(round(complete / total * 100, 1) if total > 0 else 0)
        open_risks.append(
            sum(
                1
                for h in r.get("raid_highlights", [])
                if h.get("type") == "risk"
                and h.get("status", "").lower() not in ("closed", "resolved")
            )
        )
        overdue_count.append(len(r.get("overdue_tasks", [])))

    return {
        "dates": dates,
        "pct_complete": pct_complete,
        "open_risks": open_risks,
        "overdue_count": overdue_count,
    }


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
