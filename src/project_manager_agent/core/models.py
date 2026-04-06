import json
import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Literal, Optional


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

TaskStatus = Literal["not_started", "in_progress", "complete", "blocked"]
TaskPriority = Literal["high", "medium", "low"]
RagStatus = Literal["green", "amber", "red"]
RaidType = Literal["risk", "assumption", "issue", "decision"]
RaidStatus = Literal["open", "closed", "accepted", "superseded"]
ActionStatus = Literal["open", "complete", "overdue"]
ImpactLevel = Literal["high", "medium", "low"]
MilestoneStatus = Literal["pending", "achieved", "missed"]
MessageDirection = Literal["inbound", "outbound"]


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Task:
    """A single project task."""

    task_id: int
    description: str
    owner_name: str
    owner_email: str
    due_date: dt.date
    status: TaskStatus = "not_started"
    priority: TaskPriority = "medium"
    phase_id: Optional[int] = None
    depends_on: list = field(default_factory=list)  # list of task_ids
    blocked_reason: Optional[str] = None
    external_dependency: Optional[str] = None  # narrative external dep


@dataclass
class Phase:
    """A phase or workstream grouping tasks within the project."""

    phase_id: int
    name: str
    description: str
    planned_start: dt.date
    planned_end: dt.date


@dataclass
class Milestone:
    """A key delivery point that gates on one or more tasks completing."""

    milestone_id: int
    name: str
    description: str
    planned_date: dt.date
    forecast_date: dt.date
    actual_date: Optional[dt.date]
    status: MilestoneStatus
    linked_task_ids: list = field(default_factory=list)


@dataclass
class Project:
    """Top-level project plan including phases, milestones, and RAG status."""

    name: str
    description: str
    objectives: list[str]
    sponsor: str
    project_manager: str
    planned_start: dt.date
    planned_end: dt.date
    actual_start: dt.date
    forecast_end: dt.date
    rag_status: RagStatus
    rag_reason: str
    phases: list[Phase] = field(default_factory=list)
    milestones: list[Milestone] = field(default_factory=list)


@dataclass
class RaidItem:
    """
    A single entry in the RAID log.

    Type-specific fields are Optional — only the relevant subset is populated
    for each type:
      risk:       probability, impact, mitigation, review_date
      assumption: validation_method, validation_date, validated_by
      issue:      severity, resolution, resolved_date
      decision:   rationale, decided_by, decision_date, alternatives_considered
    """

    raid_id: int
    type: RaidType
    title: str
    description: str
    owner: str
    raised_date: dt.date
    status: RaidStatus
    linked_task_ids: list = field(default_factory=list)
    # Risk
    probability: Optional[ImpactLevel] = None
    impact: Optional[ImpactLevel] = None
    mitigation: Optional[str] = None
    review_date: Optional[dt.date] = None
    # Assumption
    validation_method: Optional[str] = None
    validation_date: Optional[dt.date] = None
    validated_by: Optional[str] = None
    # Issue
    severity: Optional[ImpactLevel] = None
    resolution: Optional[str] = None
    resolved_date: Optional[dt.date] = None
    # Decision
    rationale: Optional[str] = None
    decided_by: Optional[str] = None
    decision_date: Optional[dt.date] = None
    alternatives_considered: Optional[str] = None


@dataclass
class Action:
    """An action item arising from a RAID entry or a task."""

    action_id: int
    description: str
    owner_name: str
    owner_email: str
    due_date: dt.date
    status: ActionStatus = "open"
    source_raid_id: Optional[int] = None
    source_task_id: Optional[int] = None


@dataclass
class Message:
    """A single inbox or outbox message."""

    message_id: str
    direction: MessageDirection
    timestamp: str
    owner_name: str
    owner_email: str
    message: str
    sender_name: str
    sender_email: str
    task_id: Optional[int] = None
    is_read: bool = False


# ---------------------------------------------------------------------------
# JSON serialisation helpers
# ---------------------------------------------------------------------------


class JsonSerialiser(json.JSONEncoder):
    """Extends the default JSON encoder to handle dt.date objects."""

    def default(self, o: Any) -> str:
        if isinstance(o, dt.date):
            return o.isoformat()
        return super().default(o)
