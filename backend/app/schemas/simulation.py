from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.director import DirectorSceneResult
from app.schemas.project import ParticipantEditablePersonality


class SimulationCreateRequest(BaseModel):
    strategy_cards: list[str] = Field(default_factory=list)
    selected_participant_ids: list[str] = Field(default_factory=list)
    participant_personality_overrides: dict[str, ParticipantEditablePersonality] = Field(
        default_factory=dict
    )
    scene_pack_config: dict | None = None


class SceneRunSummary(BaseModel):
    id: str
    scene_code: str
    scene_index: int
    status: str
    retry_count: int
    summary: str | None = None
    error_message: str | None = None
    finished_at: datetime | None = None


class RelationshipStateView(BaseModel):
    source_participant_id: str
    source_name: str
    target_participant_id: str
    target_name: str
    status: str
    recent_trend: str
    metrics: dict
    notes: list[str]


class AuditLogView(BaseModel):
    log_type: str
    payload: dict
    created_at: datetime


class SimulationResponse(BaseModel):
    id: str
    project_id: str
    status: str
    current_scene_index: int
    current_scene_code: str | None = None
    latest_scene_summary: str | None = None
    latest_audit_snippet: str | None = None
    created_at: datetime


class SimulationDetailResponse(SimulationResponse):
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None
    strategy_cards: list[str]
    scenes: list[SceneRunSummary]
    director_output: DirectorSceneResult | None = None
    relationships: list[RelationshipStateView]
    latest_snapshot: dict | None = None
    recent_audit_logs: list[AuditLogView]
