"""Report routes -- list reports and view individual entries."""

from __future__ import annotations

import markdown
from fastapi import APIRouter, HTTPException, Request

from project_manager_agent.web.app import ServiceDep, make_context, templates

router = APIRouter()


@router.get("/reports")
async def reports_list(request: Request, project_id: int, svc: ServiceDep):
    """List available reports (newest first)."""
    dates = svc.list_report_names()
    return templates.TemplateResponse(
        "reports_list.html",
        make_context(request, svc, project_id, "reports", dates=dates),
    )


@router.get("/reports/{date}")
async def report_detail(request: Request, project_id: int, date: str, svc: ServiceDep):
    """Render a single report as HTML."""
    content_md = svc.get_report_content(date)
    if content_md is None:
        raise HTTPException(status_code=404, detail=f"No report for {date}")

    content_html = markdown.markdown(content_md)

    return templates.TemplateResponse(
        "reports_detail.html",
        make_context(
            request,
            svc,
            project_id,
            "reports",
            date=date,
            content_html=content_html,
        ),
    )
