"""Journal routes — list journal dates and view individual entries."""

from __future__ import annotations

from pathlib import Path

import markdown
from fastapi import APIRouter, HTTPException, Request

from project_manager_agent.web.app import ServiceDep, templates

router = APIRouter()

JOURNAL_DIR = Path(__file__).resolve().parents[4] / "data" / "journal"


@router.get("/journal")
async def journal_list(request: Request, svc: ServiceDep):
    """List available journal dates (newest first)."""
    files = (
        sorted(JOURNAL_DIR.glob("*.md"), reverse=True) if JOURNAL_DIR.exists() else []
    )
    dates = [f.stem for f in files]
    return templates.TemplateResponse(
        "journal_list.html",
        {"request": request, "dates": dates},
    )


@router.get("/journal/{date}")
async def journal_detail(request: Request, date: str, svc: ServiceDep):
    """Render a single journal entry as HTML."""
    filepath = JOURNAL_DIR / f"{date}.md"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"No journal entry for {date}")

    content_md = filepath.read_text(encoding="utf-8")
    content_html = markdown.markdown(content_md)

    return templates.TemplateResponse(
        "journal_detail.html",
        {"request": request, "date": date, "content_html": content_html},
    )
