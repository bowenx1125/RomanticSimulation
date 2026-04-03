from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.director import ALLOWED_METRICS


class PlanParticipant(BaseModel):
    participant_id: str
    name: str
    cast_role: str


class ParticipantDirective(BaseModel):
    participant_id: str
    directive: str


class SceneOrchestratorPlan(BaseModel):
    scene_id: str
    scene_goal: str
    scene_frame: str
    scene_level: str | None = None
    participants: list[PlanParticipant]
    min_turns: int
    max_turns: int
    planned_rounds: int
    active_tension: str
    stop_condition: str
    scheduler_notes: list[str] = Field(default_factory=list)
    phase_outline: list[str] = Field(default_factory=list)
    participant_directives: list[ParticipantDirective] = Field(default_factory=list)


class AgentTurnPayload(BaseModel):
    speaker_participant_id: str
    speaker_name: str
    turn_index: int
    round_index: int
    utterance: str
    behavior_summary: str
    intent_tags: list[str] = Field(default_factory=list)
    target_participant_ids: list[str] = Field(default_factory=list)
    addressed_from_turn_id: str | None = None
    topic_tags: list[str] = Field(default_factory=list)
    next_speaker_suggestions: list[str] = Field(default_factory=list)
    self_observation: str | None = None


class SceneEvent(BaseModel):
    title: str
    description: str | None = None
    event_tags: list[str] = Field(default_factory=list)
    source_participant_id: str | None = None
    target_participant_ids: list[str] = Field(default_factory=list)
    linked_turn_indices: list[int] = Field(default_factory=list)


class SceneRelationshipDelta(BaseModel):
    source_participant_id: str
    target_participant_id: str
    changes: dict[str, int]
    reason: str
    event_tags: list[str] = Field(default_factory=list)

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


class ScenePairDateResult(BaseModel):
    pair_index: int
    participant_ids: list[str] = Field(default_factory=list)
    participant_names: list[str] = Field(default_factory=list)
    interaction_type: str = "pair_date"
    spark_level: str = "neutral"
    summary: str
    key_events: list[str] = Field(default_factory=list)
    relationship_deltas: list[SceneRelationshipDelta] = Field(default_factory=list)
    affects_future_candidate: bool = False
    level_semantic: str = "level_01_beginning_appeal"


class SceneCompetitionMapItem(BaseModel):
    source_participant_id: str
    target_participant_id: str
    focus_participant_id: str | None = None
    competition_sense: int = 0
    reason: str
    event_tags: list[str] = Field(default_factory=list)

    @field_validator("competition_sense")
    @classmethod
    def validate_competition_sense(cls, value: int) -> int:
        if value < 0 or value > 100:
            raise ValueError("competition_sense must stay within [0, 100]")
        return value


class SceneSelectionResult(BaseModel):
    selector_participant_id: str
    selector_name: str
    selected_target_participant_id: str
    selected_target_name: str
    outcome_type: str
    conversation_summary: str
    key_events: list[str] = Field(default_factory=list)
    relationship_deltas: list[SceneRelationshipDelta] = Field(default_factory=list)
    event_tags: list[str] = Field(default_factory=list)
    level_semantic: str = "level_02_relationship_promotion"


class SceneRefereeResult(BaseModel):
    scene_id: str
    scene_summary: str
    major_events: list[SceneEvent] = Field(default_factory=list)
    relationship_deltas: list[SceneRelationshipDelta] = Field(default_factory=list)
    pair_date_results: list[ScenePairDateResult] = Field(default_factory=list)
    competition_map: list[SceneCompetitionMapItem] = Field(default_factory=list)
    selection_results: list[SceneSelectionResult] = Field(default_factory=list)
    participant_memory_updates: list[dict] = Field(default_factory=list)
    next_tension: str


class SceneRuntimeExecution(BaseModel):
    input_summary: dict
    orchestrator_plan: SceneOrchestratorPlan
    orchestrator_raw: dict | str
    messages: list[AgentTurnPayload] = Field(default_factory=list)
    referee_result: SceneRefereeResult
    referee_raw: dict | str
    replay_payload: dict


class TimelineScenePreview(BaseModel):
    scene_run_id: str
    scene_code: str
    scene_index: int
    status: str
    summary: str | None = None
    tension: str | None = None
    replay_url: str | None = None


class ParticipantCard(BaseModel):
    participant_id: str
    name: str
    cast_role: str
    display_order: int
    personality_summary: str | None = None
    editable_personality: dict = Field(default_factory=dict)


