from pydantic import BaseModel, Field, field_validator


ALLOWED_METRICS = {
    "initial_attraction",
    "attraction",
    "trust",
    "comfort",
    "understood",
    "expectation",
    "disappointment",
    "conflict",
    "anxiety",
    "curiosity",
    "intimacy",
    "self_esteem",
    "expectation_gap",
    "competition_sense",
    "exclusivity_pressure",
    "commitment_alignment",
}


class MajorEvent(BaseModel):
    title: str
    description: str
    event_tags: list[str] = Field(default_factory=list)
    target_guest_ids: list[str] = Field(default_factory=list)


class GuestDirective(BaseModel):
    guest_id: str
    guest_name: str
    directive: str


class RelationshipDelta(BaseModel):
    guest_id: str
    guest_name: str
    event_tags: list[str] = Field(default_factory=list)
    changes: dict[str, int]
    reason: str

    @field_validator("changes")
    @classmethod
    def validate_changes(cls, value: dict[str, int]) -> dict[str, int]:
        invalid_keys = [key for key in value if key not in ALLOWED_METRICS]
        if invalid_keys:
            raise ValueError(f"Invalid metric keys: {', '.join(invalid_keys)}")
        invalid_values = [delta for delta in value.values() if delta < -18 or delta > 18]
        if invalid_values:
            raise ValueError("Every metric delta must stay within [-18, 18]")
        return value


class DirectorSceneResult(BaseModel):
    scene_id: str
    scene_summary: str
    director_summary: str
    major_events: list[MajorEvent] = Field(default_factory=list)
    guest_directives: list[GuestDirective] = Field(default_factory=list)
    relationship_deltas: list[RelationshipDelta] = Field(default_factory=list)
    next_tension: str


class DirectorExecutionResult(BaseModel):
    validated: DirectorSceneResult
    raw_output: dict | str
    input_summary: dict
