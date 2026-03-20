"""
Weekly Summary Report Generator
================================
Generates a markdown summary covering all journals from the past 7 days:
tasks completed, tasks now overdue, tasks at risk, key decisions made, and
open blockers. Output to data/reports/YYYY-Www.md.

Run from the project root:
    python -m project_manager_agent.agents.reporter.weekly
    python -m project_manager_agent.agents.reporter.weekly --output path/to/report.md
"""

import argparse
import datetime as dt
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from project_manager_agent.core.date_utils import REFERENCE_DATE
from project_manager_agent.core.services import ProjectService

load_dotenv(override=True)

REPORTS_DIR = Path("data/reports")

WEEKLY_SYSTEM_PROMPT = """\
You are a senior project manager producing a concise, professional weekly
summary report. You will be given journal entries from the past week and
current project state. Produce a well-formatted markdown report.

Tone: clear, factual, and concise. Senior readers skim — use tables and
bullets. The report should stand alone.

Required sections (use exactly these headings):

## Executive Summary
2-3 sentences. State the project name, reporting period, current RAG, and
the single most important takeaway from the week.

## Tasks Completed This Week
Bullet list of tasks completed during the period. Derive from journal entries
and current task statuses. If none, say so.

## Tasks Now Overdue
Bullet list of tasks that are currently overdue (past due date, not complete).
Include task ID, description, owner, due date, and how many days overdue.
If none, say so.

## Tasks at Risk
Bullet list of tasks that are in progress but at risk of slipping — blocked
tasks, tasks with unresolved dependencies, or tasks due within the next 7 days
that show signs of delay in journal entries. If none, say so.

## Key Decisions Made
Bullet list of key decisions recorded in journals or the RAID log during the
period. If none, say so.

## Open Blockers
Bullet list of unresolved blockers affecting the project. Include blocked tasks,
open HIGH-severity issues, and any escalation items from the journals. If none,
say "No open blockers at this time."

## Week Ahead
Brief bullet list of the most important tasks and milestones for the coming week.

End the report with a footer line:
---
*Weekly summary for {PERIOD}. Generated: {DATE}. Source: project management agent.*
"""


# ---------------------------------------------------------------------------
# Context gathering
# ---------------------------------------------------------------------------


def _build_weekly_context(svc: ProjectService) -> str:
    """Gather project data + past-week journals into a context string."""
    week_end = REFERENCE_DATE
    week_start = week_end - dt.timedelta(days=6)

    project = svc.read_project()
    tasks = svc.read_tasks()
    raid = svc.read_raid()
    actions = svc.read_actions()
    journals = svc.read_journals_range(week_start, week_end)

    complete = [t for t in tasks if t.status == "complete"]
    overdue = [
        t
        for t in tasks
        if t.status not in ("complete",) and t.due_date < REFERENCE_DATE
    ]
    blocked = [t for t in tasks if t.status == "blocked"]
    in_progress = [t for t in tasks if t.status == "in_progress"]

    open_issues = [r for r in raid if r.type == "issue" and r.status == "open"]
    decisions = [r for r in raid if r.type == "decision"]

    lines = [
        f"REPORTING PERIOD: {week_start} to {week_end}",
        f"TODAY (reference date): {REFERENCE_DATE}",
        "",
        "=== PROJECT ===",
        f"Name:           {project.name}",
        f"RAG status:     {project.rag_status.upper()}",
        f"RAG reason:     {project.rag_reason}",
        f"Planned end:    {project.planned_end}",
        f"Forecast end:   {project.forecast_end}",
        "",
        "=== TASKS ===",
        *[
            f"  [{t.status.upper()}] Task {t.task_id}: {t.description} "
            f"(owner: {t.owner_name}, due: {t.due_date}, "
            f"priority: {t.priority.upper()}"
            + (f", BLOCKED: {t.blocked_reason}" if t.blocked_reason else "")
            + ")"
            for t in tasks
        ],
        "",
        f"Summary — Complete: {len(complete)} | In progress: {len(in_progress)} | "
        f"Blocked: {len(blocked)} | Overdue: {len(overdue)}",
        "",
        "=== OPEN ISSUES ===",
        *(
            [
                f"  I{r.raid_id}: [severity: {(r.severity or '?').upper()}] "
                f"{r.title} — owner: {r.owner}"
                for r in open_issues
            ]
            or ["  None"]
        ),
        "",
        "=== DECISIONS ===",
        *(
            [
                f"  D{r.raid_id}: {r.title} — decided by: "
                f"{r.decided_by or '?'} on {r.decision_date or '?'}"
                for r in decisions
            ]
            or ["  None"]
        ),
        "",
        "=== OPEN ACTIONS ===",
        *(
            [
                f"  [{a.status.upper()}] Action {a.action_id}: "
                f"{a.description} — owner: {a.owner_name}, due: {a.due_date}"
                for a in actions
                if a.status == "open"
            ]
            or ["  None"]
        ),
        "",
        "=== JOURNAL ENTRIES (past 7 days) ===",
    ]

    if journals:
        for date in sorted(journals):
            lines.append(f"\n--- {date} ---")
            lines.append(journals[date])
    else:
        lines.append("No journal entries for this period.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_weekly_report(context_str: str) -> str:
    """Call the LLM to generate the weekly summary from context."""
    week_end = REFERENCE_DATE
    week_start = week_end - dt.timedelta(days=6)
    period = f"{week_start} to {week_end}"

    prompt = WEEKLY_SYSTEM_PROMPT.replace("{PERIOD}", period).replace(
        "{DATE}", str(REFERENCE_DATE)
    )

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    response = llm.invoke(
        [
            SystemMessage(prompt),
            HumanMessage(
                f"Please generate the weekly summary report from the following data:\n\n"
                f"{context_str}"
            ),
        ]
    )
    return response.content


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _iso_week_label(date: dt.date) -> str:
    """Return ISO week label like '2026-W12'."""
    iso = date.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def save_weekly_report(content: str, output_path: Optional[Path] = None) -> Path:
    """Save the weekly report markdown to disk and return the path."""
    if output_path is None:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        week_label = _iso_week_label(REFERENCE_DATE)
        output_path = REPORTS_DIR / f"{week_label}.md"

    week_end = REFERENCE_DATE
    week_start = week_end - dt.timedelta(days=6)
    header = (
        f"# Weekly Summary Report\n"
        f"**Period:** {week_start} to {week_end}  \n"
        f"**Generated:** {REFERENCE_DATE}  \n\n"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + content)

    return output_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run(output_path: Optional[Path] = None) -> Path:
    """Generate and save the weekly summary report. Returns the path."""
    print("Gathering project data for weekly summary...")
    svc = ProjectService()
    try:
        context_str = _build_weekly_context(svc)
    finally:
        svc.close()

    print("Generating weekly summary report...")
    report_content = generate_weekly_report(context_str)

    path = save_weekly_report(report_content, output_path)
    print(f"\nWeekly report saved to: {path}\n")
    print("=" * 72)
    print(report_content)
    print("=" * 72)

    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a weekly summary report.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Override output file path (default: data/reports/YYYY-Www.md)",
    )
    args = parser.parse_args()
    run(output_path=args.output)
