# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the project manager agent (daily loop)
uv run python -m project_manager_agent.project_manager.agent

# Run the reporter (generate a status report)
uv run python -m project_manager_agent.reporter.agent
uv run python -m project_manager_agent.reporter.agent --output path/to/report.md

# Load the demo scenario (Customer Portal Modernisation, date=2026-03-20)
uv run python create_demo_data.py

# Reset all runtime data to a clean state
uv run python reset.py
uv run python reset.py --date 2026-03-19 --reports

# Lint
uv run ruff check .
uv run ruff format .
```

## Architecture

This is a **LangGraph-based AI project management agent** with two independent sub-agents:

### Project Manager Agent (`project_manager_agent/project_manager/`)
Runs a structured daily loop via a two-node LangGraph graph:
- `project-manager` node — LLM (gpt-4o-mini) that decides which tools to call
- `tools` node — executes chosen tools via `langgraph.prebuilt.ToolNode`

The agent follows a fixed sequence: read journal → review project plan → review RAID log → read inbox → review tasks → send reminders → update health → write journal. All logic is driven by the LLM using the tool set defined in `tools.py`.

### Reporter Agent (`project_manager_agent/reporter/`)
Not agentic — a straight LLM call. `context.py` reads all data sources and formats them into a prompt string; `reporter/agent.py` sends this to the LLM and writes the markdown report to `data/reports/`.

### Simulated Time (`date_utils.py`)
`REFERENCE_DATE` is loaded at import time from `data/date.json`. It is **not** real time. After each agent run, `advance_reference_date()` increments it by one day. To jump to a specific date, edit `data/date.json` directly: `{"reference_date": "2026-03-20"}`.

### Data Layer (`repositories.py`)
All state is stored as flat JSON/JSONL files under `data/`:

| File | Repository | Notes |
|------|-----------|-------|
| `data/tasks.json` | `TasksRepo` | List of `Task` dataclass dicts |
| `data/project.json` | `ProjectRepo` | Single project with nested phases + milestones |
| `data/raid.json` | `RaidRepo` | RAID log; type-specific optional fields are null for irrelevant types |
| `data/actions.json` | `ActionsRepo` | Action items linked to RAID items or tasks |
| `data/inbox/messages.jsonl` | `Mailbox` | Append-only JSONL; simulates replies from task owners |
| `data/outbox/messages.jsonl` | `Mailbox` | Append-only JSONL; messages sent by the agent |
| `data/journal/YYYY-MM-DD.md` | `Journal` | One markdown file per reference date |
| `data/date.json` | `date_utils` | Persists `REFERENCE_DATE` |

Repos are instantiated fresh on each call (no shared state). All repos have an `initialise()` method that seeds sample data if the file doesn't exist.

### Models (`models.py`)
Pure Python `dataclass` definitions: `Task`, `Phase`, `Milestone`, `Project`, `RaidItem`, `Action`. Dates are `dt.date` objects. `JsonSerialiser` extends `json.JSONEncoder` to handle `dt.date` → ISO string.

### Tools (`project_manager/tools.py`)
Plain functions wrapped with `langchain_core.tools.Tool` (for zero-arg tools using `lambda _:`) or `StructuredTool` + Pydantic input schema (for multi-arg tools). The `tools` list at the bottom is what gets bound to the LLM.

## Backlog

Planned features are tracked in `docs/backlog.json`. Each item has `id`, `title`, `description`, `priority` (high/medium/low), `category`, and `status` (open/complete). Before adding a new capability, check this file to see if it is already planned or in progress. Current open items include per-task outbox tracking, task dependency enforcement, overdue detection, escalation logic, advance-warning reminders, inbox intent parsing, a config file for thresholds, and idempotency guards.