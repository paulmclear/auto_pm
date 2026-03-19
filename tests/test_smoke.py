"""End-to-end smoke tests for PM agent and reporter.

Seeds demo data into an in-memory SQLite database, runs the PM agent daily
loop (with a mocked LLM), and verifies the reporter context gathering works
against the SQL data layer.
"""

import datetime as dt
from typing import Annotated, TypedDict
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage
from langgraph.graph.message import add_messages
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from project_manager_agent.core.db.orm import Base
from project_manager_agent.core.db.seed import seed_demo_data
from project_manager_agent.core.services import ProjectService


class _SmokeState(TypedDict):
    messages: Annotated[list, add_messages]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def demo_engine():
    """Create an in-memory engine with demo data seeded."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as sess:
        seed_demo_data(sess)
        sess.commit()
    return engine


@pytest.fixture
def demo_session(demo_engine):
    """Yield a session from the demo-seeded engine."""
    Factory = sessionmaker(bind=demo_engine)
    sess = Factory()
    yield sess
    sess.close()


@pytest.fixture
def demo_svc(demo_session, tmp_path):
    """ProjectService backed by demo data."""
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    # Seed journal files in the temp dir
    (journal_dir / "2026-03-18.md").write_text("# Journal — 2026-03-18\nDemo journal")
    (journal_dir / "2026-03-19.md").write_text("# Journal — 2026-03-19\nDemo journal")
    with patch("project_manager_agent.core.services.JOURNAL_DIR", journal_dir):
        svc = ProjectService(session=demo_session)
        yield svc
        svc.close()


# ---------------------------------------------------------------------------
# Demo data verification
# ---------------------------------------------------------------------------


class TestDemoDataIntegrity:
    """Verify demo data was correctly seeded and can be read through ProjectService."""

    def test_project_loaded(self, demo_svc: ProjectService):
        project = demo_svc.read_project()
        assert project.name == "Customer Portal Modernisation"
        assert project.rag_status == "amber"
        assert len(project.phases) == 3
        assert len(project.milestones) == 3

    def test_tasks_loaded(self, demo_svc: ProjectService):
        tasks = demo_svc.read_tasks()
        assert len(tasks) == 11
        statuses = {t.status for t in tasks}
        assert statuses == {"complete", "in_progress", "blocked", "not_started"}

    def test_raid_loaded(self, demo_svc: ProjectService):
        raid = demo_svc.read_raid()
        assert len(raid) == 7
        types = {r.type for r in raid}
        assert types == {"risk", "assumption", "issue", "decision"}

    def test_actions_loaded(self, demo_svc: ProjectService):
        actions = demo_svc.read_actions()
        assert len(actions) == 3

    def test_messages_loaded(self, demo_svc: ProjectService):
        inbox = demo_svc.read_inbox()
        outbox = demo_svc.read_outbox()
        assert len(inbox) == 2
        assert len(outbox) == 1

    def test_journal_readable(self, demo_svc: ProjectService):
        ref_date = dt.date(2026, 3, 20)
        with patch(
            "project_manager_agent.core.db.repositories.REFERENCE_DATE", ref_date
        ):
            journal = demo_svc.read_last_journal()
            assert journal is not None
            assert "2026-03-19" in journal


# ---------------------------------------------------------------------------
# PM Agent smoke test (mocked LLM)
# ---------------------------------------------------------------------------


class TestPMAgentSmoke:
    """Run the PM agent graph with a mocked LLM to verify the graph executes."""

    def test_agent_graph_completes(self, demo_engine, tmp_path):
        """Build and invoke a LangGraph graph with a mock LLM that returns
        no tool calls, causing the graph to terminate after one pass.
        Uses the same tools as the real PM agent."""

        from langchain_core.messages import HumanMessage, SystemMessage
        from langgraph.graph import START, StateGraph
        from langgraph.prebuilt import ToolNode, tools_condition

        Factory = sessionmaker(bind=demo_engine)
        journal_dir = tmp_path / "journal"
        journal_dir.mkdir()

        # Mock LLM that returns a plain AIMessage (no tool calls → graph ends)
        mock_llm = MagicMock()
        mock_response = AIMessage(content="Daily loop complete. No actions needed.")
        mock_llm.invoke.return_value = mock_response

        with (
            patch("project_manager_agent.core.services.SessionFactory", Factory),
            patch("project_manager_agent.core.services.JOURNAL_DIR", journal_dir),
        ):
            from project_manager_agent.agents.project_manager.tools import tools

            def pm_node(state: _SmokeState) -> dict:
                response = mock_llm.invoke(state["messages"])
                return {"messages": [response]}

            graph_builder = StateGraph(_SmokeState)
            graph_builder.add_node("project-manager", pm_node)
            graph_builder.add_node("tools", ToolNode(tools=tools))
            graph_builder.add_edge(START, "project-manager")
            graph_builder.add_conditional_edges(
                "project-manager", tools_condition, "tools"
            )
            graph_builder.add_edge("tools", "project-manager")
            graph = graph_builder.compile()

            result = graph.invoke(
                {
                    "messages": [
                        SystemMessage("You are a PM agent."),
                        HumanMessage("Run your daily loop."),
                    ]
                }
            )

            # system + human + AI response
            assert len(result["messages"]) >= 3
            assert mock_llm.invoke.called


# ---------------------------------------------------------------------------
# Reporter context smoke test
# ---------------------------------------------------------------------------


class TestReporterContextSmoke:
    """Verify the reporter can gather and format context from SQL data."""

    def test_load_all_from_sql(self, demo_engine, tmp_path):
        Factory = sessionmaker(bind=demo_engine)
        journal_dir = tmp_path / "journal"
        journal_dir.mkdir()
        (journal_dir / "2026-03-19.md").write_text("# Journal\nPrevious day")

        ref_date = dt.date(2026, 3, 20)
        with (
            patch("project_manager_agent.core.services.SessionFactory", Factory),
            patch("project_manager_agent.core.services.JOURNAL_DIR", journal_dir),
            patch(
                "project_manager_agent.core.db.repositories.REFERENCE_DATE", ref_date
            ),
            patch(
                "project_manager_agent.agents.reporter.context.REFERENCE_DATE", ref_date
            ),
        ):
            from project_manager_agent.agents.reporter.context import (
                load_all,
                format_context,
            )

            ctx = load_all()

            assert ctx["project"].name == "Customer Portal Modernisation"
            assert len(ctx["tasks"]) == 11
            assert len(ctx["complete"]) == 4
            assert len(ctx["blocked"]) == 1
            assert len(ctx["in_progress"]) == 2
            assert len(ctx["open_risks"]) == 2
            assert len(ctx["open_issues"]) == 1
            assert ctx["last_journal"] is not None

            # Format context should produce a non-empty string
            context_str = format_context(ctx)
            assert "Customer Portal Modernisation" in context_str
            assert "AMBER" in context_str
            assert "RISKS" in context_str
            assert "TASKS" in context_str

    def test_reporter_save_report(self, tmp_path):
        """Verify save_report writes a markdown file."""
        ref_date = dt.date(2026, 3, 20)
        with patch(
            "project_manager_agent.agents.reporter.agent.REFERENCE_DATE", ref_date
        ):
            from project_manager_agent.agents.reporter.agent import save_report

            output_path = tmp_path / "test-report.md"
            result = save_report("## Test content", output_path)
            assert result == output_path
            content = output_path.read_text()
            assert "Project Status Report" in content
            assert "Test content" in content
