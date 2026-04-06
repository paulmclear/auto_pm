"""Seed the database with the Customer Portal Modernisation demo scenario."""

import datetime as dt
import json
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from project_manager_agent.core.db.orm import (
    ActionRow,
    MessageRow,
    MilestoneRow,
    PhaseRow,
    ProjectRow,
    RaidItemRow,
    TaskRow,
)

# Journal directory (project root / data / journal)
_JOURNAL_DIR = Path(__file__).resolve().parents[4] / "data" / "journal"


def _d(iso: str) -> dt.date:
    """Parse an ISO date string into a date object."""
    return dt.date.fromisoformat(iso)


def seed_demo_data(session: Session) -> None:
    """Insert the full Customer Portal Modernisation demo scenario via ORM objects.

    Includes: 1 project with 3 phases and 3 milestones, 11 tasks, 7 RAID items,
    3 actions, 3 messages (2 inbound, 1 outbound), and journal markdown files.
    """

    # ------------------------------------------------------------------
    # Project
    # ------------------------------------------------------------------
    project = ProjectRow(
        name="Customer Portal Modernisation",
        description=(
            "Replace the legacy customer portal with a modern, responsive web "
            "application backed by a new API layer and migrated database."
        ),
        objectives=json.dumps(
            [
                "Deliver a responsive customer portal that reduces support call volume by 20%.",
                "Migrate all customer data to the new database with zero data loss.",
                "Achieve go-live by end of April 2026 with full security sign-off.",
            ]
        ),
        sponsor="Alice (CTO)",
        project_manager="Project Manager Agent",
        planned_start=_d("2026-03-01"),
        planned_end=_d("2026-04-30"),
        actual_start=_d("2026-03-01"),
        forecast_end=_d("2026-05-07"),
        rag_status="amber",
        rag_reason=(
            "Build milestone has slipped by one week due to DBA sign-off delay on "
            "the database schema, blocking the migration task. Frontend and API "
            "development remain on track. Recovery is feasible if the DBA review "
            "is completed by 2026-03-24."
        ),
    )
    session.add(project)
    session.flush()  # populate project.id for FK references

    # ------------------------------------------------------------------
    # Phases
    # ------------------------------------------------------------------
    phases = [
        PhaseRow(
            phase_id=1,
            project_id=project.id,
            name="Discovery",
            description="Stakeholder interviews, requirements capture, and UX research.",
            planned_start=_d("2026-03-01"),
            planned_end=_d("2026-03-10"),
        ),
        PhaseRow(
            phase_id=2,
            project_id=project.id,
            name="Design & Build",
            description="Technical architecture, API development, frontend build, and DB migration.",
            planned_start=_d("2026-03-11"),
            planned_end=_d("2026-04-11"),
        ),
        PhaseRow(
            phase_id=3,
            project_id=project.id,
            name="Testing & Launch",
            description="UAT, security review, performance testing, and go-live.",
            planned_start=_d("2026-04-14"),
            planned_end=_d("2026-04-30"),
        ),
    ]
    session.add_all(phases)

    # ------------------------------------------------------------------
    # Milestones
    # ------------------------------------------------------------------
    milestones = [
        MilestoneRow(
            milestone_id=1,
            project_id=project.id,
            name="Discovery Complete",
            description="All requirements captured, wireframes approved, architecture agreed.",
            planned_date=_d("2026-03-10"),
            forecast_date=_d("2026-03-10"),
            actual_date=_d("2026-03-10"),
            status="achieved",
            linked_task_ids=json.dumps([1, 2, 3, 4]),
        ),
        MilestoneRow(
            milestone_id=2,
            project_id=project.id,
            name="Build Complete",
            description="API, frontend, and database migration all complete and integrated.",
            planned_date=_d("2026-04-11"),
            forecast_date=_d("2026-04-18"),
            actual_date=None,
            status="pending",
            linked_task_ids=json.dumps([5, 6, 7, 8]),
        ),
        MilestoneRow(
            milestone_id=3,
            project_id=project.id,
            name="Go-Live",
            description="New portal live in production, legacy system decommissioned.",
            planned_date=_d("2026-04-30"),
            forecast_date=_d("2026-05-07"),
            actual_date=None,
            status="pending",
            linked_task_ids=json.dumps([9, 10, 11]),
        ),
    ]
    session.add_all(milestones)

    # ------------------------------------------------------------------
    # Tasks (11 total across 3 phases)
    # ------------------------------------------------------------------
    pid = project.id  # project_id FK for child rows

    tasks = [
        # Phase 1 — Discovery (all complete)
        TaskRow(
            task_id=1,
            project_id=pid,
            description="Conduct stakeholder interviews",
            owner_name="Mary",
            owner_email="mary@test.com",
            due_date=_d("2026-03-05"),
            status="complete",
            priority="high",
            phase_id=1,
            depends_on="[]",
        ),
        TaskRow(
            task_id=2,
            project_id=pid,
            description="Write business requirements document",
            owner_name="Mary",
            owner_email="mary@test.com",
            due_date=_d("2026-03-07"),
            status="complete",
            priority="high",
            phase_id=1,
            depends_on=json.dumps([1]),
        ),
        TaskRow(
            task_id=3,
            project_id=pid,
            description="Produce UX wireframes",
            owner_name="Sarah",
            owner_email="sarah@test.com",
            due_date=_d("2026-03-08"),
            status="complete",
            priority="medium",
            phase_id=1,
            depends_on=json.dumps([1]),
        ),
        TaskRow(
            task_id=4,
            project_id=pid,
            description="Design technical architecture",
            owner_name="Chris",
            owner_email="chris@test.com",
            due_date=_d("2026-03-10"),
            status="complete",
            priority="high",
            phase_id=1,
            depends_on=json.dumps([2]),
        ),
        # Phase 2 — Design & Build (in progress / blocked)
        TaskRow(
            task_id=5,
            project_id=pid,
            description="Develop REST API layer",
            owner_name="Chris",
            owner_email="chris@test.com",
            due_date=_d("2026-03-28"),
            status="in_progress",
            priority="high",
            phase_id=2,
            depends_on=json.dumps([4]),
        ),
        TaskRow(
            task_id=6,
            project_id=pid,
            description="Build frontend application",
            owner_name="Sarah",
            owner_email="sarah@test.com",
            due_date=_d("2026-04-04"),
            status="in_progress",
            priority="high",
            phase_id=2,
            depends_on=json.dumps([3, 4]),
        ),
        TaskRow(
            task_id=7,
            project_id=pid,
            description="Migrate database to new schema",
            owner_name="Chris",
            owner_email="chris@test.com",
            due_date=_d("2026-04-04"),
            status="blocked",
            priority="high",
            phase_id=2,
            depends_on=json.dumps([5]),
            blocked_reason=(
                "Awaiting DBA sign-off on schema changes. Raised with Bob (DBA) "
                "on 2026-03-15 — no response yet."
            ),
            external_dependency="DBA team schema review and approval",
        ),
        TaskRow(
            task_id=8,
            project_id=pid,
            description="Integration testing",
            owner_name="Bob",
            owner_email="bob@test.com",
            due_date=_d("2026-04-11"),
            status="not_started",
            priority="medium",
            phase_id=2,
            depends_on=json.dumps([5, 6, 7]),
        ),
        # Phase 3 — Testing & Launch (not started)
        TaskRow(
            task_id=9,
            project_id=pid,
            description="User acceptance testing",
            owner_name="Mary",
            owner_email="mary@test.com",
            due_date=_d("2026-04-22"),
            status="not_started",
            priority="medium",
            phase_id=3,
            depends_on=json.dumps([8]),
        ),
        TaskRow(
            task_id=10,
            project_id=pid,
            description="Security penetration test and sign-off",
            owner_name="Bob",
            owner_email="bob@test.com",
            due_date=_d("2026-04-22"),
            status="not_started",
            priority="high",
            phase_id=3,
            depends_on=json.dumps([8]),
            external_dependency=(
                "External security firm — engagement letter signed, "
                "slot booked for w/c 2026-04-14."
            ),
        ),
        TaskRow(
            task_id=11,
            project_id=pid,
            description="Go-live deployment and cutover",
            owner_name="Chris",
            owner_email="chris@test.com",
            due_date=_d("2026-04-30"),
            status="not_started",
            priority="high",
            phase_id=3,
            depends_on=json.dumps([9, 10]),
        ),
    ]
    session.add_all(tasks)

    # ------------------------------------------------------------------
    # RAID log (7 items)
    # ------------------------------------------------------------------
    raid_items = [
        RaidItemRow(
            raid_id=1,
            project_id=pid,
            type="risk",
            title="DBA resource unavailability causes further migration delay",
            description=(
                "The DBA team is under-resourced and has not yet reviewed the schema "
                "change request submitted on 2026-03-15. Further delay would push the "
                "database migration past its window and cascade to integration testing."
            ),
            owner="Bob",
            raised_date=_d("2026-03-15"),
            status="open",
            linked_task_ids=json.dumps([7, 8]),
            probability="high",
            impact="high",
            mitigation=(
                "Escalate to DBA team lead by 2026-03-21. Identify a secondary DBA "
                "who can deputise if primary reviewer remains unavailable."
            ),
            review_date=_d("2026-03-21"),
        ),
        RaidItemRow(
            raid_id=2,
            project_id=pid,
            type="risk",
            title="Breaking changes to third-party payment API",
            description=(
                "The payment provider has announced an API v3 deprecation with a "
                "90-day notice. If our integration targets v2, we may need emergency "
                "rework before go-live."
            ),
            owner="Chris",
            raised_date=_d("2026-03-12"),
            status="open",
            linked_task_ids=json.dumps([5, 11]),
            probability="medium",
            impact="high",
            mitigation=(
                "Chris to confirm which API version is targeted and document a "
                "versioning strategy by 2026-03-28."
            ),
            review_date=_d("2026-03-28"),
        ),
        RaidItemRow(
            raid_id=3,
            project_id=pid,
            type="assumption",
            title="Cloud infrastructure will be provisioned before build phase ends",
            description=(
                "We are assuming that the cloud hosting environment (staging and "
                "production) will be provisioned by the internal infrastructure team "
                "in time for integration testing to start on 2026-04-14."
            ),
            owner="Mary",
            raised_date=_d("2026-03-01"),
            status="open",
            linked_task_ids=json.dumps([8, 9, 10, 11]),
            validation_method="Confirm provisioning timeline with infra team lead.",
            validation_date=_d("2026-03-20"),
        ),
        RaidItemRow(
            raid_id=4,
            project_id=pid,
            type="assumption",
            title="Users will be available for UAT during w/c 2026-04-14",
            description=(
                "We are assuming that at least 10 representative users can participate "
                "in UAT sessions during the week of 2026-04-14."
            ),
            owner="Mary",
            raised_date=_d("2026-03-01"),
            status="open",
            linked_task_ids=json.dumps([9]),
            validation_method="Mary to confirm UAT participant list with business leads.",
            validation_date=_d("2026-03-25"),
        ),
        RaidItemRow(
            raid_id=5,
            project_id=pid,
            type="issue",
            title="DBA schema sign-off delayed — blocking database migration",
            description=(
                "The schema change request submitted to the DBA team on 2026-03-15 "
                "has not been reviewed. Task 7 (database migration) cannot begin "
                "until sign-off is received, and the delay is now five days."
            ),
            owner="Bob",
            raised_date=_d("2026-03-20"),
            status="open",
            linked_task_ids=json.dumps([7]),
            severity="high",
        ),
        RaidItemRow(
            raid_id=6,
            project_id=pid,
            type="decision",
            title="Use React for the frontend application",
            description=(
                "Agreed to use React (with TypeScript) as the frontend framework "
                "rather than Vue or Angular."
            ),
            owner="Chris",
            raised_date=_d("2026-03-05"),
            status="closed",
            linked_task_ids=json.dumps([6]),
            rationale=(
                "Team has strongest existing React skills. Large component ecosystem "
                "reduces build time. Vue and Angular both considered but rejected due "
                "to lower team familiarity."
            ),
            decided_by="Chris",
            decision_date=_d("2026-03-05"),
            alternatives_considered=(
                "Vue 3 (good ecosystem, less team familiarity); "
                "Angular (rejected — overkill for this scale)."
            ),
        ),
        RaidItemRow(
            raid_id=7,
            project_id=pid,
            type="decision",
            title="Defer mobile native app to a follow-on project",
            description=(
                "A native mobile app was in scope in the original brief. Agreed "
                "to descope it from this project and treat it as a follow-on initiative."
            ),
            owner="Alice",
            raised_date=_d("2026-03-15"),
            status="closed",
            linked_task_ids="[]",
            rationale=(
                "The responsive web portal will be accessible on mobile browsers, "
                "covering the primary use cases. A native app adds 6+ weeks and "
                "would push go-live past the business deadline."
            ),
            decided_by="Alice",
            decision_date=_d("2026-03-15"),
            alternatives_considered=(
                "Keep mobile app in scope (rejected — timeline impact unacceptable)."
            ),
        ),
    ]
    session.add_all(raid_items)

    # ------------------------------------------------------------------
    # Actions (3)
    # ------------------------------------------------------------------
    actions = [
        ActionRow(
            action_id=1,
            project_id=pid,
            description=(
                "Escalate DBA schema sign-off to DBA team lead — request review "
                "be completed by 2026-03-24."
            ),
            owner_name="Bob",
            owner_email="bob@test.com",
            due_date=_d("2026-03-15"),  # overdue
            status="open",
            source_raid_id=1,
            source_task_id=7,
        ),
        ActionRow(
            action_id=2,
            project_id=pid,
            description=(
                "Confirm cloud infrastructure provisioning timeline with the "
                "infrastructure team lead and update the project plan."
            ),
            owner_name="Mary",
            owner_email="mary@test.com",
            due_date=_d("2026-03-22"),
            status="open",
            source_raid_id=3,
        ),
        ActionRow(
            action_id=3,
            project_id=pid,
            description=(
                "Document the API versioning strategy and confirm whether the "
                "payment integration targets v2 or v3 of the provider API."
            ),
            owner_name="Chris",
            owner_email="chris@test.com",
            due_date=_d("2026-03-28"),
            status="open",
            source_raid_id=2,
        ),
    ]
    session.add_all(actions)

    # ------------------------------------------------------------------
    # Messages (2 inbound + 1 outbound)
    # ------------------------------------------------------------------
    messages = [
        MessageRow(
            message_id=str(uuid.uuid4()),
            project_id=pid,
            direction="inbound",
            timestamp="2026-03-20T08:14:00",
            owner_name="Chris",
            owner_email="chris@test.com",
            message=(
                "Just a heads-up — the database schema is still with the DBA team. "
                "I chased again yesterday but no response. This is now blocking my "
                "migration work. Can we get this escalated? API development is going "
                "well and I expect to have a working build by next Friday."
            ),
            sender_name="Chris",
            sender_email="chris@test.com",
        ),
        MessageRow(
            message_id=str(uuid.uuid4()),
            project_id=pid,
            direction="inbound",
            timestamp="2026-03-20T09:02:00",
            owner_name="Sarah",
            owner_email="sarah@test.com",
            message=(
                "Frontend is on track. I expect to complete the main views by "
                "2026-04-04 as planned. No blockers at the moment."
            ),
            sender_name="Sarah",
            sender_email="sarah@test.com",
        ),
        MessageRow(
            message_id=str(uuid.uuid4()),
            project_id=pid,
            direction="outbound",
            timestamp="2026-03-18T09:00:00",
            owner_name="Bob",
            owner_email="bob@test.com",
            message=(
                "Hi Bob, this is a reminder that Action 1 is overdue: please escalate "
                "the DBA schema sign-off to the DBA team lead. This is blocking the "
                "database migration task (Task 7). Please provide an update by end of day."
            ),
            sender_name="Project Manager Agent",
            sender_email="pm-agent@test.com",
        ),
    ]
    session.add_all(messages)

    # ------------------------------------------------------------------
    # Journal markdown files
    # ------------------------------------------------------------------
    _seed_journals()

    session.flush()


