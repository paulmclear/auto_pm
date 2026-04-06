"""Messages routes -- email-client layout with message list and reading pane."""

from __future__ import annotations

from fastapi import APIRouter, Request

from project_manager_agent.core.date_utils import REFERENCE_DATE
from project_manager_agent.web.app import ServiceDep, make_context, templates

router = APIRouter()


@router.get("/messages")
async def messages(request: Request, project_id: int, svc: ServiceDep):
    """Email-client message view."""
    return templates.TemplateResponse(
        "messages.html",
        make_context(
            request,
            svc,
            project_id,
            "messages",
            reference_date=REFERENCE_DATE.isoformat(),
        ),
    )
