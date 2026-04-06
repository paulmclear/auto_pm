"""
Reset Script
============
Clears all runtime data to allow a clean test run:
  - Drops and recreates all SQL tables in the SQLite database
  - Deletes all journal files in data/journal/ (including project subdirectories)
  - Optionally deletes all reports in data/reports/ (--reports flag)
  - Resets REFERENCE_DATE in .env to START_DATE
"""

import re
import shutil
import argparse
from pathlib import Path

DATA = Path("data")

JOURNAL_DIR = DATA / "journal"
REPORTS_DIR = DATA / "reports"
ENV_FILE = Path(".env")

START_DATE = "2026-03-19"


def _set_env_reference_date(date: str) -> None:
    """Update REFERENCE_DATE in .env."""
    env_text = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
    new_line = f"REFERENCE_DATE={date}"
    if re.search(r"^REFERENCE_DATE=", env_text, re.MULTILINE):
        env_text = re.sub(
            r"^REFERENCE_DATE=.*$", new_line, env_text, flags=re.MULTILINE
        )
    else:
        env_text = env_text.rstrip("\n") + f"\n{new_line}\n"
    ENV_FILE.write_text(env_text, encoding="utf-8")


def reset(start_date: str = START_DATE, clear_reports: bool = False) -> None:
    cleared = []

    # Drop and recreate all SQL tables
    from project_manager_agent.core.db.engine import _engine, create_tables
    from project_manager_agent.core.db.orm import Base

    Base.metadata.drop_all(_engine)
    create_tables()
    cleared.append("SQL tables dropped and recreated")

    # Delete journal markdown files (top-level and project subdirectories)
    if JOURNAL_DIR.exists():
        for item in JOURNAL_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
                cleared.append(f"{item}/ (directory)")
            elif item.suffix == ".md":
                item.unlink()
                cleared.append(str(item))

    # Optionally delete reports (top-level and project subdirectories)
    if clear_reports and REPORTS_DIR.exists():
        for item in REPORTS_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
                cleared.append(f"{item}/ (directory)")
            elif item.suffix == ".md":
                item.unlink()
                cleared.append(str(item))

    # Reset reference date in .env
    _set_env_reference_date(start_date)
    cleared.append(f"REFERENCE_DATE → {start_date}")

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
