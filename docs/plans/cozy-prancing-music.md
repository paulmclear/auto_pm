# Plan: Layered Architecture — SQLite, Web UI, Agent Migration

## Context

The project currently stores all state as flat JSON/JSONL files under `data/`. Repositories are tightly coupled to file I/O, and agent tools instantiate repos directly. This works, but prevents adding a web UI (which would need to read the same data) without creating coupling between agents and web code.

This plan restructures the project into a layered architecture with three epics:
1. **SQLite storage** with repository abstraction
2. **Agent toolset migration** to the new layers
3. **FastAPI + AlpineJS web dashboard** (read-only)

Epic order is 1→2→3 (not 1→web→agents) so the entire system is on SQL before adding the web layer.

The goal: agents and web are independent consumers of a shared `core` package containing domain models, repository protocols, SQLite implementations, and a thin service layer.

---

## Target Package Structure

```
project_manager_agent/
├── __init__.py
├── date_utils.py                          # unchanged — reads data/date.json
│
├── core/                                  # NEW — shared by agents + web
│   ├── __init__.py
│   ├── models.py                          # moved from project_manager_agent/models.py
│   ├── protocols.py                       # repository interfaces (Protocol classes)
│   ├── services.py                        # thin service facade
│   └── db/
│       ├── __init__.py
│       ├── orm.py                         # SQLAlchemy ORM table models
│       ├── engine.py                      # engine + session factory
│       ├── repositories.py               # SQLite repo implementations
│       └── seed.py                        # demo data seeding
│
├── project_manager/                       # existing — rewired imports
│   ├── __init__.py
│   ├── agent.py
│   ├── prompt.py                          # unchanged
│   └── tools.py                           # rewired to use services
│
├── reporter/                              # existing — rewired imports
│   ├── __init__.py
│   ├── agent.py
│   ├── context.py                         # rewired to use services
│   └── prompt.py                          # unchanged
│
└── web/                                   # NEW — FastAPI dashboard
    ├── __init__.py
    ├── app.py                             # FastAPI app factory
    ├── routes/
    │   ├── __init__.py
    │   ├── dashboard.py
    │   ├── tasks.py
    │   ├── raid.py
    │   ├── journal.py
    │   └── reports.py
    ├── templates/                         # Jinja2 + AlpineJS
    │   ├── base.html
    │   ├── dashboard.html
    │   ├── tasks.html
    │   ├── raid.html
    │   ├── journal.html
    │   └── reports.html
    └── static/
        └── style.css
```

Root-level files updated: `create_demo_data.py`, `reset.py`, `pyproject.toml`.

Data directory changes:
- `data/project_manager.db` — new SQLite database
- `data/journal/` — stays as markdown files (unchanged)
- `data/reports/` — stays as markdown files (unchanged)
- `data/date.json` — stays as JSON file (unchanged)
- `data/tasks.json`, `data/project.json`, `data/raid.json`, `data/actions.json`, `data/inbox/`, `data/outbox/` — **removed** after migration

---

## Key Design Decisions

### DDD: Domain models vs ORM models
- **Domain layer**: existing dataclasses in `core/models.py` (Task, Phase, Milestone, Project, RaidItem, Action) are the contract. They remain pure Python with no SQLAlchemy dependency.
- **Persistence layer**: SQLAlchemy ORM models in `core/db/orm.py` map to SQL tables. Repos convert between ORM ↔ domain.
- This separation means domain models can evolve without touching the DB schema and vice versa.

### What moves to SQL, what stays as files
| Data | Storage | Rationale |
|------|---------|-----------|
| Tasks, Project, Phases, Milestones | SQLite | Structured, queried, updated frequently |
| RAID items, Actions | SQLite | Structured, queried, updated frequently |
| Messages (inbox + outbox) | SQLite | Structured records; future backlog item needs per-task query |
| Journal entries | Markdown files | Write-once, human-readable, never queried by field |
| Reports | Markdown files | Write-once output artifacts |
| Reference date | `data/date.json` | Single value, read once at import — no benefit from SQL |

### Repository interfaces: Protocol, not ABC
Use `typing.Protocol` for duck-typing compatibility. No registration, no metaclass overhead.

### Service layer: concrete, not abstract
One `ProjectService` class — not a Protocol. YAGNI: we don't need multiple service implementations. The service owns session lifecycle and delegates to repos.

### No Alembic
Use `Base.metadata.create_all()` for table creation, `drop_all()` for reset. This is a learning project. Add Alembic only if/when schema migrations become painful.

### Journal stays file-based
`FileJournalRepository` wraps the existing file logic behind the `JournalRepository` protocol. It receives `journal_dir: Path` as a constructor arg instead of a class constant.

---

## Epic 1: SQLite Data Layer

