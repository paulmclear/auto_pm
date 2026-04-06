"""Dashboard routes -- project summary, RAG status, milestones, task counts."""

from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Request

from project_manager_agent.web.app import ServiceDep, make_context, templates

router = APIRouter()


@router.get("/")
async def dashboard(request: Request, project_id: int, svc: ServiceDep):
    """Project summary dashboard."""
    project = svc.read_project()
    tasks = svc.read_tasks()

    status_counts = Counter(t.status for t in tasks)

    return templates.TemplateResponse(
        "dashboard.html",
        make_context(
            request,
            svc,
            project_id,
            "dashboard",
            project=project,
            task_counts={
                "total": len(tasks),
                "not_started": status_counts.get("not_started", 0),
                "in_progress": status_counts.get("in_progress", 0),
                "complete": status_counts.get("complete", 0),
                "blocked": status_counts.get("blocked", 0),
            },
        ),
    )
