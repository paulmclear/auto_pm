# Epic 12: Visual Report Dashboard

## Overview

Replace the current plain-markdown report view with a structured, visual dashboard that presents report data in cards, charts, and tables — while keeping the raw markdown accessible.

## Current State

- Reports are generated as markdown files in `data/reports/`
- The web UI renders them as raw HTML via `markdown2` conversion
- Report content includes: executive summary, milestones, task status, RAID highlights, key risks, recommendations
- The reporter agent writes free-form markdown — there's no structured data format for reports

## Design

### Approach

Two strategies:

**Option A — Parse markdown into structured sections**
- Use heading-based splitting to extract sections from existing markdown reports
- Render each section in a styled card/panel
- Pro: No changes to reporter agent. Con: Fragile if report format changes.

**Option B — Structured report output (recommended)**
- Modify the reporter agent to output both markdown AND a structured JSON alongside it
- The JSON contains typed sections (summary, milestones, task_stats, risks, recommendations)
- The web UI renders from JSON; markdown kept as fallback/download
- Pro: Reliable, enables charts. Con: Requires reporter changes.

**Recommendation**: Option B. The reporter already has full structured data in its context — emit JSON alongside markdown.

### Visual Components

| Section | Visualisation |
|---------|--------------|
| **Executive Summary** | Hero card with RAG status badge, project name, date range, 2-3 sentence summary |
| **Overall Health** | RAG traffic light + trend indicator (improving/stable/declining based on recent reports) |
| **Milestone Timeline** | Horizontal timeline or Gantt-style bar showing planned vs forecast vs actual dates |
| **Task Statistics** | Donut/pie chart: not_started / in_progress / complete / blocked. Bar chart: tasks by phase |
| **Overdue Tasks** | Red-highlighted table of overdue tasks with owner and days overdue |
| **RAID Highlights** | Cards for top risks and open issues, severity-coloured |
| **Recommendations** | Numbered list in a callout/alert box |
| **Trend Charts** | Line charts over time: % complete, open risk count, overdue task count (requires multiple reports) |

### Technology

- **Charts**: Chart.js (lightweight, CDN-loadable, works with AlpineJS)
- **Layout**: Tailwind CSS grid/flexbox cards
- **Data**: JSON endpoint `GET /api/reports/{date}` returns structured report data

### New Components

1. **`agents/reporter/schema.py`** — Pydantic model for structured report output
2. **`agents/reporter/agent.py`** — Modified to emit JSON + markdown
3. **`web/routes/reports.py`** — Enhanced with JSON API endpoint and visual template
4. **`web/templates/report_visual.html`** — Dashboard-style report template with Chart.js

## User Stories

### 12.1 — Structured report schema
Define a Pydantic model for the report output: executive_summary, rag_status, milestone_statuses, task_statistics (by status, by phase), overdue_tasks, raid_highlights, recommendations. The reporter agent outputs this as JSON alongside the markdown.

### 12.2 — Reporter agent structured output
Modify the reporter agent to produce structured JSON output (using the schema) in addition to the markdown file. Store as `data/reports/YYYY-MM-DD.json` alongside the `.md`.

### 12.3 — Report data API endpoint
`GET /api/reports/{date}` returns the structured JSON for a given report date. `GET /api/reports` returns list of available report dates.

### 12.4 — Visual report dashboard
New report detail template with cards, tables, and Chart.js charts rendering the structured data. Tabbed view: "Visual" (default) and "Markdown" (raw). Responsive layout.

### 12.5 — Trend charts across reports
Load data from multiple report JSONs to render trend lines: % tasks complete over time, open risk count, overdue task count. Displayed on the report page or as a dedicated `/trends` view.

## Dependencies

- None on other epics
- Multi-project (Epic 8) will scope reports to the selected project

## Risks

- **Reporter prompt stability**: The LLM must reliably produce valid JSON. Use structured output / function calling to enforce the schema.
- **Historical reports**: Existing markdown-only reports won't have JSON. The visual view should gracefully fall back to rendered markdown.
