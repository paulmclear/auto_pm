"""
Project Status Reporter
=======================
Generates a structured management/programme status report from current project
data. Reads the project plan, tasks, RAID log, actions, and the latest journal
entry, then uses an LLM to produce a well-formatted report suitable for
management and programme reporting.

Output: data/reports/YYYY-MM-DD-status-report.md  (also printed to stdout)

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
    python -m project_manager_agent.reporter.agent
    python -m project_manager_agent.reporter.agent --output path/to/report.md
"""

import argparse
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..date_utils import REFERENCE_DATE
from .context import load_all, format_context
from .prompt import REPORT_SYSTEM_PROMPT

load_dotenv(override=True)

REPORTS_DIR = Path("data/reports")


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(context_str: str) -> str:
    """Call the LLM to generate the full report from the formatted context."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
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


def save_report(content: str, output_path: Optional[Path] = None) -> Path:
    """Save the report markdown to disk and return the path."""
    if output_path is None:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = REPORTS_DIR / f"{REFERENCE_DATE}-status-report.md"

    header = f"# Project Status Report\n**Date:** {REFERENCE_DATE}  \n\n"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + content)

    return output_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run(output_path: Optional[Path] = None) -> Path:
    """Generate and save the project status report. Returns the path."""
    print("Gathering project data...")
    ctx = load_all()

    print("Generating report...")
    context_str = format_context(ctx)
    report_content = generate_report(context_str)

    path = save_report(report_content, output_path)
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
    args = parser.parse_args()
    run(output_path=args.output)
