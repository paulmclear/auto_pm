"""
Demo Data Setup
===============
Populates the SQL database with a realistic mid-project scenario for testing
and demos.  Also seeds journal files and sets the reference date.

Scenario: "Customer Portal Modernisation"
  - Phase 1 (Discovery) is complete with milestone achieved.
  - Phase 2 (Design & Build) is in progress — one task blocked, milestone slipping.
  - Phase 3 (Testing & Launch) is not yet started.
  - RAG is AMBER due to milestone slip caused by a blocked database task.
  - RAID log contains risks, an open issue, two assumptions (one validated,
    one overdue for validation), and two decisions.
  - One action is overdue, two are open.
  - Inbox contains two messages awaiting processing.
  - Date is set to 2026-03-20 (mid-project).

Run from the project root:
    python create_demo_data.py
"""

import json
from pathlib import Path

from project_manager_agent.core.db.engine import create_tables, get_session
from project_manager_agent.core.db.seed import seed_demo_data

DATA = Path("data")
DATE = {"reference_date": "2026-03-20"}


def create() -> None:
    # Ensure data directories exist
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "journal").mkdir(parents=True, exist_ok=True)
    (DATA / "reports").mkdir(parents=True, exist_ok=True)

    # Create SQL tables and seed demo data
    create_tables()
    with get_session() as session:
        seed_demo_data(session)

    # Set reference date
    with open(DATA / "date.json", "w", encoding="utf-8") as f:
        json.dump(DATE, f)

    print("Demo data created:")
    print("  Project:  Customer Portal Modernisation")
    print(f"  Date:     {DATE['reference_date']}")
    print("  RAG:      AMBER")
    print("  Tasks:    11 (4 complete, 2 in progress, 1 blocked)")
    print("  RAID:     7 items (2 risks, 2 assumptions, 1 issues, 2 decisions)")
    print("  Actions:  3 open (1 overdue)")
    print("  Inbox:    2 unprocessed messages")
    print("  Database: data/project_manager.db")


if __name__ == "__main__":
    create()
