# Project Manager Agent

An AI-powered project management agent built with LangGraph and a FastAPI web dashboard.

## Setup

```bash
uv sync
```

Copy `.env.example` to `.env` and set your `OPENAI_API_KEY` (required for the AI agents).

## Load Demo Data

```bash
uv run python create_demo_data.py
```

## Run the Web Dashboard

```bash
uv run uvicorn project_manager_agent.web.app:create_app --factory --reload
```

Then open http://127.0.0.1:8000.

## Run the AI Agents

```bash
# Run the daily project manager loop
uv run python -m project_manager_agent.agents.project_manager.agent

# Generate a status report
uv run python -m project_manager_agent.agents.reporter.agent
uv run python -m project_manager_agent.agents.reporter.agent --output path/to/report.md
```

## Reset Data

```bash
uv run python reset.py
uv run python reset.py --date 2026-03-19 --reports
```

## Lint

```bash
uv run ruff check .
uv run ruff format .
```
