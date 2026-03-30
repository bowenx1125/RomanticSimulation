from datetime import datetime

from pydantic import BaseModel, Field


class ParticipantEditablePersonality(BaseModel):
    extroversion: int = 50
    initiative: int = 50
    emotional_openness: int = 50
    attachment_style: str = "secure"
    conflict_style: str = "avoid_then_explode"
    self_esteem_stability: int = 50
    pace_preference: str = "gradual_but_clear"
    commitment_goal: str = "serious_relationship"
    preferred_traits: list[str] = Field(default_factory=list)
    disliked_traits: list[str] = Field(default_factory=list)
    boundaries: dict = Field(
        default_factory=lambda: {
            "hard_boundaries": [],
            "soft_boundaries": [],
        }
    )
    expression_style: dict = Field(
        default_factory=lambda: {
            "communication_style": "balanced",
            "reassurance_need": "medium",
        }
    )


class ParticipantImportPayload(BaseModel):
    name: str
    cast_role: str = "main_cast"
    age: int | None = None
    city: str | None = None
    occupation: str | None = None
    background_summary: str | None = None
    personality_summary: str | None = None
    attachment_style: str | None = None
    appearance_tags: list[str] = Field(default_factory=list)
    personality_tags: list[str] = Field(default_factory=list)
    preferred_traits: list[str] = Field(default_factory=list)
    disliked_traits: list[str] = Field(default_factory=list)
    commitment_goal: str | None = "serious_relationship"
    editable_personality: ParticipantEditablePersonality | None = None
    is_active: bool = True
    display_order: int | None = None


class ProjectCreateRequest(BaseModel):
    name: str
    description: str | None = None


class ParticipantImportRequest(BaseModel):
    participants: list[ParticipantImportPayload]


class ParticipantSummary(BaseModel):
    id: str
    name: str
    cast_role: str
    city: str | None = None
    occupation: str | None = None
    attachment_style: str | None = None
    display_order: int
    editable_personality: dict = Field(default_factory=dict)


class ParticipantPersonalityResponse(BaseModel):
    participant_id: str
    name: str
    cast_role: str
    editable_personality: dict = Field(default_factory=dict)
    changed_fields: list[str] = Field(default_factory=list)


class ParticipantPersonalityPatchRequest(BaseModel):
    editable_personality: ParticipantEditablePersonality


class PersonalityPresetSummary(BaseModel):
    slug: str
    name: str
    description: str | None = None
    values: dict = Field(default_factory=dict)


class PersonalityPresetApplyRequest(BaseModel):
    preset_slug: str
    participant_ids: list[str] = Field(default_factory=list)


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    participant_count: int
    created_at: datetime


class ProjectDetailResponse(ProjectResponse):
    participants: list[ParticipantSummary]


class ProjectParticipantsResponse(BaseModel):
    project_id: str
    project_name: str
    participants: list[ParticipantSummary]
    presets: list[PersonalityPresetSummary] = Field(default_factory=list)
