# Ralph Progress Log

This file tracks progress across iterations. Agents update this file
after each iteration and it's included in prompts for context.

## Codebase Patterns (Study These First)

*Add reusable patterns discovered during development here.*

- **src/ layout**: Package lives at `src/project_manager_agent/` with `core/` (models, date_utils, repositories), `agents/project_manager/`, and `agents/reporter/` as peer packages. All imports use absolute paths (e.g. `from project_manager_agent.core.models import Task`). Requires `uv pip install -e .` after initial setup.
- **ORM models**: `core/db/orm.py` uses SQLAlchemy 2.0 `Mapped`/`mapped_column` style. List fields (depends_on, linked_task_ids, objectives) stored as JSON-encoded `Text` columns with default `"[]"`. Shared `Base` class for all models. Row classes suffixed with `Row` to avoid clashing with dataclass names in `core/models.py`.
- **editable install**: `uv sync` alone doesn't install the package — need `uv pip install -e .` for imports to resolve.

---

## 2026-03-19 - pm-609.8
- Updated pyproject.toml: added `sqlalchemy>=2.0` to dependencies, `pytest>=8.0` to dev dependencies, and `[tool.setuptools.packages.find] where = ["src"]` for src/ layout
- Files changed: `pyproject.toml`, `uv.lock`
- **Learnings:**
  - uv lock/sync handled the new dependencies cleanly — SQLAlchemy 2.0.48 and pytest 9.0.2 resolved
  - The src/ layout config is ready but the actual `src/` directory doesn't exist yet (pm-609.1 will create it)
---

## 2026-03-19 - pm-609.2
- Tightened `Project` type hints: `objectives` → `list[str]`, `phases` → `list[Phase]`, `milestones` → `list[Milestone]`
- Added `MessageDirection` Literal type alias and `Message` dataclass with fields: message_id, direction, timestamp, owner_name, owner_email, message, sender_name, sender_email
- Kept `JsonSerialiser` unchanged
- Files changed: `src/project_manager_agent/core/models.py`
- **Learnings:**
  - Model file was already at the correct `core/models.py` location from pm-609.1, so no move was needed
  - `objectives` was previously untyped `list` — now `list[str]` which matches how it's used in `project.json`
---

## 2026-03-19 - pm-609.1
- Restructured project from flat `project_manager_agent/` to `src/project_manager_agent/` with `core/`, `agents/project_manager/`, `agents/reporter/` sub-packages
- All relative imports (`from ..models`, `from .date_utils`) converted to absolute imports (`from project_manager_agent.core.models`, etc.)
- Updated CLAUDE.md: run commands now use `project_manager_agent.agents.project_manager.agent` and `project_manager_agent.agents.reporter.agent`
- Removed old `project_manager_agent/` directory (including pycache)
- Files changed: all `.py` files moved to new locations under `src/`, `CLAUDE.md` updated
- **Learnings:**
  - `uv sync` alone doesn't make the src/ layout package importable — need `uv pip install -e .` for editable install
  - `[tool.setuptools.packages.find] where = ["src"]` in pyproject.toml is necessary for setuptools to find packages under src/
  - ruff format auto-splits long import lines into multi-line format
---

## 2026-03-19 - pm-609.5
- Created `core/db/engine.py` with SQLAlchemy engine, `SessionFactory`, `get_session()` context manager, and `create_tables()` function
- `DATABASE_URL` defaults to `sqlite:///data/project_manager.db` (path resolved relative to the engine.py file location)
- `get_session()` yields a transactional session: auto-commits on success, rolls back on error
- `create_tables()` calls `Base.metadata.create_all()` — idempotent (safe to call repeatedly)
- Files changed: `src/project_manager_agent/core/db/engine.py` (new)
- **Learnings:**
  - `Path(__file__).resolve().parents[4]` navigates from `core/db/engine.py` up to project root reliably
  - `create_all()` is inherently idempotent — uses `checkfirst=True` by default
---

## 2026-03-19 - pm-609.3
- Created `core/protocols.py` with 6 `typing.Protocol` classes: `TaskRepository`, `ProjectRepository`, `RaidRepository`, `ActionRepository`, `MessageRepository`, `JournalRepository`
- All methods return typed domain objects (not raw dicts) — key difference from existing JSON repos which return `dict` for project/RAID/actions
- Protocol signatures use proper types: `dt.date` instead of `str` for dates, `RagStatus`/`MilestoneStatus` literals instead of `str`, `RaidItem`/`Action` objects instead of `dict` for add methods
- Files changed: `src/project_manager_agent/core/protocols.py` (new)
- **Learnings:**
  - `from __future__ import annotations` needed for forward-ref-friendly Protocol definitions
  - Existing JSON repos don't yet conform to these protocols (e.g. `ProjectRepo.read()` returns `dict`, not `Project`) — SQL implementations will be the first to satisfy them
---

## 2026-03-19 - pm-609.4
- Created `core/db/__init__.py` and `core/db/orm.py` with SQLAlchemy 2.0 declarative ORM models
- 7 tables: `projects`, `phases` (FK→projects), `milestones` (FK→projects), `tasks`, `raid_items`, `actions`, `messages`
- List fields (`objectives`, `depends_on`, `linked_task_ids`) stored as JSON-encoded `Text` columns
- Row classes suffixed with `Row` (e.g. `TaskRow`) to avoid name collisions with dataclasses in `core/models.py`
- Files changed: `src/project_manager_agent/core/db/__init__.py`, `src/project_manager_agent/core/db/orm.py`
- **Learnings:**
  - SQLAlchemy 2.0 `Mapped[str | None]` syntax works cleanly for nullable columns
  - Using `Text` for JSON list fields is simpler than `JSON` type since SQLite (likely target) has limited JSON support
  - Naming convention `*Row` keeps ORM models distinct from domain dataclasses
---
