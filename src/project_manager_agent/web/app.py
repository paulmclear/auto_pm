"""FastAPI application factory for the Project Manager web UI."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from project_manager_agent.core.db.engine import create_tables
from project_manager_agent.core.services import ProjectService

WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


async def get_service(project_id: int) -> AsyncGenerator[ProjectService, None]:
    """FastAPI dependency that yields a project-scoped ProjectService."""
    svc = ProjectService(project_id=project_id)
    try:
        yield svc
    finally:
        svc.close()


ServiceDep = Annotated[ProjectService, Depends(get_service)]


def make_context(
    request: Request,
    svc: ProjectService,
    project_id: int,
    active_page: str,
    **extra,
) -> dict:
    """Build common template context with project switcher data."""
    return {
        "request": request,
        "active_page": active_page,
        "project_id": project_id,
        "projects": svc.list_all_projects(),
        "url_prefix": f"/projects/{project_id}",
        **extra,
    }


def create_app() -> FastAPI:
    """Application factory -- creates and configures the FastAPI instance."""
    create_tables()

    app = FastAPI(title="Project Manager", docs_url=None, redoc_url=None)

    # Static files
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Portfolio dashboard — shows all projects as card grid
    @app.get("/")
    async def portfolio(request: Request):
        svc = ProjectService()
        try:
            summaries = svc.list_project_summaries()
        finally:
            svc.close()
        return templates.TemplateResponse(
            "portfolio.html",
            {
                "request": request,
                "projects": summaries,
                "active_page": "portfolio",
            },
        )

    # Project CRUD API (not project-scoped)
    from project_manager_agent.web.routes import messages_api, projects_api, reports_api

    app.include_router(projects_api.router)
    app.include_router(messages_api.router)
    app.include_router(reports_api.router)

    # Project-scoped route modules
    from project_manager_agent.web.routes import (
        dashboard,
        journal,
        messages,
        raid,
        reports,
        tasks,
    )

    app.include_router(dashboard.router, prefix="/projects/{project_id}")
    app.include_router(tasks.router, prefix="/projects/{project_id}")
    app.include_router(raid.router, prefix="/projects/{project_id}")
    app.include_router(journal.router, prefix="/projects/{project_id}")
    app.include_router(reports.router, prefix="/projects/{project_id}")
    app.include_router(messages.router, prefix="/projects/{project_id}")

    # Middleware: persist selected project in cookie
    @app.middleware("http")
    async def set_project_cookie(request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path.startswith("/projects/"):
            parts = path.split("/")
            if len(parts) >= 3 and parts[2].isdigit():
                response.set_cookie(
                    "selected_project_id",
                    parts[2],
                    max_age=60 * 60 * 24 * 365,
                )
        return response

    return app
