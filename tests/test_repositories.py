"""Unit tests for SQL repository implementations using in-memory SQLite."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from project_manager_agent.core.db.orm import (
    ActionRow,
    Base,
    MessageRow,
    MilestoneRow,
    PhaseRow,
    ProjectRow,
    RaidItemRow,
    TaskRow,
)
from project_manager_agent.core.db.repositories import (
    FileJournalRepository,
    SqliteActionRepository,
    SqliteMessageRepository,
    SqliteProjectRepository,
    SqliteRaidRepository,
    SqliteTaskRepository,
)
from project_manager_agent.core.models import Action, RaidItem


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def session():
    """Create an in-memory SQLite engine, build all tables, yield a session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as sess:
        yield sess


@pytest.fixture
def seeded_session(session: Session):
    """Seed a minimal dataset and return the session."""
    # Project with one phase and one milestone
    project = ProjectRow(
        name="Test Project",
        description="A test project",
        objectives=json.dumps(["obj1", "obj2"]),
        sponsor="Sponsor",
        project_manager="PM",
        planned_start=dt.date(2026, 1, 1),
        planned_end=dt.date(2026, 6, 30),
        actual_start=dt.date(2026, 1, 5),
        forecast_end=dt.date(2026, 7, 15),
        rag_status="green",
        rag_reason="On track",
    )
    session.add(project)
    session.flush()

    session.add(
        PhaseRow(
            phase_id=1,
            project_id=project.id,
            name="Phase 1",
            description="First phase",
            planned_start=dt.date(2026, 1, 1),
            planned_end=dt.date(2026, 3, 31),
        )
    )
    session.add(
        MilestoneRow(
            milestone_id=1,
            project_id=project.id,
            name="MS-1",
            description="First milestone",
            planned_date=dt.date(2026, 3, 31),
            forecast_date=dt.date(2026, 3, 31),
            actual_date=None,
            status="pending",
            linked_task_ids=json.dumps([1, 2]),
        )
    )

    # Two tasks
    session.add(
        TaskRow(
            task_id=1,
            project_id=project.id,
            description="Task one",
            owner_name="Alice",
            owner_email="alice@test.com",
            due_date=dt.date(2026, 2, 15),
            status="in_progress",
            phase_id=1,
            depends_on=json.dumps([]),
        )
    )
    session.add(
        TaskRow(
            task_id=2,
            project_id=project.id,
            description="Task two",
            owner_name="Bob",
            owner_email="bob@test.com",
            due_date=dt.date(2026, 3, 1),
            status="not_started",
            phase_id=1,
            depends_on=json.dumps([1]),
        )
    )

    # One RAID item (risk)
    session.add(
        RaidItemRow(
            raid_id=1,
            project_id=project.id,
            type="risk",
            title="Risk one",
            description="A risk",
            owner="Alice",
            raised_date=dt.date(2026, 1, 10),
            status="open",
            linked_task_ids=json.dumps([1]),
            probability="high",
            impact="medium",
            mitigation="Mitigate it",
            review_date=dt.date(2026, 2, 1),
        )
    )

    # One action
    session.add(
        ActionRow(
            action_id=1,
            project_id=project.id,
            description="Follow up on risk",
            owner_name="Alice",
            owner_email="alice@test.com",
            due_date=dt.date(2026, 2, 1),
            status="open",
            source_raid_id=1,
        )
    )

    # Two messages (one inbound, one outbound)
    session.add(
        MessageRow(
            message_id="msg-in-1",
            project_id=project.id,
            direction="inbound",
            timestamp="2026-01-15T10:00:00",
            owner_name="Alice",
            owner_email="alice@test.com",
            message="Status update: on track",
            sender_name="Alice",
            sender_email="alice@test.com",
        )
    )
    session.add(
        MessageRow(
            message_id="msg-out-1",
            project_id=project.id,
            direction="outbound",
            timestamp="2026-01-15T11:00:00",
            owner_name="Alice",
            owner_email="alice@test.com",
            message="Thanks for the update",
            sender_name="Project Manager Agent",
            sender_email="agent@project-manager.local",
        )
    )

    session.commit()
    return session


