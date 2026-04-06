"""
Project Status Reporter
=======================
Generates a structured management/programme status report from current project
data. Reads the project plan, tasks, RAID log, actions, and the latest journal
entry, then uses an LLM to produce a well-formatted report suitable for
management and programme reporting.

Output:
  data/reports/YYYY-MM-DD-status-report.md   (markdown for humans)
  data/reports/YYYY-MM-DD-status-report.json  (structured JSON for dashboards/APIs)

Report sections:
  1. Executive Summary          — 2-3 sentence narrative for senior audiences
  2. RAG Status                 — current rating with reason
  3. Progress Made              — completed tasks and achieved milestones
  4. Schedule & Milestones      — milestone table with planned vs forecast
  5. Next Steps                 — upcoming tasks and near-term milestones
  6. Items for Management Attention — decisions needed, blockers, sponsor asks
  7. Risks & Issues to Escalate — high-impact risks and unresolved issues
  8. Open Actions               — overdue and due-soon action items

Run from the project root:
    python -m project_manager_agent.agents.reporter.agent
    python -m project_manager_agent.agents.reporter.agent --output path/to/report.md
    python -m project_manager_agent.agents.reporter.agent --project 1
"""

import argparse
from pathlib import Path
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from project_manager_agent.core.config import settings
from project_manager_agent.core.date_utils import REFERENCE_DATE
from .context import load_all, format_context
from .prompt import REPORT_SYSTEM_PROMPT
from .schema import (
    StructuredReport,
    MilestoneStatus,
    TaskStatistics,
    TaskStatsByStatus,
    TaskStatsByPhase,
    OverdueTask,
    RaidHighlight,
    Recommendation,
)

REPORTS_DIR = Path(settings.reports_dir)


# ---------------------------------------------------------------------------
# Structured report builder
# ---------------------------------------------------------------------------


