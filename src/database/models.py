"""
SQLAlchemy database models for Project Orchestrator.
"""
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from typing import Optional

from sqlalchemy import String, Text, Integer, Boolean, DateTime, Enum as SQLEnum, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class ProjectStatus(str, Enum):
    """Project workflow status."""
    BRAINSTORMING = "BRAINSTORMING"
    VISION_REVIEW = "VISION_REVIEW"
    PLANNING = "PLANNING"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


class MessageRole(str, Enum):
    """Message role in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Project(Base):
    """A software project being managed."""
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        SQLEnum(ProjectStatus),
        default=ProjectStatus.BRAINSTORMING,
        nullable=False
    )

    # External integrations
    github_repo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    telegram_chat_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Vision document stored as JSONB
    vision_document: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    messages: Mapped[list["ConversationMessage"]] = relationship(
        "ConversationMessage",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    workflow_phases: Mapped[list["WorkflowPhase"]] = relationship(
        "WorkflowPhase",
        back_populates="project",
        cascade="all, delete-orphan"
    )


class ConversationMessage(Base):
    """A message in the conversation history."""
    __tablename__ = "conversation_messages"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    role: Mapped[MessageRole] = mapped_column(SQLEnum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="messages")


class WorkflowPhase(Base):
    """A phase in the development workflow."""
    __tablename__ = "workflow_phases"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False)

    # Status
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="workflow_phases")


class ApprovalGate(Base):
    """An approval gate requiring user decision."""
    __tablename__ = "approval_gates"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)

    gate_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "vision_review", "phase_complete"
    question: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Decision
    approved: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    user_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ScarCommandExecution(Base):
    """Records of SCAR command executions for activity feed."""
    __tablename__ = "scar_command_executions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)

    command: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # 'po', 'scar', 'claude'
    message: Mapped[str] = mapped_column(Text, nullable=False)
    phase: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Metadata for verbosity filtering
    verbosity_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1=low, 2=medium, 3=high
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
