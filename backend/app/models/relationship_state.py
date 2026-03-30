from sqlalchemy import ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RelationshipState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "relationship_states"
    __table_args__ = (
        UniqueConstraint(
            "simulation_run_id",
            "source_participant_id",
            "target_participant_id",
            "relationship_kind",
        ),
    )

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    simulation_run_id: Mapped[str] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE")
    )
    source_participant_id: Mapped[str] = mapped_column(
        ForeignKey("guest_profiles.id", ondelete="CASCADE")
    )
    target_participant_id: Mapped[str] = mapped_column(
        ForeignKey("guest_profiles.id", ondelete="CASCADE")
    )
    relationship_kind: Mapped[str] = mapped_column(default="social_interest", nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(default="observing", nullable=False)
    recent_trend: Mapped[str] = mapped_column(default="observing", nullable=False)
    notes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    last_event_tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    updated_by_scene_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("scene_runs.id", ondelete="SET NULL")
    )

    simulation = relationship("SimulationRun", back_populates="relationships")
