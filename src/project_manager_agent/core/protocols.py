"""Protocol interfaces for all repository contracts.

Each protocol defines the public API that any implementation (JSON file-based,
SQL-backed, etc.) must satisfy.  All methods return typed domain objects, not
raw dicts.
"""

from __future__ import annotations

import datetime as dt
from typing import Optional, Protocol

from project_manager_agent.core.models import (
    Action,
    ActionStatus,
    Message,
    MilestoneStatus,
    Project,
    RagStatus,
    RaidItem,
    Task,
    TaskStatus,
)


class TaskRepository(Protocol):
    """Contract for task persistence."""

    def read(self) -> list[Task]: ...

    def update_status(self, task_id: int, status: TaskStatus) -> None: ...

    def update_blocking(
        self,
        task_id: int,
        blocked_reason: Optional[str],
        depends_on: Optional[list[int]],
    ) -> None: ...


class ProjectRepository(Protocol):
    """Contract for project-plan persistence."""

    def read(self) -> Project: ...

    def update_health(
        self,
        rag_status: Optional[RagStatus],
        rag_reason: Optional[str],
        forecast_end: Optional[dt.date],
    ) -> None: ...

    def update_milestone(
        self,
        milestone_id: int,
        status: Optional[MilestoneStatus],
        forecast_date: Optional[dt.date],
        actual_date: Optional[dt.date],
    ) -> None: ...


class RaidRepository(Protocol):
    """Contract for RAID-log persistence."""

    def read(self) -> list[RaidItem]: ...

    def add(self, item: RaidItem) -> int: ...

    def update(self, raid_id: int, fields: dict) -> None: ...


class ActionRepository(Protocol):
    """Contract for action-item persistence."""

    def read(self) -> list[Action]: ...

    def add(self, action: Action) -> int: ...

    def update_status(self, action_id: int, status: ActionStatus) -> None: ...


class MessageRepository(Protocol):
    """Contract for inbox / outbox message persistence."""

    def send(self, owner_name: str, owner_email: str, message: str) -> None: ...

    def read_inbox(self) -> list[Message]: ...

    def read_outbox(self) -> list[Message]: ...


class JournalRepository(Protocol):
    """Contract for daily journal persistence."""

    def read_last(self) -> Optional[str]: ...

    def write(self, section: str, content: str) -> None: ...
