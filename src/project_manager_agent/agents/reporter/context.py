"""
Reporter — Data gathering and context formatting
=================================================
Loads all project data and formats it into a string suitable for passing to
the report-generation LLM.
"""

import datetime as dt

from project_manager_agent.core.date_utils import REFERENCE_DATE
from project_manager_agent.core.services import ProjectService


def load_all() -> dict:
    """Read all data sources and return a single context dict."""
    svc = ProjectService()
    try:
        project = svc.read_project()
        tasks = svc.read_tasks()
        raid = svc.read_raid()
        actions = svc.read_actions()
        journal = svc.read_last_journal()
    finally:
        svc.close()

    complete = [t for t in tasks if t.status == "complete"]
    blocked = [t for t in tasks if t.status == "blocked"]
    in_progress = [t for t in tasks if t.status == "in_progress"]
    not_started = [t for t in tasks if t.status == "not_started"]
    overdue = [
        t
        for t in tasks
        if t.status not in ("complete",) and t.due_date < REFERENCE_DATE
    ]

    open_risks = [r for r in raid if r.type == "risk" and r.status == "open"]
    open_issues = [r for r in raid if r.type == "issue" and r.status == "open"]
    open_assumptions = [
        r for r in raid if r.type == "assumption" and r.status == "open"
    ]
    decisions = [r for r in raid if r.type == "decision"]

    overdue_actions = [
        a for a in actions if a.status == "open" and a.due_date < REFERENCE_DATE
    ]
    due_soon_actions = [
        a
        for a in actions
        if a.status == "open"
        and REFERENCE_DATE <= a.due_date <= REFERENCE_DATE + dt.timedelta(days=7)
    ]

    return {
        "project": project,
        "tasks": tasks,
        "complete": complete,
        "blocked": blocked,
        "in_progress": in_progress,
        "not_started": not_started,
        "overdue_tasks": overdue,
        "open_risks": open_risks,
        "open_issues": open_issues,
        "open_assumptions": open_assumptions,
        "decisions": decisions,
        "all_actions": actions,
        "overdue_actions": overdue_actions,
        "due_soon_actions": due_soon_actions,
        "last_journal": journal,
    }


def format_context(ctx: dict) -> str:
    """Serialise the context dict to a readable string for the LLM prompt."""
    p = ctx["project"]

    lines = [
        f"TODAY: {REFERENCE_DATE}",
        "",
        "=== PROJECT ===",
        f"Name:           {p.name}",
        f"Description:    {p.description}",
        f"Sponsor:        {p.sponsor}",
        f"Planned end:    {p.planned_end}",
        f"Forecast end:   {p.forecast_end}",
        f"RAG status:     {p.rag_status.upper()}",
        f"RAG reason:     {p.rag_reason}",
        "",
        "Objectives:",
        *[f"  - {o}" for o in p.objectives],
        "",
        "=== PHASES ===",
        *[
            f"  Phase {ph.phase_id}: {ph.name} ({ph.planned_start} → {ph.planned_end})"
            for ph in p.phases
        ],
        "",
        "=== MILESTONES ===",
        *[
            f"  M{m.milestone_id}: {m.name} | "
            f"Planned: {m.planned_date} | Forecast: {m.forecast_date} | "
            f"Status: {m.status} | "
            f"Actual: {m.actual_date or 'n/a'} | "
            f"Gates on tasks: {m.linked_task_ids}"
            for m in p.milestones
        ],
        "",
        "=== TASKS ===",
        *[
            f"  [{t.status.upper()}] Task {t.task_id}: {t.description} "
            f"(owner: {t.owner_name}, due: {t.due_date}, "
            f"priority: {t.priority.upper()}, phase: {t.phase_id}"
            + (f", depends_on: {t.depends_on}" if t.depends_on else "")
            + (f", BLOCKED: {t.blocked_reason}" if t.blocked_reason else "")
            + (f", ext dep: {t.external_dependency}" if t.external_dependency else "")
            + ")"
            for t in ctx["tasks"]
        ],
        "",
        f"Summary — Complete: {len(ctx['complete'])} | "
        f"In progress: {len(ctx['in_progress'])} | "
        f"Not started: {len(ctx['not_started'])} | "
        f"Blocked: {len(ctx['blocked'])} | "
        f"Overdue: {len(ctx['overdue_tasks'])}",
        "",
        "=== RISKS (open) ===",
        *(
            [
                f"  R{r.raid_id}: [{(r.probability or '?').upper()} prob / "
                f"{(r.impact or '?').upper()} impact] {r.title} — "
                f"owner: {r.owner} | mitigation: {r.mitigation or 'none'}"
                for r in ctx["open_risks"]
            ]
            or ["  None"]
        ),
        "",
        "=== ISSUES (open) ===",
        *(
            [
                f"  I{r.raid_id}: [severity: {(r.severity or '?').upper()}] "
                f"{r.title} — owner: {r.owner} | "
                f"resolution: {r.resolution or 'none yet'}"
                for r in ctx["open_issues"]
            ]
            or ["  None"]
        ),
        "",
        "=== ASSUMPTIONS (open, unvalidated) ===",
        *(
            [
                f"  A{r.raid_id}: {r.title} — "
                f"validate by: {r.validation_date or '?'} | "
                f"method: {r.validation_method or '?'}"
                for r in ctx["open_assumptions"]
                if not r.validated_by
            ]
            or ["  None"]
        ),
        "",
        "=== DECISIONS ===",
        *(
            [
                f"  D{r.raid_id}: {r.title} — decided by: "
                f"{r.decided_by or '?'} on {r.decision_date or '?'}"
                for r in ctx["decisions"]
            ]
            or ["  None"]
        ),
        "",
        "=== ACTIONS ===",
        *[
            f"  [{a.status.upper()}] Action {a.action_id}: "
            f"{a.description} — owner: {a.owner_name}, "
            f"due: {a.due_date}"
            + (" [OVERDUE]" if a in ctx["overdue_actions"] else "")
            + (f" [from RAID {a.source_raid_id}]" if a.source_raid_id else "")
            for a in ctx["all_actions"]
        ],
        "",
        "=== LATEST JOURNAL ===",
        ctx["last_journal"] or "No journal found.",
    ]
    return "\n".join(lines)
