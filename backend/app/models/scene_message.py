from sqlalchemy import ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SceneMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scene_messages"

    simulation_run_id: Mapped[str] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE")
    )
    scene_run_id: Mapped[str] = mapped_column(ForeignKey("scene_runs.id", ondelete="CASCADE"))
    turn_index: Mapped[int] = mapped_column(nullable=False)
    speaker_guest_id: Mapped[str] = mapped_column(ForeignKey("guest_profiles.id", ondelete="CASCADE"))
    speaker_name: Mapped[str] = mapped_column(nullable=False)
    message_role: Mapped[str] = mapped_column(nullable=False)
    utterance: Mapped[str] = mapped_column(nullable=False)
    behavior_summary: Mapped[str | None]
    intent_tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    target_guest_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    visible_context_summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    raw_output: Mapped[dict | None] = mapped_column(JSON)

    simulation = relationship("SimulationRun", back_populates="scene_messages")
    scene = relationship("SceneRun", back_populates="messages")

