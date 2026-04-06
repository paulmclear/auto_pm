"""Migration 002: Add is_archived column to projects table.

Adds a boolean is_archived column (default False) for soft-delete support.

Usage:
    uv run python -m project_manager_agent.core.db.migrations.002_add_is_archived
"""

from sqlalchemy import inspect, text

from project_manager_agent.core.db.engine import _engine


def migrate() -> None:
    inspector = inspect(_engine)
    columns = {c["name"] for c in inspector.get_columns("projects")}

    if "is_archived" in columns:
        print("  projects.is_archived already exists — skipping")
        return

    with _engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE projects ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT 0"
            )
        )
    print("  projects.is_archived column added")
    print("Migration 002 complete.")


if __name__ == "__main__":
    migrate()
