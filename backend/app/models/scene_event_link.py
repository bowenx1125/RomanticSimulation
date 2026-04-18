from sqlalchemy import ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SceneEventLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scene_event_links"

    simulation_run_id: Mapped[str] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE")
    )
    scene_run_id: Mapped[str] = mapped_column(ForeignKey("scene_runs.id", ondelete="CASCADE"))
    source_participant_id: Mapped[str | None] = mapped_column(
        ForeignKey("guest_profiles.id", ondelete="SET NULL")
    )
    target_participant_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    event_tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
