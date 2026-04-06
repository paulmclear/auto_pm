"""
Project Manager — Tool definitions
===================================
Tool functions, Pydantic input schemas, and LangChain tool instances used by
the project manager agent.
"""

import datetime as dt
import json
from dataclasses import asdict
from typing import Literal, Optional

from langchain_core.tools import Tool, StructuredTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from project_manager_agent.core.config import (
    ADVANCE_WARNING_DAYS,
    ESCALATION_THRESHOLD_DAYS,
)
from project_manager_agent.core.date_utils import REFERENCE_DATE
from project_manager_agent.core.models import Action, RaidItem
from project_manager_agent.core.services import ProjectService

# ---------------------------------------------------------------------------
# Project scoping — set once at startup, read by every tool function
# ---------------------------------------------------------------------------

_PROJECT_ID: Optional[int] = None


def set_project_id(project_id: Optional[int]) -> None:
    """Set the project_id that all tool functions will use."""
    global _PROJECT_ID
    _PROJECT_ID = project_id


def _service() -> ProjectService:
    """Create a ProjectService scoped to the active project."""
    return ProjectService(project_id=_PROJECT_ID)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize(obj: object) -> dict:
    """Convert a dataclass to a JSON-safe dict (dt.date → ISO string)."""
    d = asdict(obj)  # type: ignore[arg-type]
    for k, v in d.items():
        if isinstance(v, dt.date):
            d[k] = v.isoformat()
    return d


def _parse_date(s: Optional[str]) -> Optional[dt.date]:
    """Parse an ISO date string, returning None if input is None."""
    return dt.date.fromisoformat(s) if s else None


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------


def fetch_tasks() -> list[dict]:
    svc = _service()
    try:
        return [_serialize(t) for t in svc.read_tasks()]
    finally:
        svc.close()


def fetch_overdue_tasks() -> list[dict]:
    """Return tasks whose due_date is before REFERENCE_DATE and status is not complete."""
    svc = _service()
    try:
        tasks = svc.read_tasks()
        overdue = [
            t for t in tasks if t.due_date < REFERENCE_DATE and t.status != "complete"
        ]
        return [_serialize(t) for t in overdue]
    finally:
        svc.close()


def fetch_escalation_candidates(
    overdue_threshold_days: int = ESCALATION_THRESHOLD_DAYS,
) -> list[dict]:
    """Return tasks overdue by at least *overdue_threshold_days* that may need
    escalation to the project sponsor.

    Each result includes:
    - All standard task fields
    - ``days_overdue``: how many days past due
    - ``previously_escalated``: whether an escalation message was already sent
      to the sponsor for this task
    - ``last_escalation_date``: ISO date of the most recent escalation (if any)
    - ``sponsor``: the project sponsor name (escalation recipient)
    """
    svc = _service()
    try:
        tasks = svc.read_tasks()
        project = svc.read_project()
        outbox = svc.read_outbox()

        # Build lookup: task_id → most recent escalation timestamp
        escalation_dates: dict[int, str] = {}
        for msg in outbox:
            if msg.task_id and "ESCALATION" in msg.message.upper():
                existing = escalation_dates.get(msg.task_id, "")
                if msg.timestamp > existing:
                    escalation_dates[msg.task_id] = msg.timestamp

        results = []
        for t in tasks:
            if t.status == "complete":
                continue
            days_overdue = (REFERENCE_DATE - t.due_date).days
            if days_overdue < overdue_threshold_days:
                continue
            d = _serialize(t)
            d["days_overdue"] = days_overdue
            d["previously_escalated"] = t.task_id in escalation_dates
            d["last_escalation_date"] = escalation_dates.get(t.task_id)
            d["sponsor"] = project.sponsor
            results.append(d)
        return results
    finally:
        svc.close()


def fetch_upcoming_due_tasks(lead_days: int = ADVANCE_WARNING_DAYS) -> list[dict]:
    """Return incomplete tasks whose due_date is within the next *lead_days* days.

    Only includes tasks that are NOT already overdue (due_date >= REFERENCE_DATE)
    and NOT complete.  Each result includes a 'days_until_due' field.
    """
    svc = _service()
    try:
        tasks = svc.read_tasks()
        horizon = REFERENCE_DATE + dt.timedelta(days=lead_days)
        upcoming = []
        for t in tasks:
            if t.status == "complete":
                continue
            if REFERENCE_DATE <= t.due_date <= horizon:
                d = _serialize(t)
                d["days_until_due"] = (t.due_date - REFERENCE_DATE).days
                upcoming.append(d)
        return upcoming
    finally:
        svc.close()


