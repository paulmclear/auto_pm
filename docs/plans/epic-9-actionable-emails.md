# Epic 9: Actionable Email Buttons

## Overview

Outbound messages from the PM agent currently queue into the `messages` table with no delivery mechanism. This epic adds **action buttons** to outbound emails that link back to a lightweight web interface, allowing task owners to respond with a single click.

## Current State

- Messages are stored in `messages` table (direction=outbound), but never actually sent
- No email delivery infrastructure exists
- No inbound web endpoints for task owners to interact with

## Design

### How It Works

1. When the PM agent sends a chaser/reminder via `send_message_to_task_owner`, the system generates a set of **action links** based on the message context (overdue task, blocked task, etc.)
2. Each link contains a **signed token** (HMAC or JWT) encoding the action type, task_id, and expiry
3. The email is rendered from a template that includes the action buttons
4. Clicking a button hits a public web route that either performs the action immediately (e.g. mark complete) or renders a short form (e.g. blocker details, new forecast date)

### Action Types

| Action | Trigger Context | Behaviour |
|--------|----------------|-----------|
| **Mark Complete** | Overdue/chaser | One-click: marks task complete, shows thank-you screen |
| **I'm Stuck** | Overdue/chaser | Opens form: text area for blocker details → creates inbound message + optionally adds RAID issue |
| **New Forecast Date** | Overdue/chaser | Opens form: date picker + optional reason → creates inbound message for PM to review |
| **Acknowledge** | General reminder | One-click: logs acknowledgement as inbound message |

### Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│ PM Agent     │────▶│ Email Sender │────▶│ SMTP / Mailgun  │
│ (send_message)│    │ (new module) │     │ (configurable)  │
└─────────────┘     └──────────────┘     └─────────────────┘
                           │
                    renders action URLs
                           │
                    ┌──────▼──────────┐
                    │ /actions/{token} │  ◀── task owner clicks
                    │ (FastAPI routes) │
                    └─────────────────┘
                           │
                    ┌──────▼──────────┐
                    │ Task/Message DB  │
                    └─────────────────┘
```

### New Components

1. **`core/email/`** — Email rendering + sending
   - `renderer.py` — Jinja2 email templates (HTML + plain text)
   - `sender.py` — Pluggable sender (SMTP, Mailgun API, or `console` for dev)
   - `tokens.py` — Action token generation + validation (HMAC-signed, time-limited)

2. **`web/routes/actions.py`** — Public action endpoints
   - `GET /actions/{token}` — Validate token, render confirmation or form
   - `POST /actions/{token}` — Execute the action (update task, create inbound message)
   - Templates: `action_complete.html`, `action_stuck.html`, `action_forecast.html`, `action_thankyou.html`, `action_expired.html`

3. **Config additions** (`data/config.json`)
   - `email.provider`: `"console"` | `"smtp"` | `"mailgun"`
   - `email.from_address`, `email.action_base_url`
   - `email.action_token_expiry_hours`: default 72

## User Stories

### 9.1 — Action token generation and validation
Generate HMAC-signed tokens encoding (action_type, task_id, owner_email, expiry). Validate on receipt. Reject expired or tampered tokens.

### 9.2 — Action web endpoints
FastAPI routes for `/actions/{token}` — GET renders the appropriate page (one-click confirmation or form), POST executes the action. Includes thank-you and expired-token screens.

### 9.3 — Email template rendering
Jinja2 HTML+text email templates that include context-appropriate action buttons. Template selection based on message type (chaser, escalation, general reminder).

### 9.4 — Pluggable email sender
Abstract sender with implementations for console (dev/logging), SMTP, and HTTP API (Mailgun/SendGrid). Configured via `data/config.json`.

### 9.5 — Wire send_message to email pipeline
When `send_message_to_task_owner` is called, render the email template with action buttons and dispatch via the configured sender. Store the rendered email reference in the messages table.

## Dependencies

- None on other epics (can be built independently)
- Multi-project (Epic 8) will later require `project_id` in action tokens

## Risks

- **Security**: Action tokens must be tamper-proof and time-limited. HMAC with server secret + expiry.
- **Email deliverability**: Requires proper SPF/DKIM if using real SMTP. Console mode for dev.
- **Stale actions**: Task may have been updated between email send and click. Validate current state before executing.