def _seed_journals() -> None:
    """Write journal markdown files for the demo dates."""
    _JOURNAL_DIR.mkdir(parents=True, exist_ok=True)

    journals = {
        "2026-03-18": (
            "# Journal — 2026-03-18\n\n"
            "## Summary\n"
            "Reviewed project status. Discovery phase complete. Design & Build "
            "phase underway with API and frontend work in progress. Database "
            "migration is blocked awaiting DBA sign-off — sent reminder to Bob.\n\n"
            "## Key Observations\n"
            "- Task 7 (database migration) blocked since 2026-03-15\n"
            "- Sent overdue reminder to Bob regarding Action 1 (DBA escalation)\n"
            "- API development (Task 5) and frontend (Task 6) progressing on schedule\n\n"
            "## Actions Taken\n"
            "- Sent reminder to Bob about overdue Action 1\n"
            "- Updated RAG status to AMBER due to milestone slip risk\n"
        ),
        "2026-03-19": (
            "# Journal — 2026-03-19\n\n"
            "## Summary\n"
            "No response yet from Bob on DBA escalation. Build milestone forecast "
            "slipped to 2026-04-18 (one week). Go-live forecast updated to "
            "2026-05-07. RAG remains AMBER.\n\n"
            "## Key Observations\n"
            "- DBA sign-off still outstanding — 4 days overdue\n"
            "- Build Complete milestone slipped: 2026-04-11 → 2026-04-18\n"
            "- Go-Live milestone slipped: 2026-04-30 → 2026-05-07\n"
            "- Recovery feasible if DBA review completed by 2026-03-24\n\n"
            "## Actions Taken\n"
            "- Updated milestone forecast dates\n"
            "- Updated RAG reason to reflect milestone slip\n"
        ),
    }

    for date_str, content in journals.items():
        path = _JOURNAL_DIR / f"{date_str}.md"
        if not path.exists():
            path.write_text(content, encoding="utf-8")
