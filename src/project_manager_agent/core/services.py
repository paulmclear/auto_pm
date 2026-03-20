"""ProjectService — thin facade over all repositories.

Owns the SQLAlchemy session lifecycle and exposes simple delegation
methods so callers never need to know about individual repositories.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from project_manager_agent.core.db.engine import SessionFactory
from project_manager_agent.core.db.repositories import (
    FileJournalRepository,
    SqliteActionRepository,
    SqliteMessageRepository,
    SqliteProjectRepository,
    SqliteRaidRepository,
    SqliteTaskRepository,
)
from project_manager_agent.core.models import (
    Action,
    ActionStatus,
    MilestoneStatus,
    Project,
    RagStatus,
    RaidItem,
    Task,
    TaskStatus,
)

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
JOURNAL_DIR = DATA_DIR / "journal"
REPORTS_DIR = DATA_DIR / "reports"


class ProjectService:
    """Facade that centralises access to every repository.

    Usage::

        svc = ProjectService()
        try:
            tasks = svc.read_tasks()
            ...
        finally:
            svc.close()
    """

    def __init__(self, session: Optional[Session] = None) -> None:
        self._owns_session = session is None
        self._session: Session = session or SessionFactory()

        self.tasks = SqliteTaskRepository(self._session)
        self.project = SqliteProjectRepository(self._session)
        self.raid = SqliteRaidRepository(self._session)
        self.actions = SqliteActionRepository(self._session)
        self.messages = SqliteMessageRepository(self._session)
        self.journal = FileJournalRepository(JOURNAL_DIR)

    # -- Tasks ---------------------------------------------------------------

    def read_tasks(self) -> list[Task]:
        return self.tasks.read()

    def update_task_status(self, task_id: int, status: TaskStatus) -> None:
        self.tasks.update_status(task_id, status)

    def update_task_blocking(
        self,
        task_id: int,
        blocked_reason: Optional[str],
        depends_on: Optional[list[int]],
    ) -> None:
        self.tasks.update_blocking(task_id, blocked_reason, depends_on)

    # -- Project -------------------------------------------------------------

    def read_project(self) -> Project:
        return self.project.read()

    def update_health(
        self,
        rag_status: Optional[RagStatus] = None,
        rag_reason: Optional[str] = None,
        forecast_end: Optional[dt.date] = None,
    ) -> None:
        self.project.update_health(rag_status, rag_reason, forecast_end)

    def update_milestone(
        self,
        milestone_id: int,
        status: Optional[MilestoneStatus] = None,
        forecast_date: Optional[dt.date] = None,
        actual_date: Optional[dt.date] = None,
    ) -> None:
        self.project.update_milestone(milestone_id, status, forecast_date, actual_date)

    # -- RAID ----------------------------------------------------------------

    def read_raid(self) -> list[RaidItem]:
        return self.raid.read()

    def add_raid(self, item: RaidItem) -> int:
        return self.raid.add(item)

    def update_raid(self, raid_id: int, fields: dict) -> None:
        self.raid.update(raid_id, fields)

    # -- Actions -------------------------------------------------------------

    def read_actions(self) -> list[Action]:
        return self.actions.read()

    def add_action(self, action: Action) -> int:
        return self.actions.add(action)

    def update_action_status(self, action_id: int, status: ActionStatus) -> None:
        self.actions.update_status(action_id, status)

    # -- Messages ------------------------------------------------------------

    def send_message(
        self,
        owner_name: str,
        owner_email: str,
        message: str,
        task_id: Optional[int] = None,
    ) -> None:
        self.messages.send(owner_name, owner_email, message, task_id=task_id)

    def read_inbox(self) -> list:
        return self.messages.read_inbox()

    def read_outbox(self) -> list:
        return self.messages.read_outbox()

    # -- Journal -------------------------------------------------------------

    def has_today_journal(self) -> bool:
        """Check whether a journal entry already exists for today's date."""
        return self.journal.has_today_entry()

    def read_last_journal(self) -> Optional[str]:
        return self.journal.read_last()

    def read_journals_range(self, start: dt.date, end: dt.date) -> dict[dt.date, str]:
        """Read all journal entries between start and end (inclusive)."""
        return self.journal.read_range(start, end)

    def write_journal(self, section: str, content: str) -> None:
        self.journal.write(section, content)

    # -- Reports -------------------------------------------------------------

    def list_reports(self) -> list[Path]:
        """Return report file paths sorted by name (oldest first)."""
        if not REPORTS_DIR.exists():
            return []
        return sorted(REPORTS_DIR.glob("*.md"))

    # -- Lifecycle -----------------------------------------------------------

    def close(self) -> None:
        """Close the underlying DB session if we own it."""
        if self._owns_session:
            self._session.close()
