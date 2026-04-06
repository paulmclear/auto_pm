"""
Structured Report Schema
========================
Pydantic model for structured report output. The reporter agent produces this
as JSON alongside the markdown report, enabling programmatic consumption of
report data by dashboards and APIs.
"""

import datetime as dt
from typing import Literal, Optional

from pydantic import BaseModel, Field


class MilestoneStatus(BaseModel):
    """Status of a single milestone."""

    milestone_id: int
    name: str
    planned_date: dt.date
    forecast_date: dt.date
    actual_date: Optional[dt.date] = None
    status: Literal["pending", "achieved", "missed"]


class TaskStatsByStatus(BaseModel):
    """Task counts broken down by status."""

    complete: int = 0
    in_progress: int = 0
    not_started: int = 0
    blocked: int = 0


class TaskStatsByPhase(BaseModel):
    """Task counts for a single phase."""

    phase_id: int
    phase_name: str
    total: int = 0
    complete: int = 0
    in_progress: int = 0
    not_started: int = 0
    blocked: int = 0


class TaskStatistics(BaseModel):
    """Aggregate task statistics."""

    total: int = 0
    by_status: TaskStatsByStatus = Field(default_factory=TaskStatsByStatus)
    by_phase: list[TaskStatsByPhase] = Field(default_factory=list)


class OverdueTask(BaseModel):
    """Summary of an overdue task."""

    task_id: int
    description: str
    owner: str
    due_date: dt.date
    days_overdue: int


class RaidHighlight(BaseModel):
    """A notable risk, issue, assumption, or decision."""

    raid_id: int
    type: Literal["risk", "assumption", "issue", "decision"]
    title: str
    owner: str
    severity_or_impact: Optional[str] = None
    status: str


class Recommendation(BaseModel):
    """A recommended action from the report."""

    summary: str
    priority: Literal["high", "medium", "low"]
    related_item: Optional[str] = None  # e.g. "Task 5", "Risk R3"


class StructuredReport(BaseModel):
    """
    Full structured report output.

    Produced alongside the markdown report for programmatic consumption.
    """

    report_date: dt.date
    project_name: str
    executive_summary: str
    rag_status: Literal["green", "amber", "red"]
    rag_reason: str
    milestone_statuses: list[MilestoneStatus] = Field(default_factory=list)
    task_statistics: TaskStatistics = Field(default_factory=TaskStatistics)
    overdue_tasks: list[OverdueTask] = Field(default_factory=list)
    raid_highlights: list[RaidHighlight] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