### Step 1.1 — Create `core/models.py`
- Move contents of `project_manager_agent/models.py` → `core/models.py`
- Add `Message` dataclass for inbox/outbox records:
  ```python
  @dataclass
  class Message:
      message_id: int
      direction: Literal["inbound", "outbound"]
      timestamp: str
      owner_name: str
      owner_email: str
      message: str
      sender_name: Optional[str] = None
      sender_email: Optional[str] = None
  ```
- Keep `JsonSerialiser` (still used by journal writes)
- Leave a re-export shim in the old `models.py` location temporarily (removed in Epic 3)

### Step 1.2 — Create `core/protocols.py`
Repository interfaces using `typing.Protocol`. All repos return **typed domain objects** (not raw dicts):

```python
class TaskRepository(Protocol):
    def list_all(self) -> list[Task]: ...
    def get(self, task_id: int) -> Task: ...
    def update_status(self, task_id: int, status: TaskStatus) -> None: ...
    def update_blocking(self, task_id: int, blocked_reason: Optional[str],
                        depends_on: Optional[list[int]]) -> None: ...

class ProjectRepository(Protocol):
    def read(self) -> Project: ...  # returns typed Project with list[Phase] + list[Milestone]
    def update_health(self, rag_status: Optional[str], rag_reason: Optional[str],
                      forecast_end: Optional[str]) -> None: ...
    def update_milestone(self, milestone_id: int, status: Optional[str],
                         forecast_date: Optional[str], actual_date: Optional[str]) -> None: ...

class RaidRepository(Protocol):
    def list_all(self) -> list[RaidItem]: ...
    def add(self, item: RaidItem) -> int: ...
    def update(self, raid_id: int, fields: dict) -> None: ...

class ActionRepository(Protocol):
    def list_all(self) -> list[Action]: ...
    def add(self, action: Action) -> int: ...
    def update_status(self, action_id: int, status: ActionStatus) -> None: ...

class MessageRepository(Protocol):
    def send(self, owner_name: str, owner_email: str, message: str) -> None: ...
    def list_inbox(self) -> list[Message]: ...
    def list_outbox(self) -> list[Message]: ...

class JournalRepository(Protocol):
    def read_last(self, before_date: dt.date) -> Optional[str]: ...
    def write(self, date: dt.date, section: str, content: str) -> None: ...
    def list_all(self) -> list[tuple[dt.date, str]]: ...  # for web UI
```

**Typed returns**: All repos return domain dataclasses, not raw dicts. This requires:
- Tightening `Project.phases` to `list[Phase]` and `Project.milestones` to `list[Milestone]` in the domain model
- Tools and reporter consumers adapt to use typed objects (attribute access instead of dict access)
- `RaidRepository.add()` accepts a `RaidItem` (or a builder/factory) instead of a raw dict
- `ActionRepository.add()` accepts an `Action` instead of a raw dict

### Step 1.3 — Create `core/db/orm.py`
SQLAlchemy 2.0 declarative ORM models:

| Table | Key columns | Notes |
|-------|------------|-------|
| `tasks` | task_id (PK), description, owner_name, owner_email, due_date, status, phase_id, depends_on (JSON text), blocked_reason, external_dependency | `depends_on` stored as JSON string |
| `projects` | id (PK), name, description, objectives (JSON text), sponsor, project_manager, planned_start, planned_end, actual_start, forecast_end, rag_status, rag_reason | Single row. `objectives` as JSON string |
| `phases` | phase_id (PK), project_id (FK), name, description, planned_start, planned_end | |
| `milestones` | milestone_id (PK), project_id (FK), name, description, planned_date, forecast_date, actual_date (nullable), status, linked_task_ids (JSON text) | |
| `raid_items` | raid_id (PK), type, title, description, owner, raised_date, status, linked_task_ids (JSON), + all type-specific nullable columns | Flat table, same as current JSON structure |
| `actions` | action_id (PK), description, owner_name, owner_email, due_date, status, source_raid_id (nullable), source_task_id (nullable) | |
| `messages` | message_id (PK autoincrement), direction, timestamp, owner_name, owner_email, message, sender_name (nullable), sender_email (nullable) | Replaces both inbox + outbox JSONL |

### Step 1.4 — Create `core/db/engine.py`
- `DATABASE_URL = "sqlite:///data/project_manager.db"`
- `engine`, `SessionLocal` (sessionmaker)
- `get_session()` — context manager yielding a session
- `create_tables()` — `Base.metadata.create_all(engine)`, idempotent

### Step 1.5 — Create `core/db/repositories.py`
SQLite-backed implementations:
- `SqliteTaskRepository(session)` → implements `TaskRepository`
- `SqliteProjectRepository(session)` → implements `ProjectRepository`
- `SqliteRaidRepository(session)` → implements `RaidRepository`
- `SqliteActionRepository(session)` → implements `ActionRepository`
- `SqliteMessageRepository(session)` → implements `MessageRepository`
- `FileJournalRepository(journal_dir: Path)` → implements `JournalRepository` (wraps existing file logic)

