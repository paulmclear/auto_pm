# Ralph Progress Log

This file tracks progress across iterations. Agents update this file
after each iteration and it's included in prompts for context.

## Codebase Patterns (Study These First)

- **API route pattern**: Create router in `web/routes/<name>_api.py` with `APIRouter(prefix="/api/<name>", tags=["<name>"])`. Register in `app.py` via `app.include_router()`. Use `ProjectService(project_id=...)` with try/finally for cleanup.
- **Message access**: `svc.read_inbox()` and `svc.read_outbox()` return `List[Message]` sorted ascending by timestamp. For descending, reverse the list.

---

## 2026-04-06 - pm-7pg.1
- Implemented GET /api/messages endpoint with query params: project_id, direction (inbound/outbound), page, per_page
- Returns id, sender, recipient, subject (first 80 chars of body), date, read status, direction
- Ordered by date descending, paginated response with total/page/per_page metadata
- Files changed: `src/project_manager_agent/web/routes/messages_api.py` (new), `src/project_manager_agent/web/app.py` (router registration)
- **Learnings:**
  - ProjectService exposes `read_inbox()` and `read_outbox()` separately — no combined "read all messages" method, so combining requires merging + re-sorting
  - The `projects_api.py` pattern (non-project-scoped router) is the right model for `/api/*` endpoints that take project_id as a query param
---

## 2026-04-06 - pm-7pg.4
- Added `is_read` boolean column to `messages` table (ORM + Alembic migration with `server_default=sa.text('0')`)
- Added `is_read` field to `Message` dataclass (default `False`)
- Updated `_message_to_domain` to map `is_read` from DB row
- Added `PATCH /api/messages/{message_id}/read?project_id=N` endpoint to mark a message as read
- Updated `GET /api/messages` response to include actual `read` status from DB and `unread_inbox`/`unread_outbox` counts
- Files changed: `core/db/orm.py`, `core/models.py`, `core/db/repositories.py`, `web/routes/messages_api.py`, `alembic/versions/ce7bed265769_*.py`
- **Learnings:**
  - MySQL requires `server_default` when adding NOT NULL columns to existing tables — Alembic autogenerate doesn't add this automatically
  - `get_session()` context manager from `core/db/engine.py` is useful for direct ORM queries in API endpoints outside of `ProjectService`
---


## 2026-04-06 - pm-7pg.3
- Implemented reading pane that displays full message content for selected message
- Added GET `/api/messages/{message_id}` endpoint returning full body, task_id, and all metadata
- Reading pane header shows from, to, date, and related task as a clickable link
- Body renders full message text with whitespace preserved (`whitespace-pre-wrap`)
- Empty state ("Select a message to read") when no message selected
- Auto-selects first message on page load
- Files changed: `web/routes/messages_api.py` (new endpoint), `web/templates/messages.html` (reading pane + auto-select)
- **Learnings:**
  - The existing list endpoint only returns truncated subject — a separate detail endpoint is needed for full body
  - `selectedDetail` pattern: keep list item in `selected` for instant UI, fetch full detail asynchronously into `selectedDetail`
---

## 2026-04-06 - pm-7pg.2
- Implemented email-client layout with two-column design: left pane (1/3) message list, right pane (2/3) reading area
- Inbox/Outbox tab switching with unread count badges
- Message list items show sender/recipient, subject snippet, date, unread dot indicator
- Selected message highlighted with indigo border
- AlpineJS manages selection state, tab switching, and API calls to /api/messages
- Auto-marks messages as read on selection via PATCH /api/messages/{id}/read
- Files changed: `web/routes/messages.py` (new), `web/templates/messages.html` (new), `web/app.py` (router registration), `web/templates/_nav.html` (nav link)
- **Learnings:**
  - The existing /api/messages endpoint from pm-7pg.1 provides all the data needed for the list pane — no new API work required
  - AlpineJS x-data + x-init pattern works well for SPA-like behavior within Jinja templates
---

## 2026-04-06 - pm-7pg.5
- Added responsive/mobile layout to messages page using Alpine.js `mobileView` state + Tailwind responsive classes
- On mobile (<md): list takes full width; tapping a message switches to full-screen reading pane with back button
- On desktop (md+): unchanged two-column layout
- Back button (mobile-only, `md:hidden`) returns to list view; tab switching resets to list view
- Files changed: `web/templates/messages.html`
- **Learnings:**
  - Alpine.js state + Tailwind `md:` breakpoint classes + `hidden` is a clean pattern for mobile list/detail view switching without any extra JS framework
  - Using `:class` binding with `hidden md:block` lets you toggle mobile visibility while keeping desktop layout intact
---

## 2026-04-06 - pm-cyq.1
- Implemented inbox message composer form as a modal overlay on the messages page
- Added "Compose" button in messages header that opens a modal with fields: from (dropdown), subject, body, related task ID, date
- From dropdown populated via `GET /api/messages/stakeholders` endpoint (unique task owners from DB)
- Date defaults to REFERENCE_DATE passed from the route handler
- Form validation: sender (from dropdown) and body are required; Pydantic validates on the API side too
- Added `POST /api/messages` endpoint that creates an inbound message in the DB
- Fixed route ordering: moved `/stakeholders` before `/{message_id}` to avoid path parameter conflict
- Files changed: `web/routes/messages_api.py` (stakeholders + compose endpoints), `web/routes/messages.py` (pass reference_date to template), `web/templates/messages.html` (compose button + modal + Alpine.js state)
- **Learnings:**
  - FastAPI path parameter routes (`/{message_id}`) must come AFTER literal routes (`/stakeholders`) to avoid the literal being matched as a path parameter
  - For inbound messages, `owner_name`/`owner_email` represent the recipient (PM agent) and `sender_name`/`sender_email` represent who sent it
  - The `x-cloak` directive on Alpine.js modals prevents flash of unstyled content on page load
