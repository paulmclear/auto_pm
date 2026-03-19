"""
Project Manager — Tool definitions
===================================
Tool functions, Pydantic input schemas, and LangChain tool instances used by
the project manager agent.
"""

from typing import Literal, Optional

from langchain_core.tools import Tool, StructuredTool
from pydantic import BaseModel

from project_manager_agent.core.date_utils import REFERENCE_DATE
from project_manager_agent.core.repositories import (
    TasksRepo,
    ProjectRepo,
    RaidRepo,
    ActionsRepo,
    Mailbox,
    Journal,
)


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------


def read_last_journal() -> str:
    content = Journal().read_last()
    return content if content is not None else "No previous journal found."


def read_outbox() -> list[dict]:
    return Mailbox().read_outbox()


def read_inbox() -> list[dict]:
    return Mailbox().read_inbox()


def send_message(owner_name: str, owner_email: str, message: str) -> str:
    Mailbox().send(owner_name, owner_email, message)
    print(f"Message queued for {owner_name} ({owner_email}): {message}")
    return f"Message queued for {owner_name}"


def update_task_status(task_id: int, status: str) -> str:
    try:
        TasksRepo().update_status(task_id, status)  # type: ignore[arg-type]
        print(f"Task {task_id} status updated to '{status}'")
        return f"Task {task_id} status updated to '{status}'"
    except ValueError as e:
        return str(e)


def update_task_blocking(
    task_id: int, blocked_reason: Optional[str], depends_on: Optional[list]
) -> str:
    try:
        TasksRepo().update_blocking(task_id, blocked_reason, depends_on)
        return f"Task {task_id} blocking info updated."
    except ValueError as e:
        return str(e)


def write_journal_entry(section: str, content: str) -> str:
    Journal().write(section, content)
    return f"Journal entry written: {section}"


def fetch_project_plan() -> dict:
    return ProjectRepo().read()


def update_project_health(
    rag_status: Optional[str], rag_reason: Optional[str], forecast_end: Optional[str]
) -> str:
    ProjectRepo().update_health(rag_status, rag_reason, forecast_end)
    parts = []
    if rag_status:
        parts.append(f"RAG → {rag_status}")
    if forecast_end:
        parts.append(f"forecast end → {forecast_end}")
    return "Project health updated: " + ", ".join(parts) if parts else "No changes."


def update_milestone(
    milestone_id: int,
    status: Optional[str],
    forecast_date: Optional[str],
    actual_date: Optional[str],
) -> str:
    try:
        ProjectRepo().update_milestone(milestone_id, status, forecast_date, actual_date)
        return f"Milestone {milestone_id} updated."
    except ValueError as e:
        return str(e)


def fetch_raid_items() -> list[dict]:
    return RaidRepo().read()


def add_raid_item(
    type: str,
    title: str,
    description: str,
    owner: str,
    linked_task_ids: list,
    probability: Optional[str],
    impact: Optional[str],
    mitigation: Optional[str],
    review_date: Optional[str],
    validation_method: Optional[str],
    validation_date: Optional[str],
    severity: Optional[str],
    rationale: Optional[str],
    decided_by: Optional[str],
    decision_date: Optional[str],
    alternatives_considered: Optional[str],
) -> str:
    item = {
        "raid_id": None,
        "type": type,
        "title": title,
        "description": description,
        "owner": owner,
        "raised_date": REFERENCE_DATE.isoformat(),
        "status": "open",
        "linked_task_ids": linked_task_ids,
        "probability": probability,
        "impact": impact,
        "mitigation": mitigation,
        "review_date": review_date,
        "validation_method": validation_method,
        "validation_date": validation_date,
        "validated_by": None,
        "severity": severity,
        "resolution": None,
        "resolved_date": None,
        "rationale": rationale,
        "decided_by": decided_by,
        "decision_date": decision_date,
        "alternatives_considered": alternatives_considered,
    }
    raid_id = RaidRepo().add(item)
    print(f"RAID item {raid_id} added: [{type}] {title}")
    return f"RAID item {raid_id} added."


def update_raid_item(
    raid_id: int,
    status: Optional[str],
    probability: Optional[str],
    impact: Optional[str],
    mitigation: Optional[str],
    review_date: Optional[str],
    validation_method: Optional[str],
    validation_date: Optional[str],
    validated_by: Optional[str],
    severity: Optional[str],
    resolution: Optional[str],
    resolved_date: Optional[str],
    rationale: Optional[str],
    decided_by: Optional[str],
    decision_date: Optional[str],
    alternatives_considered: Optional[str],
) -> str:
    fields = {
        "status": status,
        "probability": probability,
        "impact": impact,
        "mitigation": mitigation,
        "review_date": review_date,
        "validation_method": validation_method,
        "validation_date": validation_date,
        "validated_by": validated_by,
        "severity": severity,
        "resolution": resolution,
        "resolved_date": resolved_date,
        "rationale": rationale,
        "decided_by": decided_by,
        "decision_date": decision_date,
        "alternatives_considered": alternatives_considered,
    }
    try:
        RaidRepo().update(raid_id, fields)
        print(f"RAID item {raid_id} updated.")
        return f"RAID item {raid_id} updated."
    except ValueError as e:
        return str(e)