Each SQL repo:
1. Accepts `Session` in constructor
2. Queries ORM models
3. Maps ORM → domain (via `_to_domain()` helper) for reads
4. Maps domain/dict → ORM for writes
5. Commits within each write method (matching current immediate-persistence pattern)

### Step 1.6 — Create `core/db/seed.py`
- `seed_demo_data(session: Session)` — inserts the "Customer Portal Modernisation" demo data via ORM objects
- Ports the logic from current `create_demo_data.py`

### Step 1.7 — Update `pyproject.toml`
Add: `sqlalchemy>=2.0`

### Step 1.8 — Tests
- `tests/test_repositories.py` — test each SQL repo against `sqlite:///:memory:`
- Pattern: create tables → seed → assert reads → assert writes → assert error cases
- Test `FileJournalRepository` against a temp directory

---

## Epic 2: Web UI (FastAPI + AlpineJS)

**Depends on**: Epic 1 complete + `core/services.py` (created in this epic)

### Step 2.1 — Create `core/services.py`
Thin facade that both agents and web consume:

```python
class ProjectService:
    def __init__(self, session: Session | None = None):
        self._session = session or next(get_session())
        self._tasks = SqliteTaskRepository(self._session)
        self._project = SqliteProjectRepository(self._session)
        self._raid = SqliteRaidRepository(self._session)
        self._actions = SqliteActionRepository(self._session)
        self._messages = SqliteMessageRepository(self._session)
        self._journal = FileJournalRepository(Path("data/journal"))

    # Task methods
    def list_tasks(self) -> list[Task]: ...
    def update_task_status(self, task_id: int, status: TaskStatus) -> None: ...
    def update_task_blocking(self, ...) -> None: ...

    # Project methods
    def get_project(self) -> dict: ...
    def update_project_health(self, ...) -> None: ...
    def update_milestone(self, ...) -> None: ...

    # RAID methods
    def list_raid_items(self) -> list[dict]: ...
    def add_raid_item(self, item: dict) -> int: ...
    def update_raid_item(self, raid_id: int, fields: dict) -> None: ...

    # Action methods
    def list_actions(self) -> list[dict]: ...
    def add_action(self, action: dict) -> int: ...
    def update_action_status(self, action_id: int, status: ActionStatus) -> None: ...

    # Message methods
    def send_message(self, owner_name, owner_email, message) -> None: ...
    def list_inbox(self) -> list[dict]: ...
    def list_outbox(self) -> list[dict]: ...

    # Journal methods
    def read_last_journal(self) -> Optional[str]: ...
    def write_journal(self, section: str, content: str) -> None: ...
    def list_journals(self) -> list[tuple[dt.date, str]]: ...

    # Reports (file-based, read-only)
    def list_reports(self) -> list[tuple[dt.date, str]]: ...

    def close(self): ...
```