---

## 2026-04-06 - pm-cyq.3
- Added "Message" link with envelope icon on each task row in the tasks table
- Link navigates to messages page with query params: `compose=1`, `taskId`, `subject` (pre-filled with task ID and description)
- Added `init()` method to messagesApp Alpine.js component that reads URL query params and auto-opens composer with pre-filled values
- Cleans URL after extracting params via `history.replaceState`
- Files changed: `web/templates/tasks.html` (action column + message link), `web/templates/messages.html` (init method + x-init update)
- **Learnings:**
  - Query param approach (`?compose=1&taskId=X&subject=Y`) is clean for cross-page compose triggers — no shared state needed
  - `window.history.replaceState({}, '', window.location.pathname)` cleanly strips query params without reload
---

## 2026-04-06 - pm-cyq.2
- Added template selector dropdown at top of composer modal with 5 templates: Status Update, Blocker Report, Risk Escalation, Completion Notice, Question
- "Custom (no template)" option clears subject and body fields
- Selecting a template pre-fills subject and body with placeholder text; user can edit before sending
- Preserves existing compose state (from, taskId, date) when switching templates
- Files changed: `web/templates/messages.html` (template data, dropdown, applyTemplate method)
- **Learnings:**
  - Template logic is purely frontend — no API changes needed; Alpine.js state + `@change` handler keeps it simple
  - Using `$event.target.value` in the `@change` handler avoids needing to bind a separate model for the template selector
---

## 2026-04-06 - pm-bpy.1
- Defined `StructuredReport` Pydantic model in `agents/reporter/schema.py` with: executive_summary, rag_status, milestone_statuses, task_statistics (by_status + by_phase), overdue_tasks, raid_highlights, recommendations
- Added `build_structured_report()` in `agents/reporter/agent.py` that computes quantitative fields directly from context data (accurate) and extracts narrative fields from LLM markdown output
- Updated `save_report()` to write `.json` alongside `.md` using `model_dump_json()`
- Updated `run()` to build and pass structured report through the pipeline
- Files changed: `agents/reporter/schema.py` (new), `agents/reporter/agent.py` (updated)
- **Learnings:**
  - Quantitative fields (task stats, milestones, overdue) should be computed from raw data, not parsed from LLM markdown — guarantees accuracy
  - Executive summary extraction via simple section-header parsing is reliable given the strict prompt template
---

## 2026-04-06 - pm-bpy.2
- Work already completed as part of pm-bpy.1 — no additional code changes needed
- Verified: schema.py defines StructuredReport, agent.py builds structured data and saves .json alongside .md
- Lint passes clean
- **Learnings:**
  - When a parent bead implements child bead work, verify and close rather than re-implementing
---

## 2026-04-06 - pm-bpy.3
- Implemented `GET /api/reports?project_id=N` — returns list of available report dates (newest first) with date and stem name
- Implemented `GET /api/reports/{date}?project_id=N` — returns structured JSON for a given report date (from the `.json` files saved alongside `.md` reports)
- Added `get_report_json()` method to `ProjectService` for clean data access
- Files changed: `web/routes/reports_api.py` (new), `web/app.py` (router registration), `core/services.py` (new method)
- **Learnings:**
  - Structured report JSON files are saved alongside markdown by the reporter agent — just need to read and serve them
  - Avoid accessing private `_reports_dir` from API routes; add a proper service method instead
---

## 2026-04-06 - pm-bpy.5
- Implemented trend charts across reports on the reports list page
- Added `GET /api/reports/trends?project_id=N` endpoint that loads all report JSONs and extracts: % tasks complete, open risk count, overdue task count per date
- Added `list_report_jsons()` method to `ProjectService` for loading all structured report JSON files
- Charts rendered with Chart.js (line charts with fill) via Alpine.js — only shown when 2+ reports exist
- Files changed: `core/services.py` (new method), `web/routes/reports_api.py` (trends endpoint), `web/templates/reports_list.html` (chart UI)
- **Learnings:**
  - Chart.js loaded via CDN works well with the existing Tailwind + Alpine.js stack — no build tooling needed
  - The `/trends` endpoint must be registered before `/{date}` to avoid FastAPI matching "trends" as a date parameter (same pattern as messages stakeholders route)
---

## 2026-04-06 - pm-bpy.4
- Implemented visual report dashboard on the report detail page
- Added tabbed view: Visual (default) shows cards/tables/charts, Markdown tab shows raw rendered markdown
- RAG status card with color-coded circle + reason text
- Executive summary card spanning 3/4 width
- Task statistics: 4 summary cards (complete, in progress, not started, blocked) + doughnut chart by status + stacked bar chart by phase
- Milestones table with status badges (achieved/missed/pending)
- Overdue tasks table with days-overdue badges
- RAID highlights table with color-coded type badges
- Recommendations list with priority badges
- Graceful fallback: if no structured JSON exists, shows warning and markdown view
- Files changed: `web/routes/reports.py` (pass report_data JSON to template), `web/templates/reports_detail.html` (full rewrite)
- **Learnings:**
  - Jinja2's `tojson` filter is essential for safely passing Python dicts to JavaScript in templates
  - When structured data may not exist (no JSON file), the template should handle both states — conditional rendering with a fallback to the existing markdown view
---
