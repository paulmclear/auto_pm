# Epic 10: Chat Interface

## Overview

Add a conversational chat interface to the web app so that humans (project stakeholders, task owners, the sponsor) can ask questions about the project at any time. This is **not** the LangGraph PM agent — it's a separate, lighter LLM-powered chat that has read access to all project data.

## Current State

- No chat capability exists
- The reporter agent already demonstrates how to load full project context into a prompt (`agents/reporter/context.py`)
- The web app is FastAPI + Jinja2 with AlpineJS — no WebSocket infrastructure yet

## Design

### Architecture

```
┌────────────────┐
│  Chat UI        │  (AlpineJS + SSE or WebSocket)
│  /chat          │
└───────┬────────┘
        │ POST /api/chat  {message, conversation_id}
        ▼
┌────────────────┐
│  Chat Backend   │  (FastAPI route)
│                 │──▶ Load project context (like reporter)
│                 │──▶ Retrieve conversation history
│                 │──▶ Call LLM with system prompt + context + history
│                 │──▶ Stream response back
└────────────────┘
        │
        ▼
┌────────────────┐
│  Conversations  │  (SQLite table)
│  table          │
└────────────────┘
```

### Chat Persona

The chat assistant:
- Has **read-only** access to all project data (tasks, RAID, milestones, journal, reports, messages)
- Can answer questions like "What's blocking the API migration?", "Who owns task T-012?", "What happened last week?"
- Does **not** modify data (no task updates, no sending messages) — that's the PM agent's job
- Speaks as a knowledgeable project assistant, not as the PM

### Context Strategy

Two approaches, to be decided during implementation:

**Option A — Full context injection (simpler, works for single project)**
- Reuse `reporter/context.py` pattern: load all project data into the system prompt
- Works well up to ~50 tasks / moderate data volume
- Simple, no tool infrastructure needed

**Option B — Tool-based retrieval (scales better, needed for multi-project)**
- Give the chat LLM read-only tools (fetch_tasks, fetch_raid, fetch_journal, etc.)
- LLM decides what to query based on the question
- More tokens per question but scales to large projects

**Recommendation**: Start with Option A. Migrate to Option B when multi-project (Epic 8) lands.

### Conversation Persistence

- New SQLite table `conversations` (conversation_id, created_at, title)
- New SQLite table `chat_messages` (id, conversation_id, role, content, timestamp)
- Conversations auto-titled from first user message
- Sidebar shows recent conversations

## User Stories

### 10.1 — Chat data model and backend
New `conversations` and `chat_messages` tables. API endpoints: `POST /api/chat/conversations` (create), `POST /api/chat/conversations/{id}/messages` (send message + get response), `GET /api/chat/conversations` (list), `GET /api/chat/conversations/{id}` (load history).

### 10.2 — Chat system prompt and context loading
System prompt that defines the assistant persona. Context loader that injects current project state (reuse/adapt `reporter/context.py`). The LLM should be able to answer questions about tasks, RAID, milestones, journal entries, and reports.

### 10.3 — Chat UI
New `/chat` page with conversation list sidebar and message thread. AlpineJS-driven with streaming response display. Markdown rendering for assistant responses. New conversation and conversation switching.

### 10.4 — Streaming responses
SSE (Server-Sent Events) endpoint for streaming LLM responses token-by-token to the UI, rather than waiting for the full response.

## Dependencies

- None on other epics (can be built independently)
- Multi-project (Epic 8) will scope chat context to the selected project

## Risks

- **Context window limits**: Full project context may grow large. Monitor token usage; Option B is the escape hatch.
- **Cost**: Every chat message includes full project context. Consider caching context and invalidating on data changes.
- **Confusion with PM agent**: Users might try to give instructions ("mark task T-005 complete"). The chat should politely redirect: "I can't modify tasks directly — the PM agent handles that during its daily run, or you can use the action links in your emails."
