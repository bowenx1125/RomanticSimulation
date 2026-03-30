from sqlalchemy import Boolean, ForeignKey, Integer, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ParticipantProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "guest_profiles"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(nullable=False)
    cast_role: Mapped[str] = mapped_column(nullable=False, default="main_cast")
    age: Mapped[int | None]
    city: Mapped[str | None]
    occupation: Mapped[str | None]
    background_summary: Mapped[str | None] = mapped_column(Text)
    personality_summary: Mapped[str | None] = mapped_column(Text)
    attachment_style: Mapped[str | None]
    appearance_tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    personality_tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_traits: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    disliked_traits: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    commitment_goal: Mapped[str | None]
    imported_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    editable_personality: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    soul_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    project = relationship("Project", back_populates="participants")


GuestProfile = ParticipantProfile
