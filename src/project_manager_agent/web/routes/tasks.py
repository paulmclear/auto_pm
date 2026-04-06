"""Task routes -- list all tasks with status information."""

from __future__ import annotations

from fastapi import APIRouter, Request

from project_manager_agent.web.app import ServiceDep, make_context, templates

router = APIRouter()


@router.get("/tasks")
async def task_list(request: Request, project_id: int, svc: ServiceDep):
    """All tasks with status info."""
    tasks = svc.read_tasks()
    return templates.TemplateResponse(
        "tasks.html",
        make_context(request, svc, project_id, "tasks", tasks=tasks),
    )
