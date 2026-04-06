"""Journal routes -- list journal dates and view individual entries."""

from __future__ import annotations

import markdown
from fastapi import APIRouter, HTTPException, Request

from project_manager_agent.web.app import ServiceDep, make_context, templates

router = APIRouter()


@router.get("/journal")
async def journal_list(request: Request, project_id: int, svc: ServiceDep):
    """List available journal dates (newest first)."""
    dates = svc.list_journal_dates()
    return templates.TemplateResponse(
        "journal_list.html",
        make_context(request, svc, project_id, "journal", dates=dates),
    )


@router.get("/journal/{date}")
async def journal_detail(request: Request, project_id: int, date: str, svc: ServiceDep):
    """Render a single journal entry as HTML."""
    content_md = svc.get_journal_content(date)
    if content_md is None:
        raise HTTPException(status_code=404, detail=f"No journal entry for {date}")

    content_html = markdown.markdown(content_md)

    return templates.TemplateResponse(
        "journal_detail.html",
        make_context(
            request,
            svc,
            project_id,
            "journal",
            date=date,
            content_html=content_html,
        ),
    )
