# Epic 11: Web-Triggered PM Agent Run

## Overview

Allow the PM agent's daily loop to be triggered from the web UI instead of only via CLI (`python -m project_manager_agent.agents.project_manager.agent`). The web interface provides a trigger button, live progress feedback via SSE, run history, and date control for demo/testing.

## Current State

- The PM agent runs via `__main__` in `agents/project_manager/agent.py`
- It's a synchronous LangGraph invocation that prints to stdout
- The `data/status.json` snapshot is written at the end of each run
- Idempotency guard prevents same-day reruns (checks journal existence)
- `advance_reference_date()` increments the simulated date after each run

## Design

### Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│  Web UI      │────▶│ POST /api/agent  │────▶│ Background  │
│  /agent      │     │   /run           │     │ Task        │
└─────────────┘     └──────────────────┘     │ (asyncio)   │
       │                                      └──────┬──────┘
       │  GET /api/agent/status                      │
       │◀────────────────────────────────────────────┘
       │  (SSE stream)                        Runs LangGraph
       │                                      agent graph
       ▼
┌─────────────┐
│  Run History │
│  /agent/runs │
└─────────────┘
```

### Key Decisions

1. **Background execution**: The agent run takes 30-60s+. It must run in a background task, not block the HTTP request.
2. **Single-run lock**: Only one agent run at a time. Reject concurrent requests with 409.
3. **Output capture**: Redirect agent output (tool calls, LLM responses) to a log that the UI can stream via SSE.
4. **Date control**: The UI shows the current `REFERENCE_DATE` and allows setting it before a run (for demo/testing).
5. **Idempotency**: The existing same-day guard is respected and surfaced to the user as a clear message.

### Run State Machine

```
idle → running → completed
              → failed
```

### Agent Event Capture

The existing LangGraph agent streams events. We tap into these for progress:
- Node transitions (project-manager → tools → project-manager)
- Tool calls (which tool, arguments summary)
- Final state

Events are captured per run, stored in the run log, and streamed to the UI via SSE.

### New Components

1. **`agents/project_manager/runner.py`** — Extracted run logic
   - Refactor `agent.py` `__main__` block into a callable `run_agent(project_id=None)` function
   - Return structured result (success/failure, journal written, date advanced, errors)
   - Capture LLM/tool output into a log buffer

2. **`web/routes/agent.py`** — Agent management endpoints
   - `GET /agent` — UI page showing current status, run button, date control, run history
   - `POST /api/agent/run` — Trigger a new agent run (returns 202 Accepted or 409 Conflict)
   - `GET /api/agent/status` — Current run state + SSE event stream for live progress
   - `GET /api/agent/runs` — Run history with timestamps and outcomes

3. **Run history table** — SQLite table `agent_runs` (run_id, started_at, completed_at, status, reference_date, log_output, error)

## User Stories

### 11.1 — Extract agent runner function
Refactor the PM agent's `__main__` block into a reusable `run_agent(project_id=None)` function that returns a structured result. Captures tool call events as structured log entries. Keep CLI entry point working by calling this function.
- **Acceptance**: Agent can be triggered programmatically; events are captured; CLI still works

### 11.2 — Agent run API endpoints and SSE
- `POST /api/agent/run` — starts background agent run, returns run ID or 409
- `GET /api/agent/status/{run_id}` — SSE stream of events for a running agent
- `GET /api/agent/runs` — JSON list of past runs
- Run metadata stored in `agent_runs` table (new ORM model)
- Concurrency lock (reject if already running); respects existing idempotency guard
- **Acceptance**: Can trigger agent via HTTP; can stream progress; can list past runs; concurrent runs rejected

### 11.3 — Agent run web UI
- Dedicated `/agent` page with "Run Agent" button (disabled while running or already run today)
- Live progress panel showing current step and tool calls via SSE
- Scrollable log output
- Run history table with start/end time, status, link to journal
- **Acceptance**: Full trigger → progress → completion flow works from the browser

### 11.4 — Date control from web UI
- Current `REFERENCE_DATE` displayed on the agent page
- Date picker to set a new date before triggering a run
- `POST /api/agent/date` with `{"date": "2026-03-21"}`
- **Acceptance**: Can change the simulated date from the browser; agent runs use the new date

## Dependencies

- None on other epics (can be built independently)
- Multi-project (Epic 8) will add project selection to the run trigger

## Risks

- **Concurrency**: Must enforce single-run lock. Use an in-memory lock (asyncio.Lock) since this is a single-process app.
- **Long-running requests**: Agent runs can take minutes. Background task + SSE is the right pattern.
- **Error handling**: Agent failures (LLM errors, tool exceptions) must be caught and reported, not crash the web server.
