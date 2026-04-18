from sqlalchemy import ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StateSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "state_snapshots"

    simulation_run_id: Mapped[str] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE")
    )
    scene_run_id: Mapped[str] = mapped_column(ForeignKey("scene_runs.id", ondelete="CASCADE"))
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    simulation = relationship("SimulationRun", back_populates="snapshots")

