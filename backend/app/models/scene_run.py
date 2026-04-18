from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SceneRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scene_runs"
    __table_args__ = (UniqueConstraint("simulation_run_id", "scene_code"),)

    simulation_run_id: Mapped[str] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE")
    )
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    scene_index: Mapped[int] = mapped_column(nullable=False)
    scene_code: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(default="queued", nullable=False)
    claim_token: Mapped[str | None]
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    director_output: Mapped[dict | None] = mapped_column(JSON)
    summary: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)

    simulation = relationship("SimulationRun", back_populates="scenes")
    messages = relationship("SceneMessage", back_populates="scene", cascade="all, delete-orphan")
    agent_turns = relationship("AgentTurn", back_populates="scene", cascade="all, delete-orphan")
    artifacts = relationship("SceneArtifact", back_populates="scene", cascade="all, delete-orphan")