# ---------------------------------------------------------------------------
# SqliteTaskRepository
# ---------------------------------------------------------------------------


class TestSqliteTaskRepository:
    def test_read_returns_all_tasks(self, seeded_session: Session):
        repo = SqliteTaskRepository(seeded_session)
        tasks = repo.read()
        assert len(tasks) == 2
        assert tasks[0].task_id == 1
        assert tasks[0].description == "Task one"
        assert tasks[0].owner_name == "Alice"
        assert tasks[0].due_date == dt.date(2026, 2, 15)
        assert tasks[0].status == "in_progress"
        assert tasks[0].depends_on == []

    def test_read_returns_depends_on_list(self, seeded_session: Session):
        repo = SqliteTaskRepository(seeded_session)
        tasks = repo.read()
        assert tasks[1].depends_on == [1]

    def test_read_empty_table(self, session: Session):
        repo = SqliteTaskRepository(session)
        assert repo.read() == []

    def test_update_status(self, seeded_session: Session):
        repo = SqliteTaskRepository(seeded_session)
        repo.update_status(1, "complete")
        tasks = repo.read()
        assert tasks[0].status == "complete"

    def test_update_status_nonexistent_raises(self, seeded_session: Session):
        repo = SqliteTaskRepository(seeded_session)
        with pytest.raises(ValueError, match="Task 999 not found"):
            repo.update_status(999, "complete")

    def test_update_blocking(self, seeded_session: Session):
        repo = SqliteTaskRepository(seeded_session)
        repo.update_blocking(1, blocked_reason="Waiting on vendor", depends_on=[2])
        tasks = repo.read()
        assert tasks[0].blocked_reason == "Waiting on vendor"
        assert tasks[0].depends_on == [2]

    def test_update_blocking_nonexistent_raises(self, seeded_session: Session):
        repo = SqliteTaskRepository(seeded_session)
        with pytest.raises(ValueError, match="Task 999 not found"):
            repo.update_blocking(999, blocked_reason="x", depends_on=None)


# ---------------------------------------------------------------------------
# SqliteProjectRepository
# ---------------------------------------------------------------------------


class TestSqliteProjectRepository:
    def test_read_returns_project(self, seeded_session: Session):
        repo = SqliteProjectRepository(seeded_session)
        project = repo.read()
        assert project.name == "Test Project"
        assert project.objectives == ["obj1", "obj2"]
        assert project.rag_status == "green"
        assert len(project.phases) == 1
        assert project.phases[0].name == "Phase 1"
        assert len(project.milestones) == 1
        assert project.milestones[0].linked_task_ids == [1, 2]

    def test_read_no_project_raises(self, session: Session):
        repo = SqliteProjectRepository(session)
        with pytest.raises(ValueError, match="No project found"):
            repo.read()

    def test_update_health(self, seeded_session: Session):
        repo = SqliteProjectRepository(seeded_session)
        repo.update_health(
            rag_status="amber",
            rag_reason="Slipping",
            forecast_end=dt.date(2026, 8, 1),
        )
        project = repo.read()
        assert project.rag_status == "amber"
        assert project.rag_reason == "Slipping"
        assert project.forecast_end == dt.date(2026, 8, 1)

    def test_update_health_partial(self, seeded_session: Session):
        repo = SqliteProjectRepository(seeded_session)
        repo.update_health(rag_status="red", rag_reason=None, forecast_end=None)
        project = repo.read()
        assert project.rag_status == "red"
        assert project.rag_reason == "On track"  # unchanged

    def test_update_milestone(self, seeded_session: Session):
        repo = SqliteProjectRepository(seeded_session)
        repo.update_milestone(
            milestone_id=1,
            status="achieved",
            forecast_date=dt.date(2026, 3, 28),
            actual_date=dt.date(2026, 3, 28),
        )
        project = repo.read()
        ms = project.milestones[0]
        assert ms.status == "achieved"
        assert ms.forecast_date == dt.date(2026, 3, 28)
        assert ms.actual_date == dt.date(2026, 3, 28)

    def test_update_milestone_nonexistent_raises(self, seeded_session: Session):
        repo = SqliteProjectRepository(seeded_session)
        with pytest.raises(ValueError, match="Milestone 999 not found"):
            repo.update_milestone(
                999, status="achieved", forecast_date=None, actual_date=None
            )


