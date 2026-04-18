from sqlalchemy import ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SceneArtifact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scene_artifacts"
    __table_args__ = (UniqueConstraint("scene_run_id", "artifact_type"),)

    simulation_run_id: Mapped[str] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE")
    )
    scene_run_id: Mapped[str] = mapped_column(ForeignKey("scene_runs.id", ondelete="CASCADE"))
    artifact_type: Mapped[str] = mapped_column(nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    simulation = relationship("SimulationRun", back_populates="scene_artifacts")
    scene = relationship("SceneRun", back_populates="artifacts")

