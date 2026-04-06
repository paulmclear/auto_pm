"""API routes for message list."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from project_manager_agent.core.db.engine import get_session
from project_manager_agent.core.db.orm import MessageRow, TaskRow
from project_manager_agent.core.services import ProjectService

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.get("")
async def list_messages(
    project_id: int,
    direction: Optional[str] = Query(None, pattern="^(inbound|outbound)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """Return paginated, filtered message list as JSON."""
    svc = ProjectService(project_id=project_id)
    try:
        # Always load all messages for unread counts
        inbox = svc.read_inbox()
        outbox = svc.read_outbox()

        if direction == "inbound":
            messages = list(reversed(inbox))
        elif direction == "outbound":
            messages = list(reversed(outbox))
        else:
            messages = inbox + outbox
            messages.sort(key=lambda m: m.timestamp, reverse=True)

        total = len(messages)
        start = (page - 1) * per_page
        page_items = messages[start : start + per_page]

        unread_inbox = sum(1 for m in inbox if not m.is_read)
        unread_outbox = sum(1 for m in outbox if not m.is_read)

        return {
            "items": [
                {
                    "id": m.message_id,
                    "sender": m.sender_name,
                    "recipient": m.owner_name,
                    "subject": m.message[:80],
                    "date": m.timestamp,
                    "read": m.is_read,
                    "direction": m.direction,
                }
                for m in page_items
            ],
            "total": total,
            "page": page,
            "per_page": per_page,
            "unread_inbox": unread_inbox,
            "unread_outbox": unread_outbox,
        }
    finally:
        svc.close()


@router.get("/stakeholders")
async def list_stakeholders(project_id: int):
    """Return unique task owners for the compose form 'from' dropdown."""
    with get_session() as session:
        rows = (
            session.query(TaskRow.owner_name, TaskRow.owner_email)
            .filter(TaskRow.project_id == project_id)
            .distinct()
            .order_by(TaskRow.owner_name)
            .all()
        )
        return [{"name": r.owner_name, "email": r.owner_email} for r in rows]


@router.get("/{message_id}")
async def get_message(message_id: str, project_id: int):
    """Return full message content."""
    svc = ProjectService(project_id=project_id)
    try:
        for msg in svc.read_inbox() + svc.read_outbox():
            if msg.message_id == message_id:
                return {
                    "id": msg.message_id,
                    "sender": msg.sender_name,
                    "recipient": msg.owner_name,
                    "body": msg.message,
                    "date": msg.timestamp,
                    "read": msg.is_read,
                    "direction": msg.direction,
                    "task_id": msg.task_id,
                }
        raise HTTPException(status_code=404, detail="Message not found")
    finally:
        svc.close()


@router.patch("/{message_id}/read")
async def mark_message_read(message_id: str, project_id: int):
    """Mark a message as read."""
    with get_session() as session:
        row = (
            session.query(MessageRow)
            .filter(
                MessageRow.message_id == message_id,
                MessageRow.project_id == project_id,
            )
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Message not found")
        row.is_read = True
        session.commit()
        return {"id": message_id, "read": True}


class ComposeRequest(BaseModel):
    project_id: int
    sender_name: str
    sender_email: str
    subject: str = ""
    body: str = Field(..., min_length=1)
    task_id: Optional[int] = None
    date: Optional[str] = None  # ISO date string


@router.post("", status_code=201)
async def compose_message(payload: ComposeRequest):
    """Create a new inbound message (simulates stakeholder sending to PM)."""
    from project_manager_agent.core.date_utils import REFERENCE_DATE

    timestamp = payload.date or REFERENCE_DATE.isoformat()
    # Prepend subject to body if provided, matching how existing messages work
    message_text = payload.body
    if payload.subject:
        message_text = f"Subject: {payload.subject}\n\n{payload.body}"

    with get_session() as session:
        row = MessageRow(
            message_id=str(uuid.uuid4()),
            project_id=payload.project_id,
            direction="inbound",
            timestamp=timestamp,
            owner_name="Project Manager Agent",
            owner_email="pm-agent@system.local",
            message=message_text,
            sender_name=payload.sender_name,
            sender_email=payload.sender_email,
            task_id=payload.task_id,
            is_read=False,
        )
        session.add(row)
        session.commit()
        return {"id": row.message_id, "status": "created"}
