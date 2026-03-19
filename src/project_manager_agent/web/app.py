"""FastAPI application factory for the Project Manager web UI."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from project_manager_agent.core.db.engine import create_tables
from project_manager_agent.core.services import ProjectService

WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


async def get_service() -> AsyncGenerator[ProjectService, None]:
    """FastAPI dependency that yields a ProjectService and closes it after the request."""
    svc = ProjectService()
    try:
        yield svc
    finally:
        svc.close()


ServiceDep = Annotated[ProjectService, Depends(get_service)]


def create_app() -> FastAPI:
    """Application factory — creates and configures the FastAPI instance."""
    create_tables()

    app = FastAPI(title="Project Manager", docs_url=None, redoc_url=None)

    # Static files
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Route modules
    from project_manager_agent.web.routes import (
        dashboard,
        journal,
        raid,
        reports,
        tasks,
    )

    app.include_router(dashboard.router)
    app.include_router(tasks.router)
    app.include_router(raid.router)
    app.include_router(journal.router)
    app.include_router(reports.router)

    return app