def build_structured_report(ctx: dict, report_markdown: str) -> StructuredReport:
    """Build a StructuredReport from the raw context dict.

    The executive_summary and recommendations are extracted from the LLM
    markdown output, while quantitative fields are computed directly from data
    to guarantee accuracy.
    """
    project = ctx["project"]

    # -- Milestone statuses (from project data, always accurate) --
    milestone_statuses = [
        MilestoneStatus(
            milestone_id=m.milestone_id,
            name=m.name,
            planned_date=m.planned_date,
            forecast_date=m.forecast_date,
            actual_date=m.actual_date,
            status=m.status,
        )
        for m in project.milestones
    ]

    # -- Task statistics --
    tasks = ctx["tasks"]
    by_status = TaskStatsByStatus(
        complete=len(ctx["complete"]),
        in_progress=len(ctx["in_progress"]),
        not_started=len(ctx["not_started"]),
        blocked=len(ctx["blocked"]),
    )

    # Group by phase
    phase_map: dict[int, dict] = {}
    for ph in project.phases:
        phase_map[ph.phase_id] = {
            "phase_name": ph.name,
            "total": 0,
            "complete": 0,
            "in_progress": 0,
            "not_started": 0,
            "blocked": 0,
        }
    for t in tasks:
        if t.phase_id and t.phase_id in phase_map:
            pm = phase_map[t.phase_id]
            pm["total"] += 1
            pm[t.status] += 1

    by_phase = [
        TaskStatsByPhase(phase_id=pid, **data) for pid, data in phase_map.items()
    ]

    task_statistics = TaskStatistics(
        total=len(tasks),
        by_status=by_status,
        by_phase=by_phase,
    )

    # -- Overdue tasks --
    overdue_tasks = [
        OverdueTask(
            task_id=t.task_id,
            description=t.description,
            owner=t.owner_name,
            due_date=t.due_date,
            days_overdue=(REFERENCE_DATE - t.due_date).days,
        )
        for t in ctx["overdue_tasks"]
    ]

    # -- RAID highlights (high-impact risks + high-severity issues) --
    raid_highlights: list[RaidHighlight] = []
    for r in ctx["open_risks"]:
        if r.impact in ("high",) or r.probability in ("high",):
            raid_highlights.append(
                RaidHighlight(
                    raid_id=r.raid_id,
                    type="risk",
                    title=r.title,
                    owner=r.owner,
                    severity_or_impact=r.impact,
                    status=r.status,
                )
            )
    for r in ctx["open_issues"]:
        if r.severity in ("high",):
            raid_highlights.append(
                RaidHighlight(
                    raid_id=r.raid_id,
                    type="issue",
                    title=r.title,
                    owner=r.owner,
                    severity_or_impact=r.severity,
                    status=r.status,
                )
            )

    # -- Extract executive summary from markdown (first paragraph after heading) --
    executive_summary = ""
    lines = report_markdown.split("\n")
    capture = False
    summary_lines: list[str] = []
    for line in lines:
        if line.strip().lower().startswith("## executive summary"):
            capture = True
            continue
        if capture:
            if line.strip().startswith("##"):
                break
            if line.strip():
                summary_lines.append(line.strip())
    executive_summary = " ".join(summary_lines)

    # -- Recommendations from "Items for Management Attention" section --
    recommendations: list[Recommendation] = []
    capture = False
    for line in lines:
        if "items for management attention" in line.lower():
            capture = True
            continue
        if capture:
            if line.strip().startswith("##"):
                break
            stripped = line.strip().lstrip("- •*")
            if stripped and "no items require" not in stripped.lower():
                recommendations.append(
                    Recommendation(summary=stripped.strip(), priority="high")
                )

    return StructuredReport(
        report_date=REFERENCE_DATE,
        project_name=project.name,
        executive_summary=executive_summary,
        rag_status=project.rag_status,
        rag_reason=project.rag_reason,
        milestone_statuses=milestone_statuses,
        task_statistics=task_statistics,
        overdue_tasks=overdue_tasks,
        raid_highlights=raid_highlights,
        recommendations=recommendations,
    )


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(context_str: str) -> str:
    """Call the LLM to generate the full report from the formatted context."""
    llm = ChatOpenAI(model=settings.llm_model, temperature=settings.llm_temperature)
    response = llm.invoke(
        [
            SystemMessage(REPORT_SYSTEM_PROMPT.replace("{DATE}", str(REFERENCE_DATE))),
            HumanMessage(
                f"Please generate the project status report from the following data:\n\n"
                f"{context_str}"
            ),
        ]
    )
    return response.content


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def save_report(
    content: str,
    output_path: Optional[Path] = None,
    project_id: Optional[int] = None,
    structured: Optional[StructuredReport] = None,
) -> Path:
    """Save the report markdown (and optional JSON) to disk. Returns the md path."""
    if output_path is None:
        if project_id is not None:
            reports_dir = REPORTS_DIR / str(project_id)
        else:
            reports_dir = REPORTS_DIR
        reports_dir.mkdir(parents=True, exist_ok=True)
        output_path = reports_dir / f"{REFERENCE_DATE}-status-report.md"

    header = f"# Project Status Report\n**Date:** {REFERENCE_DATE}  \n\n"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + content)

    # Save structured JSON alongside the markdown
    if structured is not None:
        json_path = output_path.with_suffix(".json")
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(structured.model_dump_json(indent=2))
        print(f"Structured report saved to: {json_path}")

    return output_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run(
    output_path: Optional[Path] = None,
    project_id: Optional[int] = None,
) -> Path:
    """Generate and save the project status report. Returns the path."""
    print("Gathering project data...")
    ctx = load_all(project_id=project_id)

    print("Generating report...")
    context_str = format_context(ctx)
    report_content = generate_report(context_str)

    print("Building structured report...")
    structured = build_structured_report(ctx, report_content)

    path = save_report(
        report_content, output_path, project_id=project_id, structured=structured
    )
    print(f"\nReport saved to: {path}\n")
    print("=" * 72)
    print(report_content)
    print("=" * 72)

    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a project status report.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Override output file path (default: data/reports/YYYY-MM-DD-status-report.md)",
    )
    parser.add_argument(
        "--project",
        type=int,
        default=None,
        help="Project ID to scope the report to. If omitted, runs unscoped.",
    )
    args = parser.parse_args()
    run(output_path=args.output, project_id=args.project)
