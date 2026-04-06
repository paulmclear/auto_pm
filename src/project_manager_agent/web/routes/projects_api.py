"""API routes for project CRUD operations."""

from __future__ import annotations

import datetime as dt
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from project_manager_agent.core.services import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    description: str
    objectives: list[str] = []
    sponsor: str
    project_manager: str
    planned_start: dt.date
    planned_end: dt.date


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    objectives: Optional[list[str]] = None
    sponsor: Optional[str] = None
    project_manager: Optional[str] = None
    planned_start: Optional[dt.date] = None
    planned_end: Optional[dt.date] = None
    forecast_end: Optional[dt.date] = None
    rag_status: Optional[str] = None
    rag_reason: Optional[str] = None


@router.post("", status_code=201)
async def create_project(body: ProjectCreate):
    svc = ProjectService()
    try:
        project_id = svc.create_project(
            name=body.name,
            description=body.description,
            objectives=body.objectives,
            sponsor=body.sponsor,
            project_manager=body.project_manager,
            planned_start=body.planned_start,
            planned_end=body.planned_end,
        )
    finally:
        svc.close()
    return {"id": project_id}


@router.put("/{project_id}")
async def update_project(project_id: int, body: ProjectUpdate):
    fields = body.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    svc = ProjectService()
    try:
        svc.update_project(project_id, fields)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        svc.close()
    return {"ok": True}


@router.delete("/{project_id}")
async def archive_project(project_id: int):
    svc = ProjectService()
    try:
        svc.archive_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        svc.close()
    return {"ok": True}