Each method is a 1-3 line delegation to the appropriate repo. Business logic (e.g. filtering overdue tasks) stays in the consumer (reporter's `context.py`, web routes) — the service is just a wiring layer.

### Step 2.2 — Add dependencies
`pyproject.toml`: `fastapi`, `uvicorn[standard]`, `jinja2`, `python-markdown`

### Step 2.3 — Create `web/app.py`
- FastAPI app with Jinja2 templates
- Mount static files
- `get_service()` dependency that yields `ProjectService`
- Include routers from `routes/`

### Step 2.4 — Create route modules
All read-only, server-rendered HTML:

| Route | Path | Data |
|-------|------|------|
| Dashboard | `GET /` | Project summary, RAG, milestone table, task counts |
| Tasks | `GET /tasks` | All tasks with AlpineJS filter/sort |
| RAID | `GET /raid` | RAID log with type-tab filtering |
| Journal | `GET /journal` | Date list; `GET /journal/{date}` renders markdown |
| Reports | `GET /reports` | Date list; `GET /reports/{date}` renders markdown |

### Step 2.5 — Templates
- `base.html`: nav sidebar, AlpineJS from CDN, Pico CSS (classless) from CDN, content block
- Page templates: extend base, use `x-data`, `x-show`, `x-for` for client interactivity
- No build tools, no npm

### Step 2.6 — Tests
- `tests/test_web.py` — FastAPI `TestClient`, seed DB, assert 200 + key content per route

---

## Epic 3: Migrate Agent Toolset

**Depends on**: Epic 2 (specifically `core/services.py`)

### Step 3.1 — Rewire `project_manager/tools.py`
Replace all direct repo instantiation with `ProjectService`:

```python
# Before:
def read_last_journal() -> str:
    content = Journal().read_last()
    ...

# After:
def read_last_journal() -> str:
    svc = ProjectService()
    content = svc.read_last_journal()
    svc.close()
    ...
```

Tool signatures, Pydantic schemas, and tool descriptions remain **identical** — the LLM prompt does not change.

Note: `fetch_tasks_tool` currently has an inline lambda `lambda _: TasksRepo().read()`. This also gets rewired to use the service.

### Step 3.2 — Rewire `reporter/context.py`
Replace `TasksRepo()`, `ProjectRepo()`, etc. with `ProjectService()` calls. The `load_all()` function's return structure stays the same — only the data source changes.

### Step 3.3 — Rewire `project_manager/agent.py`
Replace repo `initialise()` calls in `__main__` with `create_tables()` + journal dir init.

### Step 3.4 — Update `create_demo_data.py`
Call `create_tables()` then `seed_demo_data(session)` from `core.db.seed`.

### Step 3.5 — Update `reset.py`
- `Base.metadata.drop_all(engine)` + `create_tables()` instead of deleting JSON files
- Still delete journal markdown files and optionally reports
- Still reset `data/date.json`

### Step 3.6 — Delete old files
- Remove `project_manager_agent/models.py` (now at `core/models.py`)
- Remove `project_manager_agent/repositories.py` (replaced by `core/db/repositories.py` + `core/services.py`)
- Remove old JSON data files (`tasks.json`, `project.json`, `raid.json`, `actions.json`, `inbox/`, `outbox/`)

### Step 3.7 — Update CLAUDE.md
Document new architecture, package structure, and commands.

---

## Implementation Order

```
Epic 1 (SQLite foundation)
  1.1  core/__init__.py + core/models.py (move models)
  1.2  core/protocols.py (repository interfaces)
  1.3  core/db/orm.py (ORM table models)
  1.4  core/db/engine.py (engine + session)
  1.5  core/db/repositories.py (all SQL repos + FileJournalRepo)
  1.6  core/db/seed.py (demo data)
  1.7  pyproject.toml (add sqlalchemy)
  1.8  tests/test_repositories.py

Epic 2 (Web UI) — includes service layer
  2.1  core/services.py (ProjectService)
  2.2  pyproject.toml (add fastapi, uvicorn, jinja2, markdown)
  2.3  web/app.py
  2.4  web/routes/ (dashboard, tasks, raid, journal, reports)
  2.5  web/templates/ + web/static/
  2.6  tests/test_web.py

Epic 3 (Agent migration)
  3.1  Rewire tools.py → ProjectService
  3.2  Rewire reporter/context.py → ProjectService
  3.3  Rewire agent.py entry point
  3.4  Update create_demo_data.py
  3.5  Update reset.py
  3.6  Delete old models.py, repositories.py, JSON files
  3.7  Update CLAUDE.md
```

---

## Verification

After each epic:

**Epic 1**: Run `tests/test_repositories.py` — all repos read/write correctly against in-memory SQLite.

**Epic 2**:
```bash
uv run python create_demo_data.py          # seeds SQL + journals
uv run uvicorn project_manager_agent.web.app:app --reload
# Visit http://localhost:8000 — verify dashboard, tasks, RAID, journal, reports pages
```

**Epic 3**:
```bash
uv run python reset.py --date 2026-03-19
uv run python create_demo_data.py
uv run python -m project_manager_agent.project_manager.agent   # daily loop runs against SQL
uv run python -m project_manager_agent.reporter.agent           # report generated from SQL
uv run uvicorn project_manager_agent.web.app:app --reload       # web shows agent's changes
```

---

## Critical Files

| File | Role in plan |
|------|-------------|
| `project_manager_agent/models.py` | Source for move → `core/models.py` |
| `project_manager_agent/repositories.py` | API contract to match in SQL repos; deleted in Epic 3 |
| `project_manager_agent/project_manager/tools.py` | 17 tool functions to rewire in Epic 3 |
| `project_manager_agent/reporter/context.py` | `load_all()` to rewire in Epic 3 |
| `project_manager_agent/project_manager/agent.py` | Entry point to rewire in Epic 3 |
| `create_demo_data.py` | Port seeding logic to `core/db/seed.py` |
| `reset.py` | Update to drop/recreate SQL tables |

## New Dependencies

| Package | Epic | Purpose |
|---------|------|---------|
| `sqlalchemy>=2.0` | 1 | ORM + database engine |
| `fastapi` | 2 | Web framework |
| `uvicorn[standard]` | 2 | ASGI server |
| `jinja2` | 2 | HTML templates |
| `markdown` | 2 | Render journal/report .md as HTML |
| `pytest` | 1 (dev) | Test runner |
