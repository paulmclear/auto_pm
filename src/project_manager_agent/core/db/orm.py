"""SQLAlchemy 2.0 declarative ORM models for the project-manager database."""

import datetime as dt

from sqlalchemy import (
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Projects (single-row table)
# ---------------------------------------------------------------------------


class ProjectRow(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    objectives: Mapped[str] = mapped_column(Text, nullable=False)  # JSON list[str]
    sponsor: Mapped[str] = mapped_column(String, nullable=False)
    project_manager: Mapped[str] = mapped_column(String, nullable=False)
    planned_start: Mapped[dt.date] = mapped_column(Date, nullable=False)
    planned_end: Mapped[dt.date] = mapped_column(Date, nullable=False)
    actual_start: Mapped[dt.date] = mapped_column(Date, nullable=False)
    forecast_end: Mapped[dt.date] = mapped_column(Date, nullable=False)
    rag_status: Mapped[str] = mapped_column(String, nullable=False)  # green|amber|red
    rag_reason: Mapped[str] = mapped_column(Text, nullable=False)

    phases: Mapped[list["PhaseRow"]] = relationship(back_populates="project")
    milestones: Mapped[list["MilestoneRow"]] = relationship(back_populates="project")


# ---------------------------------------------------------------------------
# Phases (FK → projects)
# ---------------------------------------------------------------------------


class PhaseRow(Base):
    __tablename__ = "phases"

    phase_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    planned_start: Mapped[dt.date] = mapped_column(Date, nullable=False)
    planned_end: Mapped[dt.date] = mapped_column(Date, nullable=False)

    project: Mapped["ProjectRow"] = relationship(back_populates="phases")


# ---------------------------------------------------------------------------
# Milestones (FK → projects)
# ---------------------------------------------------------------------------


class MilestoneRow(Base):
    __tablename__ = "milestones"

    milestone_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    planned_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    forecast_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    actual_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String, nullable=False
    )  # pending|achieved|missed
    linked_task_ids: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]"
    )  # JSON list[int]

    project: Mapped["ProjectRow"] = relationship(back_populates="milestones")


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


class TaskRow(Base):
    __tablename__ = "tasks"

    task_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner_name: Mapped[str] = mapped_column(String, nullable=False)
    owner_email: Mapped[str] = mapped_column(String, nullable=False)
    due_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="not_started")
    priority: Mapped[str] = mapped_column(
        String, nullable=False, default="medium"
    )  # high|medium|low
    phase_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    depends_on: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]"
    )  # JSON list[int]
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_dependency: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# RAID items (flat with type-specific nullable columns)
# ---------------------------------------------------------------------------


class RaidItemRow(Base):
    __tablename__ = "raid_items"

    raid_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # risk|assumption|issue|decision
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String, nullable=False)
    raised_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String, nullable=False
    )  # open|closed|accepted|superseded
    linked_task_ids: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]"
    )  # JSON list[int]

    # Risk-specific
    probability: Mapped[str | None] = mapped_column(String, nullable=True)
    impact: Mapped[str | None] = mapped_column(String, nullable=True)
    mitigation: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)

    # Assumption-specific
    validation_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    validated_by: Mapped[str | None] = mapped_column(String, nullable=True)

    # Issue-specific
    severity: Mapped[str | None] = mapped_column(String, nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)

    # Decision-specific
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String, nullable=True)
    decision_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    alternatives_considered: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


class ActionRow(Base):
    __tablename__ = "actions"

    action_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner_name: Mapped[str] = mapped_column(String, nullable=False)
    owner_email: Mapped[str] = mapped_column(String, nullable=False)
    due_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")
    source_raid_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_task_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


# ---------------------------------------------------------------------------
# Messages (replaces inbox + outbox JSONL)
# ---------------------------------------------------------------------------


class MessageRow(Base):
    __tablename__ = "messages"

    message_id: Mapped[str] = mapped_column(String, primary_key=True)
    direction: Mapped[str] = mapped_column(String, nullable=False)  # inbound|outbound
    timestamp: Mapped[str] = mapped_column(String, nullable=False)
    owner_name: Mapped[str] = mapped_column(String, nullable=False)
    owner_email: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sender_name: Mapped[str] = mapped_column(String, nullable=False)
    sender_email: Mapped[str] = mapped_column(String, nullable=False)
