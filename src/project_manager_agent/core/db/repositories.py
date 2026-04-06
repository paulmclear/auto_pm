"""SQLite-backed repository implementations satisfying the Protocol interfaces."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from project_manager_agent.core.date_utils import REFERENCE_DATE
from project_manager_agent.core.models import (
    Action,
    ActionStatus,
    Message,
    Milestone,
    MilestoneStatus,
    Phase,
    Project,
    RagStatus,
    RaidItem,
    Task,
    TaskStatus,
)
from project_manager_agent.core.db.orm import (
    ActionRow,
    MessageRow,
    MilestoneRow,
    PhaseRow,
    ProjectRow,
    RaidItemRow,
    TaskRow,
)


# ---------------------------------------------------------------------------
# Helpers: ORM row → domain dataclass
# ---------------------------------------------------------------------------


def _task_to_domain(row: TaskRow) -> Task:
    return Task(
        task_id=row.task_id,
        description=row.description,
        owner_name=row.owner_name,
        owner_email=row.owner_email,
        due_date=row.due_date,
        status=row.status,
        priority=row.priority,
        phase_id=row.phase_id,
        depends_on=json.loads(row.depends_on),
        blocked_reason=row.blocked_reason,
        external_dependency=row.external_dependency,
    )


def _phase_to_domain(row: PhaseRow) -> Phase:
    return Phase(
        phase_id=row.phase_id,
        name=row.name,
        description=row.description,
        planned_start=row.planned_start,
        planned_end=row.planned_end,
    )


def _milestone_to_domain(row: MilestoneRow) -> Milestone:
    return Milestone(
        milestone_id=row.milestone_id,
        name=row.name,
        description=row.description,
        planned_date=row.planned_date,
        forecast_date=row.forecast_date,
        actual_date=row.actual_date,
        status=row.status,
        linked_task_ids=json.loads(row.linked_task_ids),
    )


def _project_to_domain(row: ProjectRow) -> Project:
    return Project(
        name=row.name,
        description=row.description,
        objectives=json.loads(row.objectives),
        sponsor=row.sponsor,
        project_manager=row.project_manager,
        planned_start=row.planned_start,
        planned_end=row.planned_end,
        actual_start=row.actual_start,
        forecast_end=row.forecast_end,
        rag_status=row.rag_status,
        rag_reason=row.rag_reason,
        phases=[_phase_to_domain(p) for p in row.phases],
        milestones=[_milestone_to_domain(m) for m in row.milestones],
    )


def _raid_to_domain(row: RaidItemRow) -> RaidItem:
    return RaidItem(
        raid_id=row.raid_id,
        type=row.type,
        title=row.title,
        description=row.description,
        owner=row.owner,
        raised_date=row.raised_date,
        status=row.status,
        linked_task_ids=json.loads(row.linked_task_ids),
        probability=row.probability,
        impact=row.impact,
        mitigation=row.mitigation,
        review_date=row.review_date,
        validation_method=row.validation_method,
        validation_date=row.validation_date,
        validated_by=row.validated_by,
        severity=row.severity,
        resolution=row.resolution,
        resolved_date=row.resolved_date,
        rationale=row.rationale,
        decided_by=row.decided_by,
        decision_date=row.decision_date,
        alternatives_considered=row.alternatives_considered,
    )


def _action_to_domain(row: ActionRow) -> Action:
    return Action(
        action_id=row.action_id,
        description=row.description,
        owner_name=row.owner_name,
        owner_email=row.owner_email,
        due_date=row.due_date,
        status=row.status,
        source_raid_id=row.source_raid_id,
        source_task_id=row.source_task_id,
    )


def _message_to_domain(row: MessageRow) -> Message:
    return Message(
        message_id=row.message_id,
        direction=row.direction,
        timestamp=row.timestamp,
        owner_name=row.owner_name,
        owner_email=row.owner_email,
        message=row.message,
        sender_name=row.sender_name,
        sender_email=row.sender_email,
        task_id=row.task_id,
    )


# ---------------------------------------------------------------------------
# SqliteTaskRepository
# ---------------------------------------------------------------------------


class SqliteTaskRepository:
    """Task persistence backed by SQLite via SQLAlchemy."""

    def __init__(self, session: Session, project_id: Optional[int] = None) -> None:
        self._session = session
        self._project_id = project_id

    def read(self) -> list[Task]:
        q = self._session.query(TaskRow)
        if self._project_id is not None:
            q = q.filter(TaskRow.project_id == self._project_id)
        rows = q.order_by(TaskRow.task_id).all()
        return [_task_to_domain(r) for r in rows]

    def update_status(self, task_id: int, status: TaskStatus) -> None:
        row = self._session.get(TaskRow, task_id)
        if row is None:
            raise ValueError(f"Task {task_id} not found")
        row.status = status
        self._session.commit()

    def update_blocking(
        self,
        task_id: int,
        blocked_reason: Optional[str],
        depends_on: Optional[list[int]],
    ) -> None:
        row = self._session.get(TaskRow, task_id)
        if row is None:
            raise ValueError(f"Task {task_id} not found")
        if blocked_reason is not None:
            row.blocked_reason = blocked_reason
        if depends_on is not None:
            row.depends_on = json.dumps(depends_on)
        self._session.commit()


# ---------------------------------------------------------------------------
# SqliteProjectRepository
# ---------------------------------------------------------------------------


class SqliteProjectRepository:
    """Project-plan persistence backed by SQLite via SQLAlchemy."""

    def __init__(self, session: Session, project_id: Optional[int] = None) -> None:
        self._session = session
        self._project_id = project_id

    def _get_project_row(self) -> ProjectRow:
        q = self._session.query(ProjectRow)
        if self._project_id is not None:
            q = q.filter(ProjectRow.id == self._project_id)
        row = q.first()
        if row is None:
            raise ValueError("No project found in database")
        return row

    def read(self) -> Project:
        return _project_to_domain(self._get_project_row())

    def create(
        self,
        name: str,
        description: str,
        objectives: list[str],
        sponsor: str,
        project_manager: str,
        planned_start: dt.date,
        planned_end: dt.date,
    ) -> int:
        """Create a new project and return its ID."""
        row = ProjectRow(
            name=name,
            description=description,
            objectives=json.dumps(objectives),
            sponsor=sponsor,
            project_manager=project_manager,
            planned_start=planned_start,
            planned_end=planned_end,
            actual_start=planned_start,
            forecast_end=planned_end,
            rag_status="green",
            rag_reason="New project",
            is_archived=False,
        )
        self._session.add(row)
        self._session.commit()
        return row.id

    def update(self, project_id: int, fields: dict) -> None:
        """Update arbitrary fields on a project row."""
        row = self._session.get(ProjectRow, project_id)
        if row is None:
            raise ValueError(f"Project {project_id} not found")
        for key, value in fields.items():
            if value is not None and hasattr(row, key):
                if key == "objectives":
                    value = json.dumps(value)
                setattr(row, key, value)
        self._session.commit()

    def archive(self, project_id: int) -> None:
        """Soft-delete a project by setting is_archived=True."""
        row = self._session.get(ProjectRow, project_id)
        if row is None:
            raise ValueError(f"Project {project_id} not found")
        row.is_archived = True
        self._session.commit()

    def update_health(
        self,
        rag_status: Optional[RagStatus],
        rag_reason: Optional[str],
        forecast_end: Optional[dt.date],
    ) -> None:
        row = self._get_project_row()
        if rag_status is not None:
            row.rag_status = rag_status
        if rag_reason is not None:
            row.rag_reason = rag_reason
        if forecast_end is not None:
            row.forecast_end = forecast_end
        self._session.commit()

    def update_milestone(
        self,
        milestone_id: int,
        status: Optional[MilestoneStatus],
        forecast_date: Optional[dt.date],
        actual_date: Optional[dt.date],
    ) -> None:
        row = self._session.get(MilestoneRow, milestone_id)
        if row is None:
            raise ValueError(f"Milestone {milestone_id} not found")
        if status is not None:
            row.status = status
        if forecast_date is not None:
            row.forecast_date = forecast_date
        if actual_date is not None:
            row.actual_date = actual_date
        self._session.commit()


# ---------------------------------------------------------------------------
# SqliteRaidRepository
# ---------------------------------------------------------------------------


class SqliteRaidRepository:
    """RAID-log persistence backed by SQLite via SQLAlchemy."""

    def __init__(self, session: Session, project_id: Optional[int] = None) -> None:
        self._session = session
        self._project_id = project_id

    def read(self) -> list[RaidItem]:
        q = self._session.query(RaidItemRow)
        if self._project_id is not None:
            q = q.filter(RaidItemRow.project_id == self._project_id)
        rows = q.order_by(RaidItemRow.raid_id).all()
        return [_raid_to_domain(r) for r in rows]

    def add(self, item: RaidItem) -> int:
        row = RaidItemRow(
            raid_id=item.raid_id,
            project_id=self._project_id,
            type=item.type,
            title=item.title,
            description=item.description,
            owner=item.owner,
            raised_date=item.raised_date,
            status=item.status,
            linked_task_ids=json.dumps(item.linked_task_ids),
            probability=item.probability,
            impact=item.impact,
            mitigation=item.mitigation,
            review_date=item.review_date,
            validation_method=item.validation_method,
            validation_date=item.validation_date,
            validated_by=item.validated_by,
            severity=item.severity,
            resolution=item.resolution,
            resolved_date=item.resolved_date,
            rationale=item.rationale,
            decided_by=item.decided_by,
            decision_date=item.decision_date,
            alternatives_considered=item.alternatives_considered,
        )
        self._session.add(row)
        self._session.commit()
        return row.raid_id

    def update(self, raid_id: int, fields: dict) -> None:
        row = self._session.get(RaidItemRow, raid_id)
        if row is None:
            raise ValueError(f"RAID item {raid_id} not found")
        for key, value in fields.items():
            if value is not None and hasattr(row, key):
                if key == "linked_task_ids":
                    value = json.dumps(value)
                setattr(row, key, value)
        self._session.commit()


# ---------------------------------------------------------------------------
# SqliteActionRepository
# ---------------------------------------------------------------------------


class SqliteActionRepository:
    """Action-item persistence backed by SQLite via SQLAlchemy."""

    def __init__(self, session: Session, project_id: Optional[int] = None) -> None:
        self._session = session
        self._project_id = project_id

    def read(self) -> list[Action]:
        q = self._session.query(ActionRow)
        if self._project_id is not None:
            q = q.filter(ActionRow.project_id == self._project_id)
        rows = q.order_by(ActionRow.action_id).all()
        return [_action_to_domain(r) for r in rows]

    def add(self, action: Action) -> int:
        row = ActionRow(
            action_id=action.action_id,
            project_id=self._project_id,
            description=action.description,
            owner_name=action.owner_name,
            owner_email=action.owner_email,
            due_date=action.due_date,
            status=action.status,
            source_raid_id=action.source_raid_id,
            source_task_id=action.source_task_id,
        )
        self._session.add(row)
        self._session.commit()
        return row.action_id

    def update_status(self, action_id: int, status: ActionStatus) -> None:
        row = self._session.get(ActionRow, action_id)
        if row is None:
            raise ValueError(f"Action {action_id} not found")
        row.status = status
        self._session.commit()


# ---------------------------------------------------------------------------
# SqliteMessageRepository
# ---------------------------------------------------------------------------


class SqliteMessageRepository:
    """Inbox/outbox message persistence backed by SQLite via SQLAlchemy."""

    def __init__(self, session: Session, project_id: Optional[int] = None) -> None:
        self._session = session
        self._project_id = project_id

    def send(
        self,
        owner_name: str,
        owner_email: str,
        message: str,
        task_id: Optional[int] = None,
    ) -> None:
        import uuid

        row = MessageRow(
            message_id=str(uuid.uuid4()),
            project_id=self._project_id,
            direction="outbound",
            timestamp=dt.datetime.now().isoformat(),
            owner_name=owner_name,
            owner_email=owner_email,
            message=message,
            sender_name="Project Manager Agent",
            sender_email="agent@project-manager.local",
            task_id=task_id,
        )
        self._session.add(row)
        self._session.commit()

    def read_inbox(self) -> list[Message]:
        q = self._session.query(MessageRow).filter(MessageRow.direction == "inbound")
        if self._project_id is not None:
            q = q.filter(MessageRow.project_id == self._project_id)
        rows = q.order_by(MessageRow.timestamp).all()
        return [_message_to_domain(r) for r in rows]

    def read_outbox(self) -> list[Message]:
        q = self._session.query(MessageRow).filter(MessageRow.direction == "outbound")
        if self._project_id is not None:
            q = q.filter(MessageRow.project_id == self._project_id)
        rows = q.order_by(MessageRow.timestamp).all()
        return [_message_to_domain(r) for r in rows]


# ---------------------------------------------------------------------------
# FileJournalRepository
# ---------------------------------------------------------------------------


class FileJournalRepository:
    """Journal persistence using markdown files on disk."""

    def __init__(self, journal_dir: Path, project_id: Optional[int] = None) -> None:
        if project_id is not None:
            self._journal_dir = journal_dir / str(project_id)
        else:
            self._journal_dir = journal_dir
        self._journal_dir.mkdir(parents=True, exist_ok=True)

    @property
    def _today_file(self) -> Path:
        return self._journal_dir / f"{REFERENCE_DATE}.md"

    def read_last(self) -> Optional[str]:
        past = sorted(
            (f for f in self._journal_dir.glob("*.md") if f.stem < str(REFERENCE_DATE)),
            reverse=True,
        )
        if not past:
            return None
        with open(past[0], "r", encoding="utf-8") as f:
            return f.read()

    def read_range(self, start: dt.date, end: dt.date) -> dict[dt.date, str]:
        """Read all journal entries between *start* and *end* (inclusive).

        Returns a dict mapping date → journal content, sorted oldest-first.
        """
        results: dict[dt.date, str] = {}
        for f in sorted(self._journal_dir.glob("*.md")):
            try:
                file_date = dt.date.fromisoformat(f.stem)
            except ValueError:
                continue
            if start <= file_date <= end:
                with open(f, "r", encoding="utf-8") as fh:
                    results[file_date] = fh.read()
        return results

    def has_today_entry(self) -> bool:
        """Return True if a journal file already exists for today's date."""
        return self._today_file.exists()

    def write(self, section: str, content: str) -> None:
        if not self._today_file.exists():
            with open(self._today_file, "w", encoding="utf-8") as f:
                f.write(f"# Project Manager Journal — {REFERENCE_DATE}\n\n")
        timestamp = dt.datetime.now().strftime("%H:%M:%S")
        with open(self._today_file, "a", encoding="utf-8") as f:
            f.write(f"## {section}\n*{timestamp}*\n\n{content}\n\n")