def fetch_actions() -> list[dict]:
    return ActionsRepo().read()


def add_action(
    description: str,
    owner_name: str,
    owner_email: str,
    due_date: str,
    source_raid_id: Optional[int],
    source_task_id: Optional[int],
) -> str:
    action = {
        "action_id": None,
        "description": description,
        "owner_name": owner_name,
        "owner_email": owner_email,
        "due_date": due_date,
        "status": "open",
        "source_raid_id": source_raid_id,
        "source_task_id": source_task_id,
    }
    action_id = ActionsRepo().add(action)
    print(f"Action {action_id} added: {description}")
    return f"Action {action_id} added."


def update_action_status(action_id: int, status: str) -> str:
    try:
        ActionsRepo().update_status(action_id, status)  # type: ignore[arg-type]
        print(f"Action {action_id} status updated to '{status}'")
        return f"Action {action_id} status updated to '{status}'"
    except ValueError as e:
        return str(e)


# ---------------------------------------------------------------------------
# Pydantic input schemas
# ---------------------------------------------------------------------------


class UpdateTaskStatusInput(BaseModel):
    task_id: int
    status: Literal["not_started", "in_progress", "complete", "blocked"]


class UpdateTaskBlockingInput(BaseModel):
    task_id: int
    blocked_reason: Optional[str] = None
    depends_on: Optional[list] = None


class SendMessageInput(BaseModel):
    owner_name: str
    owner_email: str
    message: str


class WriteJournalEntryInput(BaseModel):
    section: str
    content: str


class UpdateProjectHealthInput(BaseModel):
    rag_status: Optional[Literal["green", "amber", "red"]] = None
    rag_reason: Optional[str] = None
    forecast_end: Optional[str] = None  # ISO date string


class UpdateMilestoneInput(BaseModel):
    milestone_id: int
    status: Optional[Literal["pending", "achieved", "missed"]] = None
    forecast_date: Optional[str] = None  # ISO date string
    actual_date: Optional[str] = None  # ISO date string


class AddRaidItemInput(BaseModel):
    type: Literal["risk", "assumption", "issue", "decision"]
    title: str
    description: str
    owner: str
    linked_task_ids: list = []
    # Risk
    probability: Optional[Literal["high", "medium", "low"]] = None
    impact: Optional[Literal["high", "medium", "low"]] = None
    mitigation: Optional[str] = None
    review_date: Optional[str] = None
    # Assumption
    validation_method: Optional[str] = None
    validation_date: Optional[str] = None
    # Issue
    severity: Optional[Literal["high", "medium", "low"]] = None
    # Decision
    rationale: Optional[str] = None
    decided_by: Optional[str] = None
    decision_date: Optional[str] = None
    alternatives_considered: Optional[str] = None


class UpdateRaidItemInput(BaseModel):
    raid_id: int
    status: Optional[Literal["open", "closed", "accepted", "superseded"]] = None
    probability: Optional[Literal["high", "medium", "low"]] = None
    impact: Optional[Literal["high", "medium", "low"]] = None
    mitigation: Optional[str] = None
    review_date: Optional[str] = None
    validation_method: Optional[str] = None
    validation_date: Optional[str] = None
    validated_by: Optional[str] = None
    severity: Optional[Literal["high", "medium", "low"]] = None
    resolution: Optional[str] = None
    resolved_date: Optional[str] = None
    rationale: Optional[str] = None
    decided_by: Optional[str] = None
    decision_date: Optional[str] = None
    alternatives_considered: Optional[str] = None


class AddActionInput(BaseModel):
    description: str
    owner_name: str
    owner_email: str
    due_date: str  # ISO date string
    source_raid_id: Optional[int] = None
    source_task_id: Optional[int] = None


class UpdateActionStatusInput(BaseModel):
    action_id: int
    status: Literal["open", "complete", "overdue"]


# ---------------------------------------------------------------------------
# LangChain tool definitions
# ---------------------------------------------------------------------------

fetch_last_journal_tool = Tool(
    name="fetch_last_journal",
    description=(
        "Read the most recent previous journal. Call this at the start of each "
        "run to understand what was noted and actioned before."
    ),
    func=lambda _: read_last_journal(),
)

fetch_outbox_tool = Tool(
    name="fetch_outbox_messages",
    description=(
        "Read all previously sent reminder messages. Check this before sending "
        "any new reminder to avoid over-chasing."
    ),
    func=lambda _: read_outbox(),
)

