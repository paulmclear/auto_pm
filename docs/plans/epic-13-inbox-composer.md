# Epic 13: Web Inbox Composer

## Overview

Add the ability to create inbound inbox messages from the web UI. Since this system runs in a simulated environment without real email/Slack connectivity, the web UI serves as the primary interface for stakeholders to send messages to the PM agent — simulating what would be emails or chat messages in a production deployment.

## Problem Statement

The PM agent reads inbound messages from the `messages` table each day, but there's no way to create them except via the demo seed data or direct DB manipulation. To properly test the agent's inbox-processing behaviour (intent parsing, action creation, RAID escalation), we need a convenient way to compose and send messages as different stakeholders.

## Design

### Architecture

A simple form-based composer that inserts rows into the existing `messages` table with `direction='inbound'`.

### Composer Fields

| Field | Type | Notes |
|-------|------|-------|
| **From** | Dropdown | Pre-populated from task owners + known stakeholders. Also allows free-text entry for new senders. |
| **Subject** | Text input | Maps to message subject/context field |
| **Body** | Textarea | The message content. Supports multi-line plain text. |
| **Related Task** | Optional dropdown | Links the message to a specific task (populated from task list) |
| **Date** | Date picker | Defaults to current `REFERENCE_DATE`. Allows backdating for testing scenarios. |

### Message Types / Templates

Quick-fill templates for common test scenarios:
- **Status Update** — "Task T-XXX is progressing well, expect completion by [date]"
- **Blocker Report** — "T-XXX is blocked by [reason]. Need help from [person]"
- **Risk Escalation** — "New risk identified: [description]. Impact: [high/medium/low]"
- **Completion Notice** — "T-XXX is now complete"
- **Question** — "Can you clarify [topic]?"
- **Custom** — Blank form

### New Components

1. **`web/routes/inbox.py`** (or extend existing messages route)
   - `GET /inbox/compose` — Render the composer form
   - `POST /api/inbox/messages` — Create a new inbound message
   - Returns to inbox view with success confirmation

2. **`web/templates/inbox_compose.html`** — Composer form template (TailwindCSS)

## User Stories

### 13.1 — Inbox message composer form
- Web form at `/inbox/compose` with fields: from, subject, body, related task (optional), date
- Dropdown for "from" populated from known stakeholders (task owners from DB)
- Date defaults to current `REFERENCE_DATE`
- Form validation (from + body required)
- **Acceptance**: Can compose and submit a message; it appears in the inbox; PM agent picks it up on next run

### 13.2 — Message templates
- Template selector dropdown at top of composer
- Selecting a template pre-fills subject and body with placeholder text
- Templates: Status Update, Blocker Report, Risk Escalation, Completion Notice, Question, Custom
- **Acceptance**: Selecting a template fills the form; user can edit before sending

### 13.3 — Compose from task context
- "Send message about this task" link on task detail/list views
- Opens composer with task pre-selected and subject pre-filled
- **Acceptance**: Can navigate from a task to a pre-filled compose form

## Dependencies

- None on other epics
- Uses existing `messages` table schema (no DB changes needed)
- Epic 14 (email-client UI) will provide the inbox view this composer integrates with

## Risks

- **Schema fit**: The existing `messages` table may not have all fields the composer needs (e.g., subject). May need a minor schema addition.
- **Sender identity**: In production, senders would be authenticated. Here we use a dropdown — adequate for testing but should not be confused with real auth.
