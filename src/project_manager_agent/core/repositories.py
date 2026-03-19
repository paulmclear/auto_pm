import json
import datetime as dt
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from project_manager_agent.core.date_utils import REFERENCE_DATE
from project_manager_agent.core.models import (
    Task,
    TaskStatus,
    ActionStatus,
    JsonSerialiser,
)


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------


class TasksRepo:
    """Reads and writes tasks to data/tasks.json."""

    PATH = Path("data/tasks.json")

    def initialise(self) -> None:
        """Seed with sample tasks if the file does not already exist."""
        if self.PATH.exists():
            return
        initial = [
            Task(
                1,
                "Write business requirements",
                "Mary",
                "mary@test.com",
                dt.date(2026, 3, 18),
                phase_id=1,
            ),
            Task(
                2,
                "Review business requirements",
                "Bob",
                "bob@test.com",
                dt.date(2026, 3, 25),
                phase_id=1,
                depends_on=[1],
            ),
            Task(
                3,
                "Approve business requirements",
                "Bob",
                "bob@test.com",
                dt.date(2026, 3, 26),
                phase_id=1,
                depends_on=[2],
            ),
            Task(
                4,
                "Create IT plan",
                "Chris",
                "chris@test.com",
                dt.date(2026, 4, 3),
                phase_id=2,
                depends_on=[1],
            ),
        ]
        self._write(initial)

    def read(self) -> list[Task]:
        """Load all tasks, deserialising dates and back-filling new fields."""
        with open(self.PATH, "r", encoding="utf-8") as f:
            rows = json.load(f)
        tasks = []
        for row in rows:
            row["due_date"] = dt.date.fromisoformat(row["due_date"])
            row.setdefault("status", "not_started")
            row.setdefault("phase_id", None)
            row.setdefault("depends_on", [])
            row.setdefault("blocked_reason", None)
            row.setdefault("external_dependency", None)
            tasks.append(Task(**row))
        return tasks

    def update_status(self, task_id: int, status: TaskStatus) -> None:
        tasks = self.read()
        for task in tasks:
            if task.task_id == task_id:
                task.status = status
                self._write(tasks)
                return
        raise ValueError(f"Task {task_id} not found")

    def update_blocking(
        self, task_id: int, blocked_reason: Optional[str], depends_on: Optional[list]
    ) -> None:
        tasks = self.read()
        for task in tasks:
            if task.task_id == task_id:
                if blocked_reason is not None:
                    task.blocked_reason = blocked_reason
                if depends_on is not None:
                    task.depends_on = depends_on
                self._write(tasks)
                return
        raise ValueError(f"Task {task_id} not found")

    def _write(self, tasks: list[Task]) -> None:
        with open(self.PATH, "w", encoding="utf-8") as f:
            json.dump([asdict(t) for t in tasks], f, cls=JsonSerialiser, indent=4)