def fetch_dependency_blocked_tasks() -> list[dict]:
    """Return tasks whose depends_on list contains at least one incomplete upstream task.

    Each returned dict includes the task fields plus a 'blocking_tasks' list
    showing which upstream task_ids are not yet complete.
    """
    svc = _service()
    try:
        tasks = svc.read_tasks()
        status_by_id = {t.task_id: t.status for t in tasks}
        results = []
        for t in tasks:
            if t.status == "complete" or not t.depends_on:
                continue
            incomplete_deps = [
                dep_id
                for dep_id in t.depends_on
                if status_by_id.get(dep_id) != "complete"
            ]
            if incomplete_deps:
                d = _serialize(t)
                d["blocking_tasks"] = incomplete_deps
                results.append(d)
        return results
    finally:
        svc.close()


def read_last_journal() -> str:
    svc = _service()
    try:
        content = svc.read_last_journal()
        return content if content is not None else "No previous journal found."
    finally:
        svc.close()


def read_outbox() -> list[dict]:
    svc = _service()
    try:
        return [_serialize(m) for m in svc.read_outbox()]
    finally:
        svc.close()


def read_inbox() -> list[dict]:
    svc = _service()
    try:
        return [_serialize(m) for m in svc.read_inbox()]
    finally:
        svc.close()


_INTENT_PARSE_PROMPT = """\
You are a project management assistant. Analyse each inbox message and classify \
its intent. Return a JSON array with one object per message.

Each object MUST have these fields:
- "message_id": the original message_id (string)
- "intent": one of "completion_confirmation", "blocker_report", \
"date_change_request", "resource_request", "question", "general_update"
- "confidence": "high" or "low"
- "referenced_task_id": integer task_id if the message clearly references a \
specific task, otherwise null
- "extracted_details": a short string summarising the actionable content \
(e.g. the blocker reason, the requested new date, the question asked). \
Empty string if nothing specific.
- "suggested_action": one of "update_task_complete", "update_task_blocked", \
"update_task_due_date", "add_raid_item", "reply_needed", "note_only", "none"

Rules:
- If someone says a task is done/finished/complete → "completion_confirmation"
- If someone reports being stuck/blocked/waiting → "blocker_report"
- If someone asks to push back/extend/change a deadline → "date_change_request"
- If someone asks for help/resources/more people → "resource_request"
- If someone asks a question → "question"
- Otherwise → "general_update"

Messages:
{messages_json}

Respond ONLY with the JSON array, no markdown fences or explanation."""


def parse_inbox_messages() -> list[dict]:
    """Read inbox messages and classify each one by intent using LLM parsing.

    Returns the original message fields enriched with:
    - ``intent``: the classified intent type
    - ``confidence``: "high" or "low"
    - ``referenced_task_id``: task_id if identifiable, else null
    - ``extracted_details``: actionable summary
    - ``suggested_action``: recommended next step
    """
    svc = _service()
    try:
        messages = svc.read_inbox()
    finally:
        svc.close()

    if not messages:
        return []

    raw = [_serialize(m) for m in messages]

    # Call LLM to parse intents
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = _INTENT_PARSE_PROMPT.format(messages_json=json.dumps(raw, indent=2))
    response = llm.invoke(prompt)

    try:
        parsed = json.loads(response.content)
    except (json.JSONDecodeError, TypeError):
        # Fallback: return messages with unknown intent
        for m in raw:
            m["intent"] = "general_update"
            m["confidence"] = "low"
            m["referenced_task_id"] = None
            m["extracted_details"] = ""
            m["suggested_action"] = "none"
        return raw

    # Merge parsed intents back onto original message dicts
    intent_by_id = {p["message_id"]: p for p in parsed}
    results = []
    for m in raw:
        intent_data = intent_by_id.get(m["message_id"], {})
        m["intent"] = intent_data.get("intent", "general_update")
        m["confidence"] = intent_data.get("confidence", "low")
        m["referenced_task_id"] = intent_data.get("referenced_task_id")
        m["extracted_details"] = intent_data.get("extracted_details", "")
        m["suggested_action"] = intent_data.get("suggested_action", "none")
        results.append(m)
    return results