fetch_tasks_tool = Tool(
    name="fetch_tasks_from_database",
    description=(
        "Fetch all project tasks, including their phase, dependency, and "
        "blocking information."
    ),
    func=lambda _: TasksRepo().read(),
)

fetch_inbox_tool = Tool(
    name="fetch_inbox_messages",
    description="Read all messages received in the inbox from task owners.",
    func=lambda _: read_inbox(),
)

fetch_project_plan_tool = Tool(
    name="fetch_project_plan",
    description=(
        "Fetch the full project plan including objectives, phases, milestones, "
        "current RAG status, and forecast end date."
    ),
    func=lambda _: fetch_project_plan(),
)

fetch_raid_items_tool = Tool(
    name="fetch_raid_items",
    description=(
        "Fetch all RAID log entries — risks, assumptions, issues, and decisions. "
        "Review these to identify open risks, unresolved issues, and unvalidated "
        "assumptions that need attention today."
    ),
    func=lambda _: fetch_raid_items(),
)

fetch_actions_tool = Tool(
    name="fetch_actions",
    description=(
        "Fetch all action items. Check for overdue actions that need chasing, "
        "and open actions whose due date is today."
    ),
    func=lambda _: fetch_actions(),
)

update_task_status_tool = StructuredTool(
    name="update_task_status",
    description=(
        "Update the status of a task. Use when an inbox message confirms "
        "completion or reports a blocker. "
        "Valid statuses: not_started, in_progress, complete, blocked."
    ),
    func=update_task_status,
    args_schema=UpdateTaskStatusInput,
)

update_task_blocking_tool = StructuredTool(
    name="update_task_blocking",
    description=(
        "Update the blocked_reason or depends_on list for a task. Use when a "
        "task is blocked and you need to record why, or when a dependency "
        "has been resolved and you want to clear the blocked_reason."
    ),
    func=update_task_blocking,
    args_schema=UpdateTaskBlockingInput,
)

communications_tool = StructuredTool(
    name="send_message_to_task_owner",
    description="Send a reminder or chaser message to a task or action owner.",
    func=send_message,
    args_schema=SendMessageInput,
)

write_journal_tool = StructuredTool(
    name="write_journal_entry",
    description=(
        "Append a titled entry to today's journal to document thinking, "
        "observations, or a summary of actions taken."
    ),
    func=write_journal_entry,
    args_schema=WriteJournalEntryInput,
)

update_project_health_tool = StructuredTool(
    name="update_project_health",
    description=(
        "Update the project RAG status, the reason narrative, and/or the "
        "forecast end date. Call this at the end of each run after assessing "
        "milestone and RAID health."
    ),
    func=update_project_health,
    args_schema=UpdateProjectHealthInput,
)

update_milestone_tool = StructuredTool(
    name="update_milestone",
    description=(
        "Update a milestone status (pending/achieved/missed), its forecast "
        "date, or its actual achieved date."
    ),
    func=update_milestone,
    args_schema=UpdateMilestoneInput,
)

add_raid_item_tool = StructuredTool(
    name="add_raid_item",
    description=(
        "Log a new risk, assumption, issue, or decision to the RAID log. "
        "Use when inbox messages or task reviews surface new concerns or "
        "decisions. Populate only the fields relevant to the type."
    ),
    func=add_raid_item,
    args_schema=AddRaidItemInput,
)

update_raid_item_tool = StructuredTool(
    name="update_raid_item",
    description=(
        "Update an existing RAID item — e.g. close a resolved issue, update "
        "a risk score, validate an assumption, or add a decision rationale. "
        "Only provide fields that need changing."
    ),
    func=update_raid_item,
    args_schema=UpdateRaidItemInput,
)

add_action_tool = StructuredTool(
    name="add_action",
    description=(
        "Create a new action item, typically arising from a RAID entry. "
        "Assign it to an owner with a due date."
    ),
    func=add_action,
    args_schema=AddActionInput,
)

update_action_status_tool = StructuredTool(
    name="update_action_status",
    description=(
        "Update an action status to open, complete, or overdue. "
        "Mark overdue when an action is past its due date and still open."
    ),
    func=update_action_status,
    args_schema=UpdateActionStatusInput,
)

tools = [
    fetch_last_journal_tool,
    fetch_outbox_tool,
    fetch_inbox_tool,
    fetch_tasks_tool,
    fetch_project_plan_tool,
    fetch_raid_items_tool,
    fetch_actions_tool,
    update_task_status_tool,
    update_task_blocking_tool,
    update_project_health_tool,
    update_milestone_tool,
    add_raid_item_tool,
    update_raid_item_tool,
    add_action_tool,
    update_action_status_tool,
    write_journal_tool,
    communications_tool,
]
