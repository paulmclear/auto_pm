"""API routes for message list."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

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
        if direction == "inbound":
            messages = svc.read_inbox()
        elif direction == "outbound":
            messages = svc.read_outbox()
        else:
            # Both directions
            messages = svc.read_inbox() + svc.read_outbox()
            messages.sort(key=lambda m: m.timestamp, reverse=True)

        # Sort descending by date (inbox/outbox are ascending by default)
        if direction is not None:
            messages = list(reversed(messages))

        total = len(messages)
        start = (page - 1) * per_page
        page_items = messages[start : start + per_page]

        return {
            "items": [
                {
                    "id": m.message_id,
                    "sender": m.sender_name,
                    "recipient": m.owner_name,
                    "subject": m.message[:80],
                    "date": m.timestamp,
                    "read": True,
                    "direction": m.direction,
                }
                for m in page_items
            ],
            "total": total,
            "page": page,
            "per_page": per_page,
        }
    finally:
        svc.close()