def send_message(
    owner_name: str, owner_email: str, message: str, task_id: Optional[int] = None
) -> str:
    svc = _service()
    try:
        svc.send_message(owner_name, owner_email, message, task_id=task_id)
        tag = f" [task {task_id}]" if task_id else ""
        print(f"Message queued for {owner_name} ({owner_email}){tag}: {message}")
        return f"Message queued for {owner_name}{tag}"
    finally:
        svc.close()


def update_task_status(task_id: int, status: str) -> str:
    svc = _service()
    try:
        svc.update_task_status(task_id, status)  # type: ignore[arg-type]
        print(f"Task {task_id} status updated to '{status}'")
        return f"Task {task_id} status updated to '{status}'"
    except ValueError as e:
        return str(e)
    finally:
        svc.close()


def update_task_blocking(
    task_id: int, blocked_reason: Optional[str], depends_on: Optional[list]
) -> str:
    svc = _service()
    try:
        svc.update_task_blocking(task_id, blocked_reason, depends_on)
        return f"Task {task_id} blocking info updated."
    except ValueError as e:
        return str(e)
    finally:
        svc.close()


def write_journal_entry(section: str, content: str) -> str:
    svc = _service()
    try:
        svc.write_journal(section, content)
        return f"Journal entry written: {section}"
    finally:
        svc.close()


def fetch_project_plan() -> dict:
    svc = _service()
    try:
        project = svc.read_project()
        return _serialize(project)
    finally:
        svc.close()


def update_project_health(
    rag_status: Optional[str], rag_reason: Optional[str], forecast_end: Optional[str]
) -> str:
    svc = _service()
    try:
        svc.update_health(
            rag_status=rag_status,  # type: ignore[arg-type]
            rag_reason=rag_reason,
            forecast_end=_parse_date(forecast_end),
        )
        parts = []
        if rag_status:
            parts.append(f"RAG → {rag_status}")
        if forecast_end:
            parts.append(f"forecast end → {forecast_end}")
        return "Project health updated: " + ", ".join(parts) if parts else "No changes."
    finally:
        svc.close()


def update_milestone(
    milestone_id: int,
    status: Optional[str],
    forecast_date: Optional[str],
    actual_date: Optional[str],
) -> str:
    svc = _service()
    try:
        svc.update_milestone(
            milestone_id,
            status=status,  # type: ignore[arg-type]
            forecast_date=_parse_date(forecast_date),
            actual_date=_parse_date(actual_date),
        )
        return f"Milestone {milestone_id} updated."
    except ValueError as e:
        return str(e)
    finally:
        svc.close()


def fetch_raid_items() -> list[dict]:
    svc = _service()
    try:
        return [_serialize(r) for r in svc.read_raid()]
    finally:
        svc.close()


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
    item = RaidItem(
        raid_id=0,
        type=type,  # type: ignore[arg-type]
        title=title,
        description=description,
        owner=owner,
        raised_date=REFERENCE_DATE,
        status="open",
        linked_task_ids=linked_task_ids,
        probability=probability,  # type: ignore[arg-type]
        impact=impact,  # type: ignore[arg-type]
        mitigation=mitigation,
        review_date=review_date,
        validation_method=validation_method,
        validation_date=validation_date,
        validated_by=None,
        severity=severity,  # type: ignore[arg-type]
        resolution=None,
        resolved_date=None,
        rationale=rationale,
        decided_by=decided_by,
        decision_date=decision_date,
        alternatives_considered=alternatives_considered,
    )
    svc = _service()
    try:
        raid_id = svc.add_raid(item)
        print(f"RAID item {raid_id} added: [{type}] {title}")
        return f"RAID item {raid_id} added."
    finally:
        svc.close()


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
    svc = _service()
    try:
        svc.update_raid(raid_id, fields)
        print(f"RAID item {raid_id} updated.")
        return f"RAID item {raid_id} updated."
    except ValueError as e:
        return str(e)
    finally:
        svc.close()


def fetch_actions() -> list[dict]:
    svc = _service()
    try:
        return [_serialize(a) for a in svc.read_actions()]
    finally:
        svc.close()


