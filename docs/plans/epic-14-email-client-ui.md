# Epic 14: Email-Client Inbox & Outbox UI

## Overview

Redesign the inbox and outbox views to look and feel like a modern email client — a selectable list pane on the left showing messages in date-descending order, and a reading pane on the right displaying the selected message. Built with TailwindCSS / TailwindUI (Plus licence).

## Problem Statement

The current inbox/outbox views are basic table listings. They don't support quickly scanning and reading messages, which is the primary use case for stakeholders and for testing the PM agent's messaging behaviour.

## Design

### Layout

```
┌──────────────────────────────────────────────────────────┐
│  Inbox    Outbox    [Compose]                            │
├────────────────────┬─────────────────────────────────────┤
│  Message List      │  Reading Pane                       │
│  (left, ~1/3)      │  (right, ~2/3)                      │
│                    │                                     │
│  ┌──────────────┐  │  From: Alice Chen                   │
│  │ ▸ Alice Chen  │  │  Date: 2026-03-19                   │
│  │   Re: T-005   │  │  Re: Task T-005 — API Migration     │
│  │   Mar 19      │  │                                     │
│  ├──────────────┤  │  Hi PM,                              │
│  │   Bob Smith   │  │                                     │
│  │   Blocker...  │  │  Task T-005 is blocked by the       │
│  │   Mar 18      │  │  vendor delay. We need to escalate  │
│  ├──────────────┤  │  to the steering committee...        │
│  │   Carol Lee   │  │                                     │
│  │   Status...   │  │                                     │
│  │   Mar 17      │  │                                     │
│  └──────────────┘  │                                     │
└────────────────────┴─────────────────────────────────────┘
```

### TailwindUI Components

Reference components from TailwindUI Plus (https://tailwindcss.com/plus/ui-blocks/application-ui):

- **Stacked List** — For the message list pane. Each item shows sender, subject snippet, date, and unread indicator.
- **Panel / Card** — For the reading pane. Header with metadata (from, to, date, subject), body content below.
- **Tabs** — For Inbox / Outbox switching (or Sent).
- **Button** — For Compose action.
- **Empty State** — When no messages exist or none selected.
- **Badge** — For unread count, message direction (inbound/outbound), related task links.

### Interaction

1. **Page load**: Message list loads with most recent first. First message auto-selected. Reading pane shows its content.
2. **Click message**: Selected message highlighted in list. Reading pane updates (no page reload — AlpineJS).
3. **Tab switch**: Inbox shows `direction=inbound`, Outbox shows `direction=outbound`. Selection resets to first item.
4. **Compose button**: Opens composer (Epic 13) or slides in a compose panel.
5. **Responsive**: On mobile, list is full-width; tapping a message navigates to a detail view (back button to return).

### Data

Uses existing `messages` table. API endpoints:
- `GET /api/messages?direction=inbound&page=1` — Paginated message list (id, sender, subject/snippet, date, read status)
- `GET /api/messages/{id}` — Full message content

### New / Modified Components

1. **`web/routes/messages.py`** — Updated routes
   - `GET /messages` — Renders the email-client shell (list + reading pane)
   - `GET /api/messages` — JSON list endpoint with direction filter, pagination, ordering
   - `GET /api/messages/{id}` — JSON single message endpoint

2. **`web/templates/messages.html`** — Email-client layout template
   - Two-column layout using TailwindCSS grid
   - Left pane: message list (AlpineJS-driven, fetches from API)
   - Right pane: reading pane (updates on selection)
   - Tabs for Inbox/Outbox
   - Compose button linking to Epic 13 composer

3. **`web/static/`** — Any additional JS for the message selection interaction (likely minimal with AlpineJS)

### Read/Unread Tracking

Add a `read` boolean column to the `messages` table (default false). When a message is selected in the reading pane, mark it as read via `PATCH /api/messages/{id}/read`. Unread messages show with bold text / blue dot in the list.

## User Stories

### 14.1 — Message list API
- `GET /api/messages` with query params: `direction` (inbound/outbound), `page`, `per_page`
- Returns: id, sender/recipient, subject snippet (first 80 chars of body), date, read status
- Ordered by date descending
- **Acceptance**: API returns paginated, filtered message list as JSON

### 14.2 — Email-client layout and message list pane
- Two-column TailwindCSS layout: left pane (~1/3 width) with stacked message list, right pane (~2/3) for reading
- Message list items show: sender name, subject/snippet, date, unread indicator
- Selected message highlighted with distinct background
- Tabs at top for Inbox / Outbox switching
- AlpineJS for selection state and tab switching (no page reloads)
- **Acceptance**: Can see message list; can switch between inbox and outbox; selected item is highlighted

### 14.3 — Reading pane
- Right pane displays full message content for the selected message
- Header: from, to, date, related task (as link)
- Body: full message text with whitespace preserved
- Empty state when no message selected
- Auto-selects first message on page load
- **Acceptance**: Clicking a message in the list shows its full content in the reading pane

### 14.4 — Read/unread tracking
- Add `read` boolean column to `messages` table
- Mark as read when selected in reading pane (`PATCH /api/messages/{id}/read`)
- Unread messages display with bold text and/or blue dot indicator
- Unread count shown on Inbox/Outbox tabs
- **Acceptance**: New messages appear unread; selecting marks as read; visual distinction works

### 14.5 — Responsive / mobile layout
- On small screens, list takes full width
- Tapping a message navigates to a detail view (reading pane full-screen)
- Back button returns to list
- **Acceptance**: Usable on mobile-width screens

## Dependencies

- Epic 13 (Inbox Composer) provides the compose functionality linked from the Compose button
- No hard dependency — the email-client UI works without the composer; the button can be added when Epic 13 lands

## Risks

- **Message schema**: May need to add `subject` field to messages table if not already present. Current schema may only have `body`.
- **Performance**: Large message volumes could slow the list. Pagination handles this.
- **TailwindUI licence**: Components must be adapted from TailwindUI Plus, not copied verbatim into open-source. Fine for this private project.