# ---------------------------------------------------------------------------
# SqliteRaidRepository
# ---------------------------------------------------------------------------


class TestSqliteRaidRepository:
    def test_read_returns_all_items(self, seeded_session: Session):
        repo = SqliteRaidRepository(seeded_session)
        items = repo.read()
        assert len(items) == 1
        assert items[0].raid_id == 1
        assert items[0].type == "risk"
        assert items[0].linked_task_ids == [1]
        assert items[0].probability == "high"

    def test_read_empty(self, session: Session):
        repo = SqliteRaidRepository(session)
        assert repo.read() == []

    def test_add(self, seeded_session: Session):
        repo = SqliteRaidRepository(seeded_session)
        item = RaidItem(
            raid_id=2,
            type="issue",
            title="New issue",
            description="Something broke",
            owner="Bob",
            raised_date=dt.date(2026, 2, 1),
            status="open",
            linked_task_ids=[2],
            severity="high",
        )
        returned_id = repo.add(item)
        assert returned_id == 2
        items = repo.read()
        assert len(items) == 2
        assert items[1].title == "New issue"
        assert items[1].severity == "high"

    def test_update(self, seeded_session: Session):
        repo = SqliteRaidRepository(seeded_session)
        repo.update(1, {"status": "closed", "mitigation": "Resolved via workaround"})
        items = repo.read()
        assert items[0].status == "closed"
        assert items[0].mitigation == "Resolved via workaround"

    def test_update_linked_task_ids(self, seeded_session: Session):
        repo = SqliteRaidRepository(seeded_session)
        repo.update(1, {"linked_task_ids": [1, 2]})
        items = repo.read()
        assert items[0].linked_task_ids == [1, 2]

    def test_update_nonexistent_raises(self, seeded_session: Session):
        repo = SqliteRaidRepository(seeded_session)
        with pytest.raises(ValueError, match="RAID item 999 not found"):
            repo.update(999, {"status": "closed"})


# ---------------------------------------------------------------------------
# SqliteActionRepository
# ---------------------------------------------------------------------------


class TestSqliteActionRepository:
    def test_read(self, seeded_session: Session):
        repo = SqliteActionRepository(seeded_session)
        actions = repo.read()
        assert len(actions) == 1
        assert actions[0].action_id == 1
        assert actions[0].source_raid_id == 1

    def test_read_empty(self, session: Session):
        repo = SqliteActionRepository(session)
        assert repo.read() == []

    def test_add(self, seeded_session: Session):
        repo = SqliteActionRepository(seeded_session)
        action = Action(
            action_id=2,
            description="New action",
            owner_name="Bob",
            owner_email="bob@test.com",
            due_date=dt.date(2026, 3, 1),
            status="open",
            source_task_id=2,
        )
        returned_id = repo.add(action)
        assert returned_id == 2
        actions = repo.read()
        assert len(actions) == 2

    def test_update_status(self, seeded_session: Session):
        repo = SqliteActionRepository(seeded_session)
        repo.update_status(1, "complete")
        actions = repo.read()
        assert actions[0].status == "complete"

    def test_update_status_nonexistent_raises(self, seeded_session: Session):
        repo = SqliteActionRepository(seeded_session)
        with pytest.raises(ValueError, match="Action 999 not found"):
            repo.update_status(999, "complete")


# ---------------------------------------------------------------------------
# SqliteMessageRepository
# ---------------------------------------------------------------------------


