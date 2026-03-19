"""Web route tests using FastAPI TestClient.

Seeds demo data into an in-memory SQLite database and asserts each
route returns 200 with expected key content in the HTML response.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from project_manager_agent.core.db.orm import Base
from project_manager_agent.core.db.seed import seed_demo_data
from project_manager_agent.core.services import ProjectService


@pytest.fixture
def client(tmp_path):
    """FastAPI TestClient with demo data seeded via dependency override."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as sess:
        seed_demo_data(sess)
        sess.commit()

    Factory = sessionmaker(bind=engine)

    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    (journal_dir / "2026-03-18.md").write_text(
        "# Journal — 2026-03-18\nDemo journal day 1"
    )
    (journal_dir / "2026-03-19.md").write_text(
        "# Journal — 2026-03-19\nDemo journal day 2"
    )

    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "2026-03-18-status-report.md").write_text(
        "# Status Report — 2026-03-18\nAll good"
    )

    with (
        patch("project_manager_agent.web.routes.journal.JOURNAL_DIR", journal_dir),
        patch("project_manager_agent.web.routes.reports.REPORTS_DIR", reports_dir),
        patch("project_manager_agent.web.app.create_tables"),
    ):
        from project_manager_agent.web.app import create_app, get_service

        app = create_app()

        async def _override_service():
            svc = ProjectService(session=Factory())
            svc.journal = type(svc.journal)(journal_dir)
            try:
                yield svc
            finally:
                svc.close()

        app.dependency_overrides[get_service] = _override_service
        yield TestClient(app)
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class TestDashboard:
    def test_dashboard_returns_200(self, client: TestClient):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_dashboard_contains_project_name(self, client: TestClient):
        resp = client.get("/")
        assert "Customer Portal Modernisation" in resp.text

    def test_dashboard_contains_rag_status(self, client: TestClient):
        resp = client.get("/")
        assert "amber" in resp.text.lower()


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


class TestTasks:
    def test_tasks_returns_200(self, client: TestClient):
        resp = client.get("/tasks")
        assert resp.status_code == 200

    def test_tasks_contains_task_descriptions(self, client: TestClient):
        resp = client.get("/tasks")
        html = resp.text
        assert "API" in html or "api" in html.lower()

    def test_tasks_contains_status_badges(self, client: TestClient):
        resp = client.get("/tasks")
        html = resp.text
        assert "in_progress" in html or "complete" in html or "not_started" in html


# ---------------------------------------------------------------------------
# RAID
# ---------------------------------------------------------------------------


class TestRaid:
    def test_raid_returns_200(self, client: TestClient):
        resp = client.get("/raid")
        assert resp.status_code == 200

    def test_raid_contains_raid_entries(self, client: TestClient):
        resp = client.get("/raid")
        html = resp.text
        assert "risk" in html.lower() or "issue" in html.lower()

    def test_raid_contains_type_badges(self, client: TestClient):
        resp = client.get("/raid")
        html = resp.text
        assert "risk" in html.lower()


# ---------------------------------------------------------------------------
# Journal
# ---------------------------------------------------------------------------


class TestJournal:
    def test_journal_list_returns_200(self, client: TestClient):
        resp = client.get("/journal")
        assert resp.status_code == 200

    def test_journal_list_contains_dates(self, client: TestClient):
        resp = client.get("/journal")
        assert "2026-03-19" in resp.text
        assert "2026-03-18" in resp.text

    def test_journal_detail_returns_200(self, client: TestClient):
        resp = client.get("/journal/2026-03-19")
        assert resp.status_code == 200

    def test_journal_detail_contains_content(self, client: TestClient):
        resp = client.get("/journal/2026-03-19")
        assert "Demo journal day 2" in resp.text

    def test_journal_detail_404_for_missing(self, client: TestClient):
        resp = client.get("/journal/1999-01-01")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


class TestReports:
    def test_reports_list_returns_200(self, client: TestClient):
        resp = client.get("/reports")
        assert resp.status_code == 200

    def test_reports_list_contains_dates(self, client: TestClient):
        resp = client.get("/reports")
        assert "2026-03-18-status-report" in resp.text

    def test_report_detail_returns_200(self, client: TestClient):
        resp = client.get("/reports/2026-03-18-status-report")
        assert resp.status_code == 200

    def test_report_detail_contains_content(self, client: TestClient):
        resp = client.get("/reports/2026-03-18-status-report")
        assert "All good" in resp.text

    def test_report_detail_404_for_missing(self, client: TestClient):
        resp = client.get("/reports/1999-01-01")
        assert resp.status_code == 404