def add_action(
    description: str,
    owner_name: str,
    owner_email: str,
    due_date: str,
    source_raid_id: Optional[int],
    source_task_id: Optional[int],
) -> str:
    action = Action(
        action_id=0,
        description=description,
        owner_name=owner_name,
        owner_email=owner_email,
        due_date=dt.date.fromisoformat(due_date),
        status="open",
        source_raid_id=source_raid_id,
        source_task_id=source_task_id,
    )
    svc = _service()
    try:
        action_id = svc.add_action(action)
        print(f"Action {action_id} added: {description}")
        return f"Action {action_id} added."
    finally:
        svc.close()


def update_action_status(action_id: int, status: str) -> str:
    svc = _service()
    try:
        svc.update_action_status(action_id, status)  # type: ignore[arg-type]
        print(f"Action {action_id} status updated to '{status}'")
        return f"Action {action_id} status updated to '{status}'"
    except ValueError as e:
        return str(e)
    finally:
        svc.close()


# ---------------------------------------------------------------------------
# Pydantic input schemas
# ---------------------------------------------------------------------------


class FetchEscalationCandidatesInput(BaseModel):
    overdue_threshold_days: int = ESCALATION_THRESHOLD_DAYS


class FetchUpcomingDueTasksInput(BaseModel):
    lead_days: int = ADVANCE_WARNING_DAYS


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
    task_id: Optional[int] = None


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
    func=lambda _: fetch_tasks(),
)

fetch_overdue_tasks_tool = Tool(
    name="fetch_overdue_tasks",
    description=(
        "Fetch tasks that are past their due date and not yet complete. "
        "These are overdue and require urgent attention — use this to "
        "identify tasks needing escalated reminders."
    ),
    func=lambda _: fetch_overdue_tasks(),
)

fetch_dependency_blocked_tasks_tool = Tool(
    name="fetch_dependency_blocked_tasks",
    description=(
        "Fetch tasks that are blocked because one or more upstream dependencies "
        "(depends_on) are not yet complete. Each result includes a 'blocking_tasks' "
        "list of the incomplete upstream task_ids. Do NOT send reminders for these "
        "tasks — they cannot proceed until their dependencies finish."
    ),
    func=lambda _: fetch_dependency_blocked_tasks(),
)

fetch_upcoming_due_tasks_tool = StructuredTool(
    name="fetch_upcoming_due_tasks",
    description=(
        "Fetch incomplete tasks whose due date falls within the next N days "
        "(default 2). Use this to send advance warning reminders BEFORE a task "
        "becomes due. Each result includes a 'days_until_due' field. Does not "
        "include tasks that are already overdue or complete."
    ),
    func=fetch_upcoming_due_tasks,
    args_schema=FetchUpcomingDueTasksInput,
)

fetch_escalation_candidates_tool = StructuredTool(
    name="fetch_escalation_candidates",
    description=(
        "Fetch tasks that are overdue by N or more days (default 3) and may need "
        "escalation to the project sponsor. Each result includes 'days_overdue', "
        "'previously_escalated' (bool), 'last_escalation_date', and 'sponsor'. "
        "Use this to decide which tasks warrant an escalation message to the "
        "project sponsor or manager."
    ),
    func=fetch_escalation_candidates,
    args_schema=FetchEscalationCandidatesInput,
)

fetch_inbox_tool = Tool(
    name="fetch_inbox_messages",
    description="Read all messages received in the inbox from task owners.",
    func=lambda _: read_inbox(),
)

parse_inbox_tool = Tool(
    name="parse_inbox_messages",
    description=(
        "Read inbox messages and classify each one by structured intent using "
        "LLM parsing. Returns each message enriched with: intent (completion_confirmation, "
        "blocker_report, date_change_request, resource_request, question, general_update), "
        "confidence (high/low), referenced_task_id, extracted_details, and "
        "suggested_action. Use this INSTEAD of fetch_inbox_messages for smarter "
        "inbox processing — it tells you exactly what action each message needs."
    ),
    func=lambda _: parse_inbox_messages(),
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
    description=(
        "Send a reminder or chaser message to a task or action owner. "
        "When sending a reminder about a specific task, include the task_id "
        "so chaser frequency can be tracked per-task rather than per-person."
    ),
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
    parse_inbox_tool,
    fetch_tasks_tool,
    fetch_overdue_tasks_tool,
    fetch_dependency_blocked_tasks_tool,
    fetch_upcoming_due_tasks_tool,
    fetch_escalation_candidates_tool,
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
