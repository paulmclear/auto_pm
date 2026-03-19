"""Report routes — list reports and view individual entries."""

from __future__ import annotations

from pathlib import Path

import markdown
from fastapi import APIRouter, HTTPException, Request

from project_manager_agent.web.app import ServiceDep, templates

router = APIRouter()

REPORTS_DIR = Path(__file__).resolve().parents[4] / "data" / "reports"


@router.get("/reports")
async def reports_list(request: Request, svc: ServiceDep):
    """List available reports (newest first)."""
    files = (
        sorted(REPORTS_DIR.glob("*.md"), reverse=True) if REPORTS_DIR.exists() else []
    )
    dates = [f.stem for f in files]
    return templates.TemplateResponse(
        "reports_list.html",
        {"request": request, "dates": dates},
    )


@router.get("/reports/{date}")
async def report_detail(request: Request, date: str, svc: ServiceDep):
    """Render a single report as HTML."""
    filepath = REPORTS_DIR / f"{date}.md"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"No report for {date}")

    content_md = filepath.read_text(encoding="utf-8")
    content_html = markdown.markdown(content_md)

    return templates.TemplateResponse(
        "reports_detail.html",
        {"request": request, "date": date, "content_html": content_html},
    )
