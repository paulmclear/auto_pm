"""Task routes — list all tasks with status information."""

from __future__ import annotations

from fastapi import APIRouter, Request

from project_manager_agent.web.app import ServiceDep, templates

router = APIRouter()


@router.get("/tasks")
async def task_list(request: Request, svc: ServiceDep):
    """All tasks with status info."""
    tasks = svc.read_tasks()
    return templates.TemplateResponse(
        "tasks.html",
        {"request": request, "tasks": tasks},
    )
