"""
Demo Data Setup
===============
Populates the SQL database with realistic mid-project scenarios for testing
and demos.  Also seeds journal files and sets the reference date.

Projects seeded:
  1. Customer Portal Modernisation (AMBER) — blocked DB migration
  2. Data Platform Migration (GREEN) — on track, steady progress
  3. Mobile Banking App Refresh (RED) — critical vendor SDK bug

Run from the project root:
    python create_demo_data.py
"""

import json
from pathlib import Path

from project_manager_agent.core.db.engine import create_tables, get_session
from project_manager_agent.core.db.seed import seed_all_demo_data

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
        project_ids = seed_all_demo_data(session)

    # Set reference date
    with open(DATA / "date.json", "w", encoding="utf-8") as f:
        json.dump(DATE, f)

    print(f"Demo data created ({len(project_ids)} projects):")
    print()
    print("  1. Customer Portal Modernisation")
    print("     RAG: AMBER | Tasks: 11 | RAID: 7 | Actions: 3 | Inbox: 2")
    print()
    print("  2. Data Platform Migration")
    print("     RAG: GREEN | Tasks: 9 | RAID: 4 | Actions: 2 | Inbox: 2")
    print()
    print("  3. Mobile Banking App Refresh")
    print("     RAG: RED   | Tasks: 9 | RAID: 5 | Actions: 3 | Inbox: 2")
    print()
    print(f"  Date:     {DATE['reference_date']}")
    print("  Database: data/project_manager.db")


if __name__ == "__main__":
    create()
