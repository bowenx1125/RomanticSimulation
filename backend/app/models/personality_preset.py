from sqlalchemy import JSON, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PersonalityPreset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "personality_presets"
    __table_args__ = (UniqueConstraint("slug"),)

    slug: Mapped[str] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    values: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
