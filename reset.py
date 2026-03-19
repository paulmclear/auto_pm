"""
Reset Script
============
Clears all runtime data to allow a clean test run:
  - Drops and recreates all SQL tables in the SQLite database
  - Deletes all journal files in data/journal/
  - Optionally deletes all reports in data/reports/ (--reports flag)
  - Resets data/date.json to START_DATE
"""

import json
import argparse
from pathlib import Path

DATA = Path("data")

JOURNAL_DIR = DATA / "journal"
REPORTS_DIR = DATA / "reports"
DATE_FILE = DATA / "date.json"

START_DATE = "2026-03-19"


def reset(start_date: str = START_DATE, clear_reports: bool = False) -> None:
    cleared = []

    # Drop and recreate all SQL tables
    from project_manager_agent.core.db.engine import _engine, create_tables
    from project_manager_agent.core.db.orm import Base

    Base.metadata.drop_all(_engine)
    create_tables()
    cleared.append("SQL tables dropped and recreated")

    # Delete journal markdown files
    for journal in JOURNAL_DIR.glob("*.md"):
        journal.unlink()
        cleared.append(str(journal))

    # Optionally delete reports
    if clear_reports:
        for report in REPORTS_DIR.glob("*.md"):
            report.unlink()
            cleared.append(str(report))

    # Reset reference date
    with open(DATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"reference_date": start_date}, f)
    cleared.append(f"{DATE_FILE} → {start_date}")

    print("Cleared:")
    for item in cleared:
        print(f"  {item}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset project manager runtime data.")
    parser.add_argument(
        "--date",
        default=START_DATE,
        help=f"Start date to reset to (YYYY-MM-DD). Defaults to {START_DATE}.",
    )
    parser.add_argument(
        "--reports",
        action="store_true",
        help="Also delete all generated reports in data/reports/.",
    )
    args = parser.parse_args()
    reset(args.date, clear_reports=args.reports)
