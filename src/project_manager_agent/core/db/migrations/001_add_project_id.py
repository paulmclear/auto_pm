"""Migration 001: Add project_id FK to tasks, raid_items, actions, messages.

Adds a nullable project_id column to each table, backfills existing rows
with the ID of the first project found, and creates indexes.

SQLite does not support ALTER TABLE ADD CONSTRAINT for foreign keys, so
the FK is enforced at the ORM level only.  The column + index are added
via raw DDL.

Usage:
    uv run python -m project_manager_agent.core.db.migrations.001_add_project_id
"""

from sqlalchemy import inspect, text

from project_manager_agent.core.db.engine import _engine

TABLES = ["tasks", "raid_items", "actions", "messages"]


def _has_column(inspector, table: str, column: str) -> bool:
    columns = {c["name"] for c in inspector.get_columns(table)}
    return column in columns


def migrate() -> None:
    inspector = inspect(_engine)

    with _engine.begin() as conn:
        # Determine the default project ID for backfill
        row = conn.execute(
            text("SELECT id FROM projects ORDER BY id LIMIT 1")
        ).fetchone()
        default_pid = row[0] if row else None

        for table in TABLES:
            if _has_column(inspector, table, "project_id"):
                print(f"  {table}.project_id already exists — skipping column add")
            else:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN project_id INTEGER"))
                print(f"  {table}.project_id column added")

            # Backfill NULLs with the default project ID
            if default_pid is not None:
                result = conn.execute(
                    text(
                        f"UPDATE {table} SET project_id = :pid WHERE project_id IS NULL"
                    ),
                    {"pid": default_pid},
                )
                if result.rowcount:
                    print(
                        f"  {table}: backfilled {result.rowcount} rows with project_id={default_pid}"
                    )

            # Create index (IF NOT EXISTS)
            idx_name = f"ix_{table}_project_id"
            conn.execute(
                text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} (project_id)")
            )
            print(f"  {idx_name} index ensured")

    print("Migration 001 complete.")


if __name__ == "__main__":
    migrate()
