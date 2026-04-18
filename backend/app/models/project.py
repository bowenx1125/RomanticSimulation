from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    participants = relationship(
        "ParticipantProfile",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    simulations = relationship(
        "SimulationRun", back_populates="project", cascade="all, delete-orphan"
    )