class RelationshipCard(BaseModel):
    source_participant_id: str
    source_name: str
    target_participant_id: str
    target_name: str
    relationship_kind: str
    status: str
    trend: str
    top_reasons: list[str] = Field(default_factory=list)
    surface_metrics: dict[str, int] = Field(default_factory=dict)
    last_event_tags: list[str] = Field(default_factory=list)


class HotPair(BaseModel):
    participant_a_id: str
    participant_a_name: str
    participant_b_id: str
    participant_b_name: str
    combined_score: int
    summary: str


class RelationshipGraphNode(BaseModel):
    participant_id: str
    name: str
    cast_role: str
    outgoing_score: int
    incoming_score: int
    total_score: int


class RelationshipGraphEdge(BaseModel):
    source_participant_id: str
    source_name: str
    target_participant_id: str
    target_name: str
    score: int
    status: str
    trend: str
    strongest_metric: str | None = None
    last_event_tags: list[str] = Field(default_factory=list)


class RelationshipGraphPreview(BaseModel):
    node_count: int
    edge_count: int
    strongest_signals: list[RelationshipCard] = Field(default_factory=list)


class SimulationOverviewResponse(BaseModel):
    id: str
    project_id: str
    status: str
    current_scene_index: int
    current_scene_code: str | None = None
    latest_scene_summary: str | None = None
    latest_audit_snippet: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None
    strategy_cards: list[str] = Field(default_factory=list)
    active_tension: str | None = None
    latest_scene_replay_url: str | None = None
    scene_timeline_preview: list[TimelineScenePreview] = Field(default_factory=list)
    participants: list[ParticipantCard] = Field(default_factory=list)
    relationship_cards: list[RelationshipCard] = Field(default_factory=list)
    group_tension_summary: str | None = None
    hot_pairs: list[HotPair] = Field(default_factory=list)
    isolated_participants: list[ParticipantCard] = Field(default_factory=list)
    relationship_graph_preview: RelationshipGraphPreview | None = None
    recent_audit_logs: list[dict] = Field(default_factory=list)


class SceneRound(BaseModel):
    round_index: int
    phase_label: str | None = None
    turns: list[AgentTurnPayload] = Field(default_factory=list)


class SpeakerSwitchSummary(BaseModel):
    participant_id: str
    name: str
    turn_count: int
    addressed_count: int


class SceneReplayResponse(BaseModel):
    simulation_id: str
    scene_run_id: str
    scene_code: str
    scene_index: int
    status: str
    summary: str | None = None
    scene_plan: SceneOrchestratorPlan | None = None
    messages: list[AgentTurnPayload] = Field(default_factory=list)
    rounds: list[SceneRound] = Field(default_factory=list)
    speaker_switch_summary: list[SpeakerSwitchSummary] = Field(default_factory=list)
    major_events: list[SceneEvent] = Field(default_factory=list)
    relationship_deltas: list[SceneRelationshipDelta] = Field(default_factory=list)
    pair_date_results: list[ScenePairDateResult] = Field(default_factory=list)
    competition_map: list[SceneCompetitionMapItem] = Field(default_factory=list)
    selection_results: list[SceneSelectionResult] = Field(default_factory=list)
    group_state_after_scene: dict = Field(default_factory=dict)
    next_tension: str | None = None
    replay_url: str | None = None


class SimulationTimelineResponse(BaseModel):
    simulation_id: str
    scenes: list[TimelineScenePreview] = Field(default_factory=list)


class SimulationRelationshipsResponse(BaseModel):
    simulation_id: str
    participants: list[ParticipantCard] = Field(default_factory=list)
    relationships: list[RelationshipCard] = Field(default_factory=list)


class SimulationRelationshipGraphResponse(BaseModel):
    simulation_id: str
    group_tension_summary: str | None = None
    nodes: list[RelationshipGraphNode] = Field(default_factory=list)
    edges: list[RelationshipGraphEdge] = Field(default_factory=list)
    strongest_signals: list[RelationshipCard] = Field(default_factory=list)
    hot_pairs: list[HotPair] = Field(default_factory=list)
    isolated_participants: list[ParticipantCard] = Field(default_factory=list)


class PersonalityRecord(BaseModel):
    participant_id: str
    name: str
    cast_role: str
    editable_personality: dict = Field(default_factory=dict)
    changed_fields: list[str] = Field(default_factory=list)
    preset_slug: str | None = None


class SimulationPersonalitiesResponse(BaseModel):
    simulation_id: str
    personalities: list[PersonalityRecord] = Field(default_factory=list)
