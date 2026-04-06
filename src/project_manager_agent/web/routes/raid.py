"""RAID log routes -- view all RAID entries."""

from __future__ import annotations

from fastapi import APIRouter, Request

from project_manager_agent.web.app import ServiceDep, make_context, templates

router = APIRouter()


@router.get("/raid")
async def raid_list(request: Request, project_id: int, svc: ServiceDep):
    """RAID log entries."""
    items = svc.read_raid()
    return templates.TemplateResponse(
        "raid.html",
        make_context(request, svc, project_id, "raid", items=items),
    )
