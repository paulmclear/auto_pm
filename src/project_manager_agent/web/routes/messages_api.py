"""API routes for message list."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from project_manager_agent.core.db.engine import get_session
from project_manager_agent.core.db.orm import MessageRow
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
