from sqlalchemy import ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AuditLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"

    simulation_run_id: Mapped[str] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE")
    )
    scene_run_id: Mapped[str] = mapped_column(ForeignKey("scene_runs.id", ondelete="CASCADE"))
    log_type: Mapped[str] = mapped_column(nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    simulation = relationship("SimulationRun", back_populates="audit_logs")
