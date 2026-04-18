from sqlalchemy import ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ParticipantSceneMemory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "participant_scene_memories"

    simulation_run_id: Mapped[str] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE")
    )
    scene_run_id: Mapped[str] = mapped_column(ForeignKey("scene_runs.id", ondelete="CASCADE"))
    participant_id: Mapped[str] = mapped_column(ForeignKey("guest_profiles.id", ondelete="CASCADE"))
    memory_type: Mapped[str] = mapped_column(default="scene_takeaway", nullable=False)
    target_participant_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[int] = mapped_column(default=50, nullable=False)
    event_tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
