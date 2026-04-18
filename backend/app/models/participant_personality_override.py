from sqlalchemy import ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ParticipantPersonalityOverride(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "participant_personality_overrides"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    simulation_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE")
    )
    participant_id: Mapped[str] = mapped_column(ForeignKey("guest_profiles.id", ondelete="CASCADE"))
    source_type: Mapped[str] = mapped_column(default="simulation_setup", nullable=False)
    preset_slug: Mapped[str | None]
    override_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    changed_fields: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
