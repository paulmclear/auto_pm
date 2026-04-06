"""FastAPI application factory for the Project Manager web UI."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Annotated

from fastapi import Cookie, Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
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

    # Root redirect: cookie-stored project or first available
    @app.get("/")
    async def root_redirect(
        selected_project_id: str | None = Cookie(default=None),
    ):
        if selected_project_id and selected_project_id.isdigit():
            return RedirectResponse(
                url=f"/projects/{selected_project_id}/", status_code=302
            )
        # Fall back to first project in DB
        svc = ProjectService()
        try:
            projects = svc.list_all_projects()
        finally:
            svc.close()
        if projects:
            return RedirectResponse(
                url=f"/projects/{projects[0]['id']}/", status_code=302
            )
        return RedirectResponse(url="/static/style.css", status_code=302)

    # Project-scoped route modules
    from project_manager_agent.web.routes import (
        dashboard,
        journal,
        raid,
        reports,
        tasks,
    )

    app.include_router(dashboard.router, prefix="/projects/{project_id}")
    app.include_router(tasks.router, prefix="/projects/{project_id}")
    app.include_router(raid.router, prefix="/projects/{project_id}")
    app.include_router(journal.router, prefix="/projects/{project_id}")
    app.include_router(reports.router, prefix="/projects/{project_id}")

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
