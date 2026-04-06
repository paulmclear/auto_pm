"""Seed the database with demo project scenarios."""

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


def seed_all_demo_data(session: Session) -> list[int]:
    """Seed all demo projects. Returns list of project IDs created."""
    pid1 = seed_demo_data(session)
    pid2 = seed_data_platform_project(session)
    pid3 = seed_mobile_app_project(session)
    return [pid1, pid2, pid3]


def seed_demo_data(session: Session) -> int:
    """Insert the Customer Portal Modernisation demo scenario.

    Returns the project ID.
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
    _seed_journals(project.id)

    session.flush()
    return project.id


def _seed_journals(project_id: int, journals: dict[str, str] | None = None) -> None:
    """Write journal markdown files for a project.

    If *journals* is None, writes the default Customer Portal journals.
    """
    journal_dir = _JOURNAL_DIR / str(project_id)
    journal_dir.mkdir(parents=True, exist_ok=True)

    if journals is None:
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
        path = journal_dir / f"{date_str}.md"
        if not path.exists():
            path.write_text(content, encoding="utf-8")


def seed_data_platform_project(session: Session) -> int:
    """Insert the Data Platform Migration demo scenario. Returns the project ID."""

    project = ProjectRow(
        name="Data Platform Migration",
        description=(
            "Migrate the legacy on-premise data warehouse to a cloud-based "
            "lakehouse architecture using Databricks, replacing aging ETL "
            "pipelines with modern streaming ingestion."
        ),
        objectives=json.dumps(
            [
                "Migrate 100% of critical reporting pipelines to the new platform.",
                "Reduce average ETL job runtime by 60%.",
                "Achieve SOC 2 compliance for the new data platform by go-live.",
            ]
        ),
        sponsor="David (VP Engineering)",
        project_manager="Project Manager Agent",
        planned_start=_d("2026-02-15"),
        planned_end=_d("2026-05-15"),
        actual_start=_d("2026-02-15"),
        forecast_end=_d("2026-05-15"),
        rag_status="green",
        rag_reason=(
            "All workstreams on track. Infrastructure provisioning complete, "
            "first batch of pipelines migrated successfully. Team velocity "
            "is steady."
        ),
    )
    session.add(project)
    session.flush()
    pid = project.id

    # Phases
    phases = [
        PhaseRow(
            phase_id=100,
            project_id=pid,
            name="Assessment & Planning",
            description="Audit existing pipelines, design target architecture, set up cloud infra.",
            planned_start=_d("2026-02-15"),
            planned_end=_d("2026-03-07"),
        ),
        PhaseRow(
            phase_id=101,
            project_id=pid,
            name="Migration & Build",
            description="Migrate pipelines in priority order, build new streaming layer.",
            planned_start=_d("2026-03-10"),
            planned_end=_d("2026-04-25"),
        ),
        PhaseRow(
            phase_id=102,
            project_id=pid,
            name="Validation & Cutover",
            description="Data quality checks, parallel run, cutover, decommission legacy.",
            planned_start=_d("2026-04-28"),
            planned_end=_d("2026-05-15"),
        ),
    ]
    session.add_all(phases)

    # Milestones
    milestones = [
        MilestoneRow(
            milestone_id=100,
            project_id=pid,
            name="Architecture Approved",
            description="Target lakehouse architecture reviewed and signed off.",
            planned_date=_d("2026-03-07"),
            forecast_date=_d("2026-03-07"),
            actual_date=_d("2026-03-06"),
            status="achieved",
            linked_task_ids=json.dumps([100, 101, 102]),
        ),
        MilestoneRow(
            milestone_id=101,
            project_id=pid,
            name="Core Pipelines Migrated",
            description="Top 20 priority pipelines running on new platform.",
            planned_date=_d("2026-04-11"),
            forecast_date=_d("2026-04-11"),
            actual_date=None,
            status="pending",
            linked_task_ids=json.dumps([103, 104, 105]),
        ),
        MilestoneRow(
            milestone_id=102,
            project_id=pid,
            name="Production Cutover",
            description="Legacy warehouse decommissioned, all traffic on new platform.",
            planned_date=_d("2026-05-15"),
            forecast_date=_d("2026-05-15"),
            actual_date=None,
            status="pending",
            linked_task_ids=json.dumps([106, 107, 108]),
        ),
    ]
    session.add_all(milestones)

    # Tasks (9 total)
    tasks = [
        # Phase 1 — Assessment (complete)
        TaskRow(
            task_id=100,
            project_id=pid,
            description="Audit and catalog existing ETL pipelines",
            owner_name="Priya",
            owner_email="priya@test.com",
            due_date=_d("2026-02-21"),
            status="complete",
            priority="high",
            phase_id=100,
            depends_on="[]",
        ),
        TaskRow(
            task_id=101,
            project_id=pid,
            description="Design lakehouse target architecture",
            owner_name="James",
            owner_email="james@test.com",
            due_date=_d("2026-02-28"),
            status="complete",
            priority="high",
            phase_id=100,
            depends_on=json.dumps([100]),
        ),
        TaskRow(
            task_id=102,
            project_id=pid,
            description="Provision cloud infrastructure (Databricks, S3, networking)",
            owner_name="James",
            owner_email="james@test.com",
            due_date=_d("2026-03-07"),
            status="complete",
            priority="high",
            phase_id=100,
            depends_on=json.dumps([101]),
        ),
        # Phase 2 — Migration (in progress)
        TaskRow(
            task_id=103,
            project_id=pid,
            description="Migrate batch reporting pipelines (priority 1-10)",
            owner_name="Priya",
            owner_email="priya@test.com",
            due_date=_d("2026-03-28"),
            status="in_progress",
            priority="high",
            phase_id=101,
            depends_on=json.dumps([102]),
        ),
        TaskRow(
            task_id=104,
            project_id=pid,
            description="Migrate batch reporting pipelines (priority 11-20)",
            owner_name="Lena",
            owner_email="lena@test.com",
            due_date=_d("2026-04-11"),
            status="not_started",
            priority="medium",
            phase_id=101,
            depends_on=json.dumps([103]),
        ),
        TaskRow(
            task_id=105,
            project_id=pid,
            description="Build real-time streaming ingestion layer",
            owner_name="James",
            owner_email="james@test.com",
            due_date=_d("2026-04-18"),
            status="in_progress",
            priority="high",
            phase_id=101,
            depends_on=json.dumps([102]),
        ),
        # Phase 3 — Validation & Cutover (not started)
        TaskRow(
            task_id=106,
            project_id=pid,
            description="Run parallel data quality validation (old vs new)",
            owner_name="Priya",
            owner_email="priya@test.com",
            due_date=_d("2026-05-02"),
            status="not_started",
            priority="high",
            phase_id=102,
            depends_on=json.dumps([104, 105]),
        ),
        TaskRow(
            task_id=107,
            project_id=pid,
            description="SOC 2 compliance audit for new platform",
            owner_name="Lena",
            owner_email="lena@test.com",
            due_date=_d("2026-05-09"),
            status="not_started",
            priority="high",
            phase_id=102,
            depends_on=json.dumps([106]),
            external_dependency="External auditor — engagement confirmed for w/c 2026-05-04.",
        ),
        TaskRow(
            task_id=108,
            project_id=pid,
            description="Production cutover and legacy decommission",
            owner_name="James",
            owner_email="james@test.com",
            due_date=_d("2026-05-15"),
            status="not_started",
            priority="high",
            phase_id=102,
            depends_on=json.dumps([106, 107]),
        ),
    ]
    session.add_all(tasks)

    # RAID (4 items)
    raid_items = [
        RaidItemRow(
            raid_id=100,
            project_id=pid,
            type="risk",
            title="Streaming ingestion latency may exceed SLA for real-time dashboards",
            description=(
                "The target p99 latency for streaming data is 5 seconds. Initial "
                "benchmarks show 4.2s but under peak load this could breach the SLA."
            ),
            owner="James",
            raised_date=_d("2026-03-12"),
            status="open",
            linked_task_ids=json.dumps([105]),
            probability="medium",
            impact="high",
            mitigation="Run load test by 2026-04-04; plan auto-scaling fallback.",
            review_date=_d("2026-04-04"),
        ),
        RaidItemRow(
            raid_id=101,
            project_id=pid,
            type="assumption",
            title="Legacy warehouse can remain read-only during parallel run",
            description=(
                "We assume the legacy system can be set to read-only for the 2-week "
                "parallel validation period without impacting downstream consumers."
            ),
            owner="Priya",
            raised_date=_d("2026-02-20"),
            status="open",
            linked_task_ids=json.dumps([106]),
            validation_method="Confirm with ops team that no write jobs target the legacy warehouse.",
            validation_date=_d("2026-04-18"),
        ),
        RaidItemRow(
            raid_id=102,
            project_id=pid,
            type="decision",
            title="Use Delta Lake format for the lakehouse storage layer",
            description="Chose Delta Lake over Apache Iceberg for table format.",
            owner="James",
            raised_date=_d("2026-02-25"),
            status="closed",
            linked_task_ids=json.dumps([101]),
            rationale="Better Databricks integration, team familiarity, ACID guarantees.",
            decided_by="James",
            decision_date=_d("2026-02-25"),
            alternatives_considered="Apache Iceberg (good but less Databricks-native); Apache Hudi (rejected — less mature).",
        ),
        RaidItemRow(
            raid_id=103,
            project_id=pid,
            type="issue",
            title="Three legacy pipelines have undocumented dependencies",
            description=(
                "During audit, Priya found 3 pipelines with dependencies on an "
                "undocumented shared lookup table. Migration requires reverse-engineering "
                "these before they can be ported."
            ),
            owner="Priya",
            raised_date=_d("2026-03-18"),
            status="open",
            linked_task_ids=json.dumps([103]),
            severity="medium",
        ),
    ]
    session.add_all(raid_items)

    # Actions (2)
    actions = [
        ActionRow(
            action_id=100,
            project_id=pid,
            description="Run streaming load test and document p99 latency results.",
            owner_name="James",
            owner_email="james@test.com",
            due_date=_d("2026-04-04"),
            status="open",
            source_raid_id=100,
        ),
        ActionRow(
            action_id=101,
            project_id=pid,
            description="Reverse-engineer undocumented pipeline dependencies and document them.",
            owner_name="Priya",
            owner_email="priya@test.com",
            due_date=_d("2026-03-25"),
            status="open",
            source_raid_id=103,
            source_task_id=103,
        ),
    ]
    session.add_all(actions)

    # Messages (2)
    messages = [
        MessageRow(
            message_id=str(uuid.uuid4()),
            project_id=pid,
            direction="inbound",
            timestamp="2026-03-20T10:30:00",
            owner_name="Priya",
            owner_email="priya@test.com",
            message=(
                "First 5 pipelines are migrated and passing validation. Found 3 with "
                "undocumented deps — raised as an issue. On track to finish batch 1 "
                "by 2026-03-28."
            ),
            sender_name="Priya",
            sender_email="priya@test.com",
        ),
        MessageRow(
            message_id=str(uuid.uuid4()),
            project_id=pid,
            direction="inbound",
            timestamp="2026-03-20T11:15:00",
            owner_name="James",
            owner_email="james@test.com",
            message=(
                "Streaming layer prototype is working. Initial latency benchmarks "
                "look good (p99 = 4.2s against 5s SLA). Will run full load test "
                "next week."
            ),
            sender_name="James",
            sender_email="james@test.com",
        ),
    ]
    session.add_all(messages)

    # Journals
    _seed_journals(
        pid,
        {
            "2026-03-18": (
                "# Journal — 2026-03-18\n\n"
                "## Summary\n"
                "Assessment phase complete. Cloud infrastructure provisioned ahead "
                "of schedule. Migration phase started — Priya beginning pipeline "
                "batch 1, James prototyping streaming layer.\n\n"
                "## Key Observations\n"
                "- All 3 assessment tasks complete\n"
                "- Architecture Approved milestone achieved on 2026-03-06\n"
                "- Migration work ramping up on schedule\n\n"
                "## Actions Taken\n"
                "- Confirmed migration priority list with stakeholders\n"
            ),
            "2026-03-19": (
                "# Journal — 2026-03-19\n\n"
                "## Summary\n"
                "Good progress on migration. Priya reports 5 of 10 priority "
                "pipelines migrated. Streaming prototype showing promising latency. "
                "RAG remains GREEN.\n\n"
                "## Key Observations\n"
                "- Pipeline migration at 50% for batch 1\n"
                "- Streaming p99 latency at 4.2s (within 5s SLA)\n"
                "- Discovered 3 undocumented pipeline dependencies\n\n"
                "## Actions Taken\n"
                "- Created issue for undocumented dependencies\n"
                "- Assigned Priya to reverse-engineer before continuing migration\n"
            ),
        },
    )

    session.flush()
    return pid


def seed_mobile_app_project(session: Session) -> int:
    """Insert the Mobile Banking App Refresh demo scenario. Returns the project ID."""

    project = ProjectRow(
        name="Mobile Banking App Refresh",
        description=(
            "Redesign and rebuild the mobile banking app with a new UI, "
            "biometric authentication, and real-time transaction notifications."
        ),
        objectives=json.dumps(
            [
                "Increase mobile app store rating from 3.2 to 4.5 stars.",
                "Reduce customer support tickets related to mobile by 30%.",
                "Launch on both iOS and Android by end of May 2026.",
            ]
        ),
        sponsor="Elena (Head of Digital)",
        project_manager="Project Manager Agent",
        planned_start=_d("2026-03-01"),
        planned_end=_d("2026-05-30"),
        actual_start=_d("2026-03-01"),
        forecast_end=_d("2026-06-06"),
        rag_status="red",
        rag_reason=(
            "Biometric SDK integration has hit a critical compatibility issue "
            "with Android 14. Vendor has acknowledged the bug but no fix ETA. "
            "This blocks the authentication module and cascades to beta launch."
        ),
    )
    session.add(project)
    session.flush()
    pid = project.id

    # Phases
    phases = [
        PhaseRow(
            phase_id=200,
            project_id=pid,
            name="Design & Prototyping",
            description="User research, UI/UX design, interactive prototypes.",
            planned_start=_d("2026-03-01"),
            planned_end=_d("2026-03-21"),
        ),
        PhaseRow(
            phase_id=201,
            project_id=pid,
            name="Development",
            description="Core app development, API integration, biometric auth.",
            planned_start=_d("2026-03-24"),
            planned_end=_d("2026-05-02"),
        ),
        PhaseRow(
            phase_id=202,
            project_id=pid,
            name="Beta & Launch",
            description="Beta testing, app store submission, staged rollout.",
            planned_start=_d("2026-05-05"),
            planned_end=_d("2026-05-30"),
        ),
    ]
    session.add_all(phases)

    # Milestones
    milestones = [
        MilestoneRow(
            milestone_id=200,
            project_id=pid,
            name="Design Sign-off",
            description="Final UI designs and prototype approved by stakeholders.",
            planned_date=_d("2026-03-21"),
            forecast_date=_d("2026-03-21"),
            actual_date=_d("2026-03-20"),
            status="achieved",
            linked_task_ids=json.dumps([200, 201, 202]),
        ),
        MilestoneRow(
            milestone_id=201,
            project_id=pid,
            name="Feature Complete",
            description="All app features developed and integrated.",
            planned_date=_d("2026-05-02"),
            forecast_date=_d("2026-05-09"),
            actual_date=None,
            status="pending",
            linked_task_ids=json.dumps([203, 204, 205, 206]),
        ),
        MilestoneRow(
            milestone_id=202,
            project_id=pid,
            name="App Store Launch",
            description="App published on iOS App Store and Google Play.",
            planned_date=_d("2026-05-30"),
            forecast_date=_d("2026-06-06"),
            actual_date=None,
            status="pending",
            linked_task_ids=json.dumps([207, 208]),
        ),
    ]
    session.add_all(milestones)

    # Tasks (9 total)
    tasks = [
        # Phase 1 — Design (complete)
        TaskRow(
            task_id=200,
            project_id=pid,
            description="Conduct user research and define personas",
            owner_name="Anika",
            owner_email="anika@test.com",
            due_date=_d("2026-03-07"),
            status="complete",
            priority="high",
            phase_id=200,
            depends_on="[]",
        ),
        TaskRow(
            task_id=201,
            project_id=pid,
            description="Create high-fidelity UI mockups",
            owner_name="Anika",
            owner_email="anika@test.com",
            due_date=_d("2026-03-14"),
            status="complete",
            priority="high",
            phase_id=200,
            depends_on=json.dumps([200]),
        ),
        TaskRow(
            task_id=202,
            project_id=pid,
            description="Build interactive prototype and run usability tests",
            owner_name="Anika",
            owner_email="anika@test.com",
            due_date=_d("2026-03-21"),
            status="complete",
            priority="medium",
            phase_id=200,
            depends_on=json.dumps([201]),
        ),
        # Phase 2 — Development (in progress / blocked)
        TaskRow(
            task_id=203,
            project_id=pid,
            description="Develop core app shell and navigation (React Native)",
            owner_name="Tom",
            owner_email="tom@test.com",
            due_date=_d("2026-04-04"),
            status="in_progress",
            priority="high",
            phase_id=201,
            depends_on=json.dumps([202]),
        ),
        TaskRow(
            task_id=204,
            project_id=pid,
            description="Integrate biometric authentication SDK",
            owner_name="Tom",
            owner_email="tom@test.com",
            due_date=_d("2026-04-18"),
            status="blocked",
            priority="high",
            phase_id=201,
            depends_on=json.dumps([203]),
            blocked_reason=(
                "Vendor SDK has a critical bug on Android 14 causing crash on "
                "fingerprint enrollment. Vendor ticket #4821 opened 2026-03-18, "
                "no fix ETA provided."
            ),
            external_dependency="Biometric SDK vendor — bug fix for Android 14 compatibility.",
        ),
        TaskRow(
            task_id=205,
            project_id=pid,
            description="Build real-time transaction notification service",
            owner_name="Raj",
            owner_email="raj@test.com",
            due_date=_d("2026-04-18"),
            status="in_progress",
            priority="high",
            phase_id=201,
            depends_on=json.dumps([203]),
        ),
        TaskRow(
            task_id=206,
            project_id=pid,
            description="Integrate banking API and account views",
            owner_name="Raj",
            owner_email="raj@test.com",
            due_date=_d("2026-05-02"),
            status="not_started",
            priority="high",
            phase_id=201,
            depends_on=json.dumps([203]),
        ),
        # Phase 3 — Beta & Launch (not started)
        TaskRow(
            task_id=207,
            project_id=pid,
            description="Beta testing program (500 users)",
            owner_name="Anika",
            owner_email="anika@test.com",
            due_date=_d("2026-05-16"),
            status="not_started",
            priority="medium",
            phase_id=202,
            depends_on=json.dumps([204, 205, 206]),
        ),
        TaskRow(
            task_id=208,
            project_id=pid,
            description="App store submission and staged rollout",
            owner_name="Tom",
            owner_email="tom@test.com",
            due_date=_d("2026-05-30"),
            status="not_started",
            priority="high",
            phase_id=202,
            depends_on=json.dumps([207]),
        ),
    ]
    session.add_all(tasks)

    # RAID (5 items)
    raid_items = [
        RaidItemRow(
            raid_id=200,
            project_id=pid,
            type="risk",
            title="Biometric SDK vendor may not fix Android 14 bug in time",
            description=(
                "The biometric SDK crashes on Android 14 fingerprint enrollment. "
                "If the vendor does not release a fix by 2026-04-11, we will need "
                "to evaluate alternative SDKs, adding 2-3 weeks."
            ),
            owner="Tom",
            raised_date=_d("2026-03-18"),
            status="open",
            linked_task_ids=json.dumps([204]),
            probability="high",
            impact="high",
            mitigation=(
                "Evaluate FingerprintJS and native BiometricPrompt as fallback "
                "options by 2026-04-04. Escalate to vendor management."
            ),
            review_date=_d("2026-04-04"),
        ),
        RaidItemRow(
            raid_id=201,
            project_id=pid,
            type="risk",
            title="App store review may reject first submission",
            description=(
                "Apple's review process has become stricter on biometric apps. "
                "First submission rejection would add 1-2 weeks."
            ),
            owner="Tom",
            raised_date=_d("2026-03-10"),
            status="open",
            linked_task_ids=json.dumps([208]),
            probability="medium",
            impact="medium",
            mitigation="Review Apple's latest guidelines and prepare compliance documentation ahead of submission.",
            review_date=_d("2026-05-09"),
        ),
        RaidItemRow(
            raid_id=202,
            project_id=pid,
            type="issue",
            title="Biometric SDK crashes on Android 14 — blocking authentication module",
            description=(
                "Vendor SDK v3.2 throws a fatal exception during fingerprint "
                "enrollment on Android 14 devices. Vendor acknowledges the bug "
                "(ticket #4821) but has not provided an ETA for a fix."
            ),
            owner="Tom",
            raised_date=_d("2026-03-18"),
            status="open",
            linked_task_ids=json.dumps([204]),
            severity="critical",
        ),
        RaidItemRow(
            raid_id=203,
            project_id=pid,
            type="assumption",
            title="Banking API will support real-time push notifications",
            description=(
                "We assume the core banking API team will expose a webhook/SSE "
                "endpoint for transaction events by 2026-04-11."
            ),
            owner="Raj",
            raised_date=_d("2026-03-05"),
            status="open",
            linked_task_ids=json.dumps([205]),
            validation_method="Confirm with banking API team lead that webhook endpoint is on their Q2 roadmap.",
            validation_date=_d("2026-03-25"),
        ),
        RaidItemRow(
            raid_id=204,
            project_id=pid,
            type="decision",
            title="Use React Native for cross-platform development",
            description="Chose React Native over Flutter for the mobile app framework.",
            owner="Tom",
            raised_date=_d("2026-03-03"),
            status="closed",
            linked_task_ids=json.dumps([203]),
            rationale="Existing team has strong React expertise. Shared codebase reduces effort by ~40%.",
            decided_by="Tom",
            decision_date=_d("2026-03-03"),
            alternatives_considered="Flutter (good performance, but team would need ramp-up); Native (rejected — double the effort).",
        ),
    ]
    session.add_all(raid_items)

    # Actions (3)
    actions = [
        ActionRow(
            action_id=200,
            project_id=pid,
            description="Escalate biometric SDK bug to vendor management and request fix ETA.",
            owner_name="Tom",
            owner_email="tom@test.com",
            due_date=_d("2026-03-20"),
            status="open",
            source_raid_id=200,
            source_task_id=204,
        ),
        ActionRow(
            action_id=201,
            project_id=pid,
            description="Evaluate FingerprintJS and native BiometricPrompt as fallback SDK options.",
            owner_name="Tom",
            owner_email="tom@test.com",
            due_date=_d("2026-04-04"),
            status="open",
            source_raid_id=200,
        ),
        ActionRow(
            action_id=202,
            project_id=pid,
            description="Confirm banking API webhook endpoint availability with API team lead.",
            owner_name="Raj",
            owner_email="raj@test.com",
            due_date=_d("2026-03-25"),
            status="open",
            source_raid_id=203,
            source_task_id=205,
        ),
    ]
    session.add_all(actions)

    # Messages (2 inbound)
    messages = [
        MessageRow(
            message_id=str(uuid.uuid4()),
            project_id=pid,
            direction="inbound",
            timestamp="2026-03-20T08:45:00",
            owner_name="Tom",
            owner_email="tom@test.com",
            message=(
                "Bad news on the biometric front — the SDK crash on Android 14 is "
                "confirmed as a vendor bug. I've opened ticket #4821 but they haven't "
                "given us an ETA. I'm blocked on the auth module until this is resolved. "
                "Should I start evaluating alternatives?"
            ),
            sender_name="Tom",
            sender_email="tom@test.com",
        ),
        MessageRow(
            message_id=str(uuid.uuid4()),
            project_id=pid,
            direction="inbound",
            timestamp="2026-03-20T09:20:00",
            owner_name="Raj",
            owner_email="raj@test.com",
            message=(
                "Notification service prototype is working with mock events. I need "
                "the banking API webhook endpoint to go live for real integration. "
                "Waiting on confirmation from the API team — will chase this week."
            ),
            sender_name="Raj",
            sender_email="raj@test.com",
        ),
    ]
    session.add_all(messages)

    # Journals
    _seed_journals(
        pid,
        {
            "2026-03-18": (
                "# Journal — 2026-03-18\n\n"
                "## Summary\n"
                "Design phase wrapping up — usability tests positive. Development "
                "phase prep underway. Tom flagged a potential issue with the "
                "biometric SDK on Android 14.\n\n"
                "## Key Observations\n"
                "- Design Sign-off milestone on track for 2026-03-21\n"
                "- Biometric SDK showing crash on Android 14 — investigating\n"
                "- Raj starting notification service prototype\n\n"
                "## Actions Taken\n"
                "- Asked Tom to file a bug with the SDK vendor\n"
            ),
            "2026-03-19": (
                "# Journal — 2026-03-19\n\n"
                "## Summary\n"
                "Biometric SDK bug confirmed as vendor issue — no fix ETA. This is "
                "now a critical blocker. RAG moved to RED. Feature Complete milestone "
                "forecast slipped by one week.\n\n"
                "## Key Observations\n"
                "- Vendor ticket #4821 open, no ETA\n"
                "- Task 204 (biometric auth) blocked\n"
                "- Feature Complete: 2026-05-02 → 2026-05-09\n"
                "- App Store Launch: 2026-05-30 → 2026-06-06\n\n"
                "## Actions Taken\n"
                "- Updated RAG to RED\n"
                "- Created actions for SDK escalation and fallback evaluation\n"
            ),
        },
    )

    session.flush()
    return pid
