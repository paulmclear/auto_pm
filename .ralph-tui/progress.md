# Ralph Progress Log

This file tracks progress across iterations. Agents update this file
after each iteration and it's included in prompts for context.

## Codebase Patterns (Study These First)

*Add reusable patterns discovered during development here.*

- **src/ layout**: Package lives at `src/project_manager_agent/` with `core/` (models, date_utils, repositories), `agents/project_manager/`, and `agents/reporter/` as peer packages. All imports use absolute paths (e.g. `from project_manager_agent.core.models import Task`). Requires `uv pip install -e .` after initial setup.
- **editable install**: `uv sync` alone doesn't install the package — need `uv pip install -e .` for imports to resolve.

---

## 2026-03-19 - pm-609.8
- Updated pyproject.toml: added `sqlalchemy>=2.0` to dependencies, `pytest>=8.0` to dev dependencies, and `[tool.setuptools.packages.find] where = ["src"]` for src/ layout
- Files changed: `pyproject.toml`, `uv.lock`
- **Learnings:**
  - uv lock/sync handled the new dependencies cleanly — SQLAlchemy 2.0.48 and pytest 9.0.2 resolved
  - The src/ layout config is ready but the actual `src/` directory doesn't exist yet (pm-609.1 will create it)
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
