from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SimulationRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "simulation_runs"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(default="queued", nullable=False)
    current_scene_index: Mapped[int] = mapped_column(default=1, nullable=False)
    current_scene_code: Mapped[str | None]
    latest_scene_summary: Mapped[str | None] = mapped_column(Text)
    latest_audit_snippet: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    strategy_cards: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project = relationship("Project", back_populates="simulations")
    scenes = relationship("SceneRun", back_populates="simulation", cascade="all, delete-orphan")
    snapshots = relationship(
        "StateSnapshot", back_populates="simulation", cascade="all, delete-orphan"
    )
    audit_logs = relationship("AuditLog", back_populates="simulation", cascade="all, delete-orphan")
    relationships = relationship(
        "RelationshipState", back_populates="simulation", cascade="all, delete-orphan"
    )
    scene_messages = relationship(
        "SceneMessage", back_populates="simulation", cascade="all, delete-orphan"
    )
    agent_turns = relationship(
        "AgentTurn", back_populates="simulation", cascade="all, delete-orphan"
    )
    scene_artifacts = relationship(
        "SceneArtifact", back_populates="simulation", cascade="all, delete-orphan"
    )
