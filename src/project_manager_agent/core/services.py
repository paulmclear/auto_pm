"""ProjectService — thin facade over all repositories.

Owns the SQLAlchemy session lifecycle and exposes simple delegation
methods so callers never need to know about individual repositories.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Optional

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

    def __init__(
        self,
        session: Optional[Session] = None,
        project_id: Optional[int] = None,
    ) -> None:
        self._owns_session = session is None
        self._session: Session = session or SessionFactory()
        self._project_id = project_id

        self.tasks = SqliteTaskRepository(self._session, project_id=project_id)
        self.project = SqliteProjectRepository(self._session, project_id=project_id)
        self.raid = SqliteRaidRepository(self._session, project_id=project_id)
        self.actions = SqliteActionRepository(self._session, project_id=project_id)
        self.messages = SqliteMessageRepository(self._session, project_id=project_id)
        self.journal = FileJournalRepository(JOURNAL_DIR, project_id=project_id)

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

    # -- Projects (cross-project queries) ------------------------------------

    def list_all_projects(self) -> list[dict]:
        """Return all projects as [{"id": ..., "name": ...}, ...]."""
        from project_manager_agent.core.db.orm import ProjectRow

        rows = (
            self._session.query(ProjectRow.id, ProjectRow.name)
            .order_by(ProjectRow.name)
            .all()
        )
        return [{"id": r.id, "name": r.name} for r in rows]

    # -- Journal (web helpers) -----------------------------------------------

    def list_journal_dates(self) -> list[str]:
        """Return journal date stems (newest first)."""
        d = self.journal._journal_dir
        if not d.exists():
            return []
        return [f.stem for f in sorted(d.glob("*.md"), reverse=True)]

    def get_journal_content(self, date: str) -> str | None:
        """Read a single journal entry by date string. Returns None if missing."""
        filepath = self.journal._journal_dir / f"{date}.md"
        if not filepath.exists():
            return None
        return filepath.read_text(encoding="utf-8")

    # -- Reports -------------------------------------------------------------

    @property
    def _reports_dir(self) -> Path:
        if self._project_id is not None:
            return REPORTS_DIR / str(self._project_id)
        return REPORTS_DIR

    def list_reports(self) -> list[Path]:
        """Return report file paths sorted by name (oldest first)."""
        d = self._reports_dir
        if not d.exists():
            return []
        return sorted(d.glob("*.md"))

    def list_report_names(self) -> list[str]:
        """Return report stems (newest first)."""
        return [r.stem for r in reversed(self.list_reports())]

    def get_report_content(self, name: str) -> str | None:
        """Read a single report by stem. Returns None if missing."""
        filepath = self._reports_dir / f"{name}.md"
        if not filepath.exists():
            return None
        return filepath.read_text(encoding="utf-8")

    # -- Status snapshot -----------------------------------------------------

    def write_status_snapshot(self) -> Path:
        """Write a machine-readable JSON snapshot of current project state.

        The snapshot includes task states, project health, milestone statuses,
        RAID summary, action summary, and key metrics.  Written to
        ``data/status.json`` so external tools can consume it without parsing
        journals or querying the DB directly.
        """
        from project_manager_agent.core.date_utils import REFERENCE_DATE

        project = self.read_project()
        tasks = self.read_tasks()
        raid_items = self.read_raid()
        actions = self.read_actions()

        # Task metrics
        status_counts: dict[str, int] = {}
        overdue_count = 0
        for t in tasks:
            status_counts[t.status] = status_counts.get(t.status, 0) + 1
            if t.due_date < REFERENCE_DATE and t.status != "complete":
                overdue_count += 1

        # Milestone summary
        milestones = []
        for m in project.milestones:
            milestones.append(
                {
                    "milestone_id": m.milestone_id,
                    "name": m.name,
                    "status": m.status,
                    "planned_date": m.planned_date.isoformat(),
                    "forecast_date": m.forecast_date.isoformat(),
                    "actual_date": m.actual_date.isoformat() if m.actual_date else None,
                }
            )

        # RAID summary
        raid_counts: dict[str, dict[str, int]] = {}
        for r in raid_items:
            raid_counts.setdefault(r.type, {"open": 0, "closed": 0})
            if r.status == "open":
                raid_counts[r.type]["open"] += 1
            else:
                raid_counts[r.type]["closed"] += 1

        # Action summary
        action_status_counts: dict[str, int] = {}
        for a in actions:
            action_status_counts[a.status] = action_status_counts.get(a.status, 0) + 1

        # Task details
        task_list = []
        for t in tasks:
            task_list.append(
                {
                    "task_id": t.task_id,
                    "description": t.description,
                    "owner_name": t.owner_name,
                    "status": t.status,
                    "priority": t.priority,
                    "due_date": t.due_date.isoformat(),
                    "blocked_reason": t.blocked_reason,
                    "depends_on": t.depends_on,
                }
            )

        snapshot: dict[str, Any] = {
            "reference_date": REFERENCE_DATE.isoformat(),
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "project": {
                "name": project.name,
                "rag_status": project.rag_status,
                "rag_reason": project.rag_reason,
                "planned_end": project.planned_end.isoformat(),
                "forecast_end": project.forecast_end.isoformat(),
                "sponsor": project.sponsor,
                "project_manager": project.project_manager,
            },
            "metrics": {
                "total_tasks": len(tasks),
                "tasks_by_status": status_counts,
                "overdue_tasks": overdue_count,
                "total_raid_items": len(raid_items),
                "raid_by_type": raid_counts,
                "total_actions": len(actions),
                "actions_by_status": action_status_counts,
            },
            "milestones": milestones,
            "tasks": task_list,
        }

        if self._project_id is not None:
            status_dir = DATA_DIR / str(self._project_id)
            status_dir.mkdir(parents=True, exist_ok=True)
            status_path = status_dir / "status.json"
        else:
            status_path = DATA_DIR / "status.json"
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)

        return status_path

    # -- Lifecycle -----------------------------------------------------------

    def close(self) -> None:
        """Close the underlying DB session if we own it."""
        if self._owns_session:
            self._session.close()
