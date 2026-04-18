from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AgentTurn(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_turns"
    __table_args__ = (UniqueConstraint("scene_run_id", "turn_index", "guest_id"),)

    simulation_run_id: Mapped[str] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE")
    )
    scene_run_id: Mapped[str] = mapped_column(ForeignKey("scene_runs.id", ondelete="CASCADE"))
    turn_index: Mapped[int] = mapped_column(nullable=False)
    guest_id: Mapped[str] = mapped_column(ForeignKey("guest_profiles.id", ondelete="CASCADE"))
    agent_name: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, default="completed")
    input_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    raw_output: Mapped[dict | None] = mapped_column(JSON)
    normalized_output: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    simulation = relationship("SimulationRun", back_populates="agent_turns")
    scene = relationship("SceneRun", back_populates="agent_turns")