class TestSqliteMessageRepository:
    def test_read_inbox(self, seeded_session: Session):
        repo = SqliteMessageRepository(seeded_session)
        inbox = repo.read_inbox()
        assert len(inbox) == 1
        assert inbox[0].direction == "inbound"
        assert inbox[0].message == "Status update: on track"

    def test_read_outbox(self, seeded_session: Session):
        repo = SqliteMessageRepository(seeded_session)
        outbox = repo.read_outbox()
        assert len(outbox) == 1
        assert outbox[0].direction == "outbound"

    def test_read_inbox_empty(self, session: Session):
        repo = SqliteMessageRepository(session)
        assert repo.read_inbox() == []

    def test_send_creates_outbound_message(self, seeded_session: Session):
        repo = SqliteMessageRepository(seeded_session)
        repo.send("Bob", "bob@test.com", "Please update task 2")
        outbox = repo.read_outbox()
        assert len(outbox) == 2
        new_msg = outbox[-1]
        assert new_msg.direction == "outbound"
        assert new_msg.owner_name == "Bob"
        assert new_msg.message == "Please update task 2"
        assert new_msg.sender_name == "Project Manager Agent"


# ---------------------------------------------------------------------------
# FileJournalRepository
# ---------------------------------------------------------------------------


class TestFileJournalRepository:
    def test_write_creates_journal_file(self, tmp_path: Path):
        ref_date = dt.date(2026, 3, 20)
        with patch(
            "project_manager_agent.core.db.repositories.REFERENCE_DATE", ref_date
        ):
            repo = FileJournalRepository(tmp_path / "journal", project_id=1)
            repo.write("Morning Review", "All good")
            journal_file = tmp_path / "journal" / "1" / "2026-03-20.md"
            assert journal_file.exists()
            content = journal_file.read_text()
            assert "# Project Manager Journal — 2026-03-20" in content
            assert "## Morning Review" in content
            assert "All good" in content

    def test_write_appends_to_existing_file(self, tmp_path: Path):
        ref_date = dt.date(2026, 3, 20)
        with patch(
            "project_manager_agent.core.db.repositories.REFERENCE_DATE", ref_date
        ):
            repo = FileJournalRepository(tmp_path / "journal", project_id=1)
            repo.write("Section 1", "Content 1")
            repo.write("Section 2", "Content 2")
            content = (tmp_path / "journal" / "1" / "2026-03-20.md").read_text()
            assert "## Section 1" in content
            assert "## Section 2" in content

    def test_read_last_returns_previous_day(self, tmp_path: Path):
        journal_dir = tmp_path / "journal"
        journal_dir.mkdir()
        project_journal = journal_dir / "1"
        project_journal.mkdir()
        # Write a "previous" journal
        (project_journal / "2026-03-19.md").write_text("Yesterday's journal")
        ref_date = dt.date(2026, 3, 20)
        with patch(
            "project_manager_agent.core.db.repositories.REFERENCE_DATE", ref_date
        ):
            repo = FileJournalRepository(journal_dir, project_id=1)
            result = repo.read_last()
            assert result == "Yesterday's journal"

    def test_read_last_returns_none_when_no_past(self, tmp_path: Path):
        ref_date = dt.date(2026, 3, 20)
        with patch(
            "project_manager_agent.core.db.repositories.REFERENCE_DATE", ref_date
        ):
            repo = FileJournalRepository(tmp_path / "journal", project_id=1)
            assert repo.read_last() is None

    def test_read_last_ignores_current_day(self, tmp_path: Path):
        journal_dir = tmp_path / "journal"
        journal_dir.mkdir()
        project_journal = journal_dir / "1"
        project_journal.mkdir()
        # Only today's journal exists
        (project_journal / "2026-03-20.md").write_text("Today's journal")
        ref_date = dt.date(2026, 3, 20)
        with patch(
            "project_manager_agent.core.db.repositories.REFERENCE_DATE", ref_date
        ):
            repo = FileJournalRepository(journal_dir, project_id=1)
            assert repo.read_last() is None

    def test_read_last_picks_most_recent(self, tmp_path: Path):
        journal_dir = tmp_path / "journal"
        journal_dir.mkdir()
        project_journal = journal_dir / "1"
        project_journal.mkdir()
        (project_journal / "2026-03-18.md").write_text("Two days ago")
        (project_journal / "2026-03-19.md").write_text("Yesterday")
        ref_date = dt.date(2026, 3, 20)
        with patch(
            "project_manager_agent.core.db.repositories.REFERENCE_DATE", ref_date
        ):
            repo = FileJournalRepository(journal_dir, project_id=1)
            assert repo.read_last() == "Yesterday"
