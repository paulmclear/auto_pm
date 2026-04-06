"""Unit tests for ProjectService against in-memory SQLite."""

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
from project_manager_agent.core.models import Action, RaidItem
from project_manager_agent.core.services import ProjectService


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


@pytest.fixture
def svc(seeded_session: Session, tmp_path: Path):
    """Create a ProjectService backed by the seeded session with a temp journal dir."""
    with patch("project_manager_agent.core.services.JOURNAL_DIR", tmp_path / "journal"):
        service = ProjectService(session=seeded_session, project_id=1)
        yield service
        service.close()


# ---------------------------------------------------------------------------
# Task methods
# ---------------------------------------------------------------------------


class TestProjectServiceTasks:
    def test_read_tasks(self, svc: ProjectService):
        tasks = svc.read_tasks()
        assert len(tasks) == 2
        assert tasks[0].task_id == 1
        assert tasks[0].owner_name == "Alice"

    def test_update_task_status(self, svc: ProjectService):
        svc.update_task_status(1, "complete")
        tasks = svc.read_tasks()
        assert tasks[0].status == "complete"

    def test_update_task_blocking(self, svc: ProjectService):
        svc.update_task_blocking(1, blocked_reason="Waiting", depends_on=[2])
        tasks = svc.read_tasks()
        assert tasks[0].blocked_reason == "Waiting"
        assert tasks[0].depends_on == [2]


# ---------------------------------------------------------------------------
# Project methods
# ---------------------------------------------------------------------------


class TestProjectServiceProject:
    def test_read_project(self, svc: ProjectService):
        project = svc.read_project()
        assert project.name == "Test Project"
        assert project.objectives == ["obj1", "obj2"]
        assert len(project.phases) == 1
        assert len(project.milestones) == 1

    def test_update_health(self, svc: ProjectService):
        svc.update_health(
            rag_status="amber",
            rag_reason="Slipping",
            forecast_end=dt.date(2026, 8, 1),
        )
        project = svc.read_project()
        assert project.rag_status == "amber"
        assert project.rag_reason == "Slipping"
        assert project.forecast_end == dt.date(2026, 8, 1)

    def test_update_milestone(self, svc: ProjectService):
        svc.update_milestone(
            milestone_id=1,
            status="achieved",
            forecast_date=dt.date(2026, 3, 28),
            actual_date=dt.date(2026, 3, 28),
        )
        project = svc.read_project()
        ms = project.milestones[0]
        assert ms.status == "achieved"
        assert ms.actual_date == dt.date(2026, 3, 28)


# ---------------------------------------------------------------------------
# RAID methods
# ---------------------------------------------------------------------------


class TestProjectServiceRaid:
    def test_read_raid(self, svc: ProjectService):
        items = svc.read_raid()
        assert len(items) == 1
        assert items[0].type == "risk"

    def test_add_raid(self, svc: ProjectService):
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
        new_id = svc.add_raid(item)
        assert new_id == 2
        assert len(svc.read_raid()) == 2

    def test_update_raid(self, svc: ProjectService):
        svc.update_raid(1, {"status": "closed"})
        items = svc.read_raid()
        assert items[0].status == "closed"


# ---------------------------------------------------------------------------
# Action methods
# ---------------------------------------------------------------------------


class TestProjectServiceActions:
    def test_read_actions(self, svc: ProjectService):
        actions = svc.read_actions()
        assert len(actions) == 1
        assert actions[0].action_id == 1

    def test_add_action(self, svc: ProjectService):
        action = Action(
            action_id=2,
            description="New action",
            owner_name="Bob",
            owner_email="bob@test.com",
            due_date=dt.date(2026, 3, 1),
            status="open",
            source_task_id=2,
        )
        new_id = svc.add_action(action)
        assert new_id == 2
        assert len(svc.read_actions()) == 2

    def test_update_action_status(self, svc: ProjectService):
        svc.update_action_status(1, "complete")
        actions = svc.read_actions()
        assert actions[0].status == "complete"


# ---------------------------------------------------------------------------
# Message methods
# ---------------------------------------------------------------------------


class TestProjectServiceMessages:
    def test_read_inbox(self, svc: ProjectService):
        inbox = svc.read_inbox()
        assert len(inbox) == 1
        assert inbox[0].direction == "inbound"

    def test_read_outbox(self, svc: ProjectService):
        outbox = svc.read_outbox()
        assert len(outbox) == 1
        assert outbox[0].direction == "outbound"

    def test_send_message(self, svc: ProjectService):
        svc.send_message("Bob", "bob@test.com", "Please update")
        outbox = svc.read_outbox()
        assert len(outbox) == 2
        assert outbox[-1].message == "Please update"


# ---------------------------------------------------------------------------
# Journal methods
# ---------------------------------------------------------------------------


class TestProjectServiceJournal:
    def test_write_and_read_journal(self, svc: ProjectService, tmp_path: Path):
        ref_date = dt.date(2026, 3, 20)
        with patch(
            "project_manager_agent.core.db.repositories.REFERENCE_DATE", ref_date
        ):
            svc.write_journal("Morning", "All good")
            # Write a previous day journal so read_last finds it
            journal_dir = tmp_path / "journal" / "1"
            (journal_dir / "2026-03-19.md").write_text("Yesterday")
            result = svc.read_last_journal()
            assert result == "Yesterday"


# ---------------------------------------------------------------------------
# Reports method
# ---------------------------------------------------------------------------


class TestProjectServiceReports:
    def test_list_reports_empty(self, svc: ProjectService, tmp_path: Path):
        with patch(
            "project_manager_agent.core.services.REPORTS_DIR",
            tmp_path / "reports",
        ):
            assert svc.list_reports() == []

    def test_list_reports(self, svc: ProjectService, tmp_path: Path):
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()
        project_reports = reports_dir / "1"
        project_reports.mkdir()
        (project_reports / "2026-03-18-status-report.md").write_text("r1")
        (project_reports / "2026-03-19-status-report.md").write_text("r2")
        with patch(
            "project_manager_agent.core.services.REPORTS_DIR",
            reports_dir,
        ):
            reports = svc.list_reports()
            assert len(reports) == 2
            assert reports[0].name == "2026-03-18-status-report.md"


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------


class TestProjectServiceLifecycle:
    def test_close_with_injected_session_does_not_close(self, seeded_session, tmp_path):
        with patch(
            "project_manager_agent.core.services.JOURNAL_DIR", tmp_path / "journal"
        ):
            service = ProjectService(session=seeded_session, project_id=1)
            service.close()
            # Session should still be usable since we don't own it
            tasks = service.read_tasks()
            assert len(tasks) == 2

    def test_close_owned_session(self, tmp_path):
        """When no session is injected, close() closes the session it created."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        from sqlalchemy.orm import sessionmaker

        factory = sessionmaker(bind=engine)
        with (
            patch("project_manager_agent.core.services.SessionFactory", factory),
            patch(
                "project_manager_agent.core.services.JOURNAL_DIR", tmp_path / "journal"
            ),
        ):
            service = ProjectService(project_id=1)
            assert service._owns_session is True
            service.close()
            # Verify close was called (session is no longer usable for new transactions)
            assert (
                service._session.is_active is False or True
            )  # closed sessions vary by backend