class ProjectRepo:
    """Reads and writes the project plan (including phases and milestones)."""

    PATH = Path("data/project.json")

    def initialise(self) -> None:
        """Seed with a sample project if the file does not already exist."""
        if self.PATH.exists():
            return
        project = {
            "name": "Business Systems Modernisation",
            "description": (
                "Modernise core business systems by capturing requirements, "
                "producing an IT plan, and delivering a phased implementation."
            ),
            "objectives": [
                "Produce agreed business requirements signed off by all stakeholders.",
                "Deliver a costed, phased IT plan approved by the sponsor.",
                "Implement Phase 1 of the new system by end of April 2026.",
            ],
            "sponsor": "Alice",
            "project_manager": "Project Manager Agent",
            "planned_start": "2026-03-17",
            "planned_end": "2026-04-30",
            "actual_start": "2026-03-17",
            "forecast_end": "2026-04-30",
            "rag_status": "green",
            "rag_reason": "Project is on track. Requirements phase underway.",
            "phases": [
                {
                    "phase_id": 1,
                    "name": "Requirements",
                    "description": "Capture, review, and approve business requirements.",
                    "planned_start": "2026-03-17",
                    "planned_end": "2026-03-26",
                },
                {
                    "phase_id": 2,
                    "name": "Planning & Design",
                    "description": "Produce the IT plan and high-level design.",
                    "planned_start": "2026-03-27",
                    "planned_end": "2026-04-10",
                },
                {
                    "phase_id": 3,
                    "name": "Delivery",
                    "description": "Implement and test the new system.",
                    "planned_start": "2026-04-13",
                    "planned_end": "2026-04-30",
                },
            ],
            "milestones": [
                {
                    "milestone_id": 1,
                    "name": "Requirements Approved",
                    "description": "Business requirements written, reviewed, and formally approved.",
                    "planned_date": "2026-03-26",
                    "forecast_date": "2026-03-26",
                    "actual_date": None,
                    "status": "pending",
                    "linked_task_ids": [1, 2, 3],
                },
                {
                    "milestone_id": 2,
                    "name": "IT Plan Approved",
                    "description": "Costed IT plan reviewed and approved by sponsor.",
                    "planned_date": "2026-04-10",
                    "forecast_date": "2026-04-10",
                    "actual_date": None,
                    "status": "pending",
                    "linked_task_ids": [4],
                },
            ],
        }
        with open(self.PATH, "w", encoding="utf-8") as f:
            json.dump(project, f, indent=4)

    def read(self) -> dict:
        """Return the raw project dict (phases and milestones included)."""
        with open(self.PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def update_health(
        self,
        rag_status: Optional[str],
        rag_reason: Optional[str],
        forecast_end: Optional[str],
    ) -> None:
        """Update RAG status, reason, and/or forecast end date."""
        data = self.read()
        if rag_status is not None:
            data["rag_status"] = rag_status
        if rag_reason is not None:
            data["rag_reason"] = rag_reason
        if forecast_end is not None:
            data["forecast_end"] = forecast_end
        self._write(data)

    def update_milestone(
        self,
        milestone_id: int,
        status: Optional[str],
        forecast_date: Optional[str],
        actual_date: Optional[str],
    ) -> None:
        """Update a milestone's status and/or dates."""
        data = self.read()
        for m in data.get("milestones", []):
            if m["milestone_id"] == milestone_id:
                if status is not None:
                    m["status"] = status
                if forecast_date is not None:
                    m["forecast_date"] = forecast_date
                if actual_date is not None:
                    m["actual_date"] = actual_date
                self._write(data)
                return
        raise ValueError(f"Milestone {milestone_id} not found")

    def _write(self, data: dict) -> None:
        with open(self.PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)


class RaidRepo:
    """Reads and writes the RAID log to data/raid.json."""

    PATH = Path("data/raid.json")

    def initialise(self) -> None:
        """Seed with sample RAID items if the file does not already exist."""
        if self.PATH.exists():
            return
        initial = [
            {
                "raid_id": 1,
                "type": "risk",
                "title": "Stakeholder unavailability during review",
                "description": (
                    "Bob may be unavailable for the requirements review due to "
                    "competing commitments, which could delay approval."
                ),
                "owner": "Bob",
                "raised_date": "2026-03-17",
                "status": "open",
                "linked_task_ids": [2, 3],
                "probability": "medium",
                "impact": "high",
                "mitigation": "Schedule review meeting early and agree a deputy approver.",
                "review_date": "2026-03-21",
            },
            {
                "raid_id": 2,
                "type": "assumption",
                "title": "Requirements will be stable once written",
                "description": (
                    "We are assuming that once Mary has written the requirements, "
                    "no major changes will be requested during review."
                ),
                "owner": "Mary",
                "raised_date": "2026-03-17",
                "status": "open",
                "linked_task_ids": [1, 2],
                "validation_method": "Confirm with Bob after review that no major rework is needed.",
                "validation_date": "2026-03-25",
                "validated_by": None,
            },
            {
                "raid_id": 3,
                "type": "decision",
                "title": "Use agile delivery methodology for Phase 3",
                "description": (
                    "Agreed to use two-week sprints for the Delivery phase "
                    "rather than a waterfall approach."
                ),
                "owner": "Alice",
                "raised_date": "2026-03-17",
                "status": "closed",
                "linked_task_ids": [],
                "rationale": (
                    "Agile allows earlier feedback and reduces risk of building "
                    "the wrong thing. Team has prior experience with sprints."
                ),
                "decided_by": "Alice",
                "decision_date": "2026-03-17",
                "alternatives_considered": "Waterfall; rejected due to inflexibility.",
            },
        ]
        with open(self.PATH, "w", encoding="utf-8") as f:
            json.dump(initial, f, indent=4)

    def read(self) -> list[dict]:
        """Load all RAID items as raw dicts."""
        with open(self.PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def add(self, item: dict) -> int:
        """Append a new RAID item and return its assigned raid_id."""
        items = self.read()
        next_id = max((i["raid_id"] for i in items), default=0) + 1
        item["raid_id"] = next_id
        items.append(item)
        self._write(items)
        return next_id

    def update(self, raid_id: int, fields: dict) -> None:
        """Merge fields into the RAID item with the given raid_id."""
        items = self.read()
        for item in items:
            if item["raid_id"] == raid_id:
                item.update({k: v for k, v in fields.items() if v is not None})
                self._write(items)
                return
        raise ValueError(f"RAID item {raid_id} not found")

    def _write(self, items: list[dict]) -> None:
        with open(self.PATH, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=4)


class ActionsRepo:
    """Reads and writes action items to data/actions.json."""

    PATH = Path("data/actions.json")

    def initialise(self) -> None:
        """Seed with sample actions if the file does not already exist."""
        if self.PATH.exists():
            return
        initial = [
            {
                "action_id": 1,
                "description": (
                    "Schedule requirements review meeting with Bob for the week "
                    "of 2026-03-23 to ensure his availability."
                ),
                "owner_name": "Bob",
                "owner_email": "bob@test.com",
                "due_date": "2026-03-20",
                "status": "open",
                "source_raid_id": 1,
                "source_task_id": None,
            },
        ]
        with open(self.PATH, "w", encoding="utf-8") as f:
            json.dump(initial, f, indent=4)

    def read(self) -> list[dict]:
        """Load all actions as raw dicts."""
        with open(self.PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def add(self, action: dict) -> int:
        """Append a new action and return its assigned action_id."""
        actions = self.read()
        next_id = max((a["action_id"] for a in actions), default=0) + 1
        action["action_id"] = next_id
        actions.append(action)
        self._write(actions)
        return next_id

    def update_status(self, action_id: int, status: ActionStatus) -> None:
        actions = self.read()
        for action in actions:
            if action["action_id"] == action_id:
                action["status"] = status
                self._write(actions)
                return
        raise ValueError(f"Action {action_id} not found")

    def _write(self, actions: list[dict]) -> None:
        with open(self.PATH, "w", encoding="utf-8") as f:
            json.dump(actions, f, indent=4)


class Mailbox:
    """
    Manages the agent's inbox and outbox directories.

    Both use JSONL format (one JSON object per line), so messages accumulate
    across runs and can be processed or appended independently.
    """

    INBOX_PATH = Path("data/inbox")
    OUTBOX_PATH = Path("data/outbox")
    INBOX_FILE = INBOX_PATH / "messages.jsonl"
    OUTBOX_FILE = OUTBOX_PATH / "messages.jsonl"

    def initialise(self) -> None:
        self.INBOX_PATH.mkdir(parents=True, exist_ok=True)
        self.OUTBOX_PATH.mkdir(parents=True, exist_ok=True)

    def send(self, owner_name: str, owner_email: str, message: str) -> None:
        entry = {
            "timestamp": dt.datetime.now().isoformat(),
            "owner_name": owner_name,
            "owner_email": owner_email,
            "message": message,
        }
        with open(self.OUTBOX_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def read_inbox(self) -> list[dict]:
        if not self.INBOX_FILE.exists():
            return []
        with open(self.INBOX_FILE, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def read_outbox(self) -> list[dict]:
        if not self.OUTBOX_FILE.exists():
            return []
        with open(self.OUTBOX_FILE, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]


class Journal:
    """
    Maintains a daily markdown journal of the agent's thinking and actions.

    Each day gets its own file at data/journal/YYYY-MM-DD.md.
    """

    JOURNAL_PATH = Path("data/journal")

    def initialise(self) -> None:
        self.JOURNAL_PATH.mkdir(parents=True, exist_ok=True)

    @property
    def today_file(self) -> Path:
        return self.JOURNAL_PATH / f"{REFERENCE_DATE}.md"

    def read_last(self) -> Optional[str]:
        past = sorted(
            (f for f in self.JOURNAL_PATH.glob("*.md") if f.stem < str(REFERENCE_DATE)),
            reverse=True,
        )
        if not past:
            return None
        with open(past[0], "r", encoding="utf-8") as f:
            return f.read()

    def write(self, section: str, content: str) -> None:
        if not self.today_file.exists():
            with open(self.today_file, "w", encoding="utf-8") as f:
                f.write(f"# Project Manager Journal — {REFERENCE_DATE}\n\n")
        timestamp = dt.datetime.now().strftime("%H:%M:%S")
        with open(self.today_file, "a", encoding="utf-8") as f:
            f.write(f"## {section}\n*{timestamp}*\n\n{content}\n\n")
