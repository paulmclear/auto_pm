# Epic 8: Multi-Project Support

## Overview

Transform the application from single-project to multi-project. Every data entity gains a `project_id`. The web app provides a project switcher and cross-project views. The PM agent runs scoped to one project at a time. A future "Programme Manager" agent (out of scope for this epic) will supervise across projects.

## Current State

- **Single-project architecture throughout**:
  - `ProjectRow` is a singleton — `SqliteProjectRepository.read()` has no WHERE clause
  - `tasks`, `raid_items`, `actions` tables have no `project_id` column
  - `messages` have no `project_id`
  - `journal/` and `reports/` directories are flat (no project scoping)
  - All web routes assume a single project
  - All agent tools assume a single project
  - `ProjectService` instantiates one set of repositories with no project filter

## Design

### Data Model Changes

Every entity needs a `project_id` foreign key:

```
projects        — id (already exists, becomes meaningful)
phases          — project_id (already exists as FK)
milestones      — project_id (already exists as FK)
tasks           — ADD project_id FK
raid_items      — ADD project_id FK
actions         — ADD project_id FK
messages        — ADD project_id FK
agent_runs      — ADD project_id FK (from Epic 11)
conversations   — ADD project_id FK (from Epic 10)
chat_messages   — scoped via conversation → project
journal/        — MOVE to journal/{project_id}/YYYY-MM-DD.md
reports/        — MOVE to reports/{project_id}/YYYY-MM-DD.md
date.json       — EITHER per-project OR global (see below)
config.json     — EITHER per-project overrides OR global (see below)
```

### Simulated Date Strategy

**Option A — Global date (recommended for now)**
All projects share the same simulated date. Simpler. The PM agent advances the date after processing all projects (or after each project — TBD).

**Option B — Per-project date**
Each project has its own simulated timeline. More flexible but complex.

**Recommendation**: Global date. Per-project date can be a future enhancement.

### Service Layer Changes

`ProjectService` gains a `project_id` parameter:

```python
class ProjectService:
    def __init__(self, project_id: str):
        self.project_id = project_id
        # All repositories filter by project_id
```

All repository methods that query/insert data must include `project_id` in their WHERE clauses and INSERT values.

### Web App Changes

1. **Project switcher** — Dropdown or sidebar list of all projects, stored in session/cookie
2. **Cross-project dashboard** — New `/` landing page showing all projects with RAG status, key metrics
3. **Project-scoped views** — All existing views (`/tasks`, `/raid`, `/journal`, `/reports`) become `/projects/{project_id}/tasks`, etc.
4. **URL scheme**: `/projects/{project_id}/...` for project-scoped pages; `/` for portfolio view

### Agent Changes

1. **PM agent** accepts `project_id` argument: `run_agent(project_id="proj-001")`
2. All tools receive `project_id` via closure or config (not as an LLM parameter — the agent manages one project)
3. The agent prompt includes the project name and context
4. CLI: `python -m project_manager_agent.agents.project_manager.agent --project proj-001`
5. Web trigger (Epic 11): project selector before "Run Agent"

### Migration Strategy

1. Add `project_id` columns with a default value (e.g., `"proj-001"`) so existing data is preserved
2. Backfill existing single-project data with the default project_id
3. Move journal/report files into project-scoped subdirectories
4. Update all queries to filter by project_id
5. This is a **big-bang migration** — all layers change together

## User Stories

### 8.1 — Database schema migration
Add `project_id` FK to `tasks`, `raid_items`, `actions`, `messages` tables. Alembic or manual migration script. Backfill existing data with default project ID.

### 8.2 — Repository and service layer scoping
Update all repository classes to accept and filter by `project_id`. Update `ProjectService` constructor to take `project_id`. Update `FileJournalRepository` to use `journal/{project_id}/` paths.

### 8.3 — Agent multi-project scoping
PM agent accepts `--project` CLI argument. All tools operate within the scoped `project_id`. Agent prompt includes project name. Runner function takes `project_id` parameter.

### 8.4 — Web app project switcher and routing
Add project switcher UI. Restructure routes to `/projects/{project_id}/...`. Session/cookie stores selected project. Navigation updates to include project context.

### 8.5 — Portfolio dashboard
New landing page at `/` showing all projects in a card grid: project name, RAG status, % tasks complete, next milestone, forecast end date. Click through to project-scoped views.

### 8.6 — Project CRUD
Web UI and API endpoints to create, edit, and archive projects. `POST /api/projects`, `PUT /api/projects/{id}`, `DELETE /api/projects/{id}` (soft delete/archive).

### 8.7 — Demo data seeding for multiple projects
Update `create_demo_data.py` and `seed.py` to create 2-3 demo projects with distinct data sets.

## Dependencies

- **Prioritised first** — building new features on a single-project architecture and retrofitting multi-project is more costly than doing it upfront
- Epics 9-14 should be designed with multi-project in mind (avoid hardcoding single-project assumptions)

## Risks

- **Migration complexity**: Touching every layer simultaneously is risky. Mitigate with thorough tests and a rollback-capable migration script.
- **Performance**: Cross-project queries (portfolio dashboard, programme manager) need efficient indexing on `project_id`.
- **Journal/report file moves**: File-based storage gets messy with project scoping. Consider moving journals into the DB (future).
- **Scope creep**: The "Programme Manager" agent is explicitly out of scope. Resist the temptation to build it here — just ensure the data model supports it.

## Future: Programme Manager Agent (Out of Scope)

After Epic 8 ships, a Programme Manager agent can be built that:
- Reads reports from all PM agents
- Identifies cross-project dependencies and risks
- Produces a portfolio-level status report
- Escalates cross-cutting issues

This requires the multi-project data model from this epic but is a separate piece of work.
