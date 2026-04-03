from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import (
    ParticipantPersonalityOverride,
    ParticipantProfile,
    RelationshipState,
    SceneRun,
    SimulationRun,
)
from app.schemas.runtime import (
    AgentTurnPayload,
    HotPair,
    ParticipantCard,
    PersonalityRecord,
    RelationshipCard,
    RelationshipGraphEdge,
    RelationshipGraphNode,
    RelationshipGraphPreview,
    SceneOrchestratorPlan,
    SceneRound,
    SceneReplayResponse,
    SceneRefereeResult,
    SimulationRelationshipGraphResponse,
    SimulationOverviewResponse,
    SimulationPersonalitiesResponse,
    SimulationRelationshipsResponse,
    SpeakerSwitchSummary,
    SimulationTimelineResponse,
    TimelineScenePreview,
)
from app.schemas.simulation import SimulationCreateRequest, SimulationResponse
from app.services.simulation.service import (
    build_relationship_surface_metrics,
    create_simulation,
    enqueue_scene,
    get_project_or_404,
    get_recent_audit_logs,
    get_scene_artifact,
    get_scene_artifacts,
    get_scene_messages,
    get_simulation_participants,
    get_simulation_or_404,
)

router = APIRouter(tags=["simulations"])


@router.post(
    "/projects/{project_id}/simulations",
    response_model=SimulationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_simulation_endpoint(
    project_id: str,
    payload: SimulationCreateRequest,
    db: Session = Depends(get_db),
) -> SimulationResponse:
    project = get_project_or_404(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    try:
        simulation, scene_run = create_simulation(db, project, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    enqueue_scene(scene_run.id)
    return serialize_simulation(simulation)


@router.get("/simulations/{simulation_id}", response_model=SimulationOverviewResponse)
def get_simulation_endpoint(
    simulation_id: str,
    db: Session = Depends(get_db),
) -> SimulationOverviewResponse:
    simulation = get_simulation_or_404(db, simulation_id)
    if simulation is None:
        raise HTTPException(status_code=404, detail="Simulation not found.")

    scenes = list(
        db.scalars(
            select(SceneRun)
            .where(SceneRun.simulation_run_id == simulation.id)
            .order_by(SceneRun.scene_index.asc())
        ).all()
    )
    relationships = list(
        db.scalars(
            select(RelationshipState).where(RelationshipState.simulation_run_id == simulation.id)
        ).all()
    )
    participants_list = get_simulation_participants(db, simulation)
    participants = {participant.id: participant for participant in participants_list}
    override_lookup = get_override_lookup(db, simulation.id)
    artifacts = get_scene_artifacts(db, simulation.id)
    artifact_lookup = {(item.scene_run_id, item.artifact_type): item.payload for item in artifacts}

    timeline_preview = [
        build_timeline_preview(simulation.id, scene, artifact_lookup)
        for scene in scenes
    ]
    relationship_cards = build_relationship_cards(relationships, participants)
    hot_pairs = build_hot_pairs(relationships, participants)
    isolated_participants = build_isolated_participants(relationships, participants)
    latest_scene = scenes[-1] if scenes else None
    latest_scene_replay_url = (
        f"/simulations/{simulation.id}/scenes/{latest_scene.id}" if latest_scene else None
    )
    active_tension = None
    if latest_scene:
        replay_payload = artifact_lookup.get((latest_scene.id, "scene_replay_dto"))
        referee_payload = artifact_lookup.get((latest_scene.id, "scene_referee_result"))
        if replay_payload:
            active_tension = replay_payload.get("next_tension")
        elif referee_payload:
            active_tension = referee_payload.get("next_tension")

    audit_logs = get_recent_audit_logs(db, simulation.id)
    return SimulationOverviewResponse(
        id=simulation.id,
        project_id=simulation.project_id,
        status=simulation.status,
        current_scene_index=simulation.current_scene_index,
        current_scene_code=simulation.current_scene_code,
        latest_scene_summary=simulation.latest_scene_summary,
        latest_audit_snippet=simulation.latest_audit_snippet,
        created_at=simulation.created_at,
        started_at=simulation.started_at,
        finished_at=simulation.finished_at,
        error_message=simulation.error_message,
        strategy_cards=simulation.strategy_cards,
        active_tension=active_tension or simulation.latest_audit_snippet,
        latest_scene_replay_url=latest_scene_replay_url,
        scene_timeline_preview=timeline_preview,
        participants=build_participant_cards(participants_list, override_lookup),
        relationship_cards=relationship_cards,
        group_tension_summary=build_group_tension_summary(hot_pairs, isolated_participants),
        hot_pairs=hot_pairs,
        isolated_participants=isolated_participants,
        relationship_graph_preview=RelationshipGraphPreview(
            node_count=len(participants_list),
            edge_count=len(relationship_cards),
            strongest_signals=relationship_cards[:4],
        ),
        recent_audit_logs=[
            {
                "log_type": item.log_type,
                "payload": item.payload,
                "created_at": item.created_at.isoformat(),
            }
            for item in audit_logs
        ],
    )


@router.get(
    "/simulations/{simulation_id}/scenes/{scene_run_id}",
    response_model=SceneReplayResponse,
)
def get_scene_replay_endpoint(
    simulation_id: str,
    scene_run_id: str,
    db: Session = Depends(get_db),
) -> SceneReplayResponse:
    simulation = get_simulation_or_404(db, simulation_id)
    if simulation is None:
        raise HTTPException(status_code=404, detail="Simulation not found.")

    scene_run = db.scalar(
        select(SceneRun).where(
            SceneRun.id == scene_run_id,
            SceneRun.simulation_run_id == simulation.id,
        )
    )
    if scene_run is None:
        raise HTTPException(status_code=404, detail="Scene not found.")

    replay_artifact = get_scene_artifact(db, scene_run.id, "scene_replay_dto")
    if replay_artifact is not None:
        payload = dict(replay_artifact.payload)
        messages = [AgentTurnPayload.model_validate(item) for item in payload.get("messages", [])]
        scene_plan = (
            SceneOrchestratorPlan.model_validate(payload["scene_plan"])
            if payload.get("scene_plan")
            else None
        )
        payload.setdefault("rounds", [item.model_dump() for item in build_rounds(messages, scene_plan)])
        payload.setdefault(
            "speaker_switch_summary",
            [item.model_dump() for item in build_speaker_switch_summary(messages)],
        )
        payload.setdefault(
            "group_state_after_scene",
            build_group_state_after_scene(
                messages,
                [
                    item
                    if isinstance(item, dict)
                    else item.model_dump()
                    for item in payload.get("relationship_deltas", [])
                ],
                {participant.id: participant for participant in get_simulation_participants(db, simulation)},
            ),
        )
        return SceneReplayResponse.model_validate(payload)

    plan_artifact = get_scene_artifact(db, scene_run.id, "scene_orchestrator_plan")
    referee_artifact = get_scene_artifact(db, scene_run.id, "scene_referee_result")
    messages = [
        AgentTurnPayload(
            speaker_participant_id=item.speaker_guest_id,
            speaker_name=item.speaker_name,
            turn_index=item.turn_index,
            round_index=(item.raw_output or {}).get("round_index", 1),
            utterance=item.utterance,
            behavior_summary=item.behavior_summary or "",
            intent_tags=item.intent_tags,
            target_participant_ids=item.target_guest_ids,
            addressed_from_turn_id=(item.raw_output or {}).get("addressed_from_turn_id"),
            topic_tags=(item.raw_output or {}).get("topic_tags", []),
            next_speaker_suggestions=(item.raw_output or {}).get("next_speaker_suggestions", []),
            self_observation=(item.raw_output or {}).get("self_observation"),
        )
        for item in get_scene_messages(db, scene_run.id)
    ]
    referee = (
        SceneRefereeResult.model_validate(referee_artifact.payload)
        if referee_artifact is not None
        else None
    )
    return SceneReplayResponse(
        simulation_id=simulation.id,
        scene_run_id=scene_run.id,
        scene_code=scene_run.scene_code,
        scene_index=scene_run.scene_index,
        status=scene_run.status,
        summary=scene_run.summary,
        scene_plan=SceneOrchestratorPlan.model_validate(plan_artifact.payload) if plan_artifact else None,
        messages=messages,
        rounds=build_rounds(messages, SceneOrchestratorPlan.model_validate(plan_artifact.payload) if plan_artifact else None),
        speaker_switch_summary=build_speaker_switch_summary(messages),
        major_events=referee.major_events if referee else [],
        relationship_deltas=referee.relationship_deltas if referee else [],
        competition_map=referee.competition_map if referee else [],
        selection_results=referee.selection_results if referee else [],
        signal_results=referee.signal_results if referee else [],
        missed_expectations=referee.missed_expectations if referee else [],
        group_state_after_scene=build_group_state_after_scene(
            messages,
            [item.model_dump() for item in (referee.relationship_deltas if referee else [])],
            {participant.id: participant for participant in get_simulation_participants(db, simulation)},
        ),
        next_tension=referee.next_tension if referee else None,
        replay_url=f"/simulations/{simulation.id}/scenes/{scene_run.id}",
    )


@router.get(
    "/simulations/{simulation_id}/timeline",
    response_model=SimulationTimelineResponse,
)
def get_simulation_timeline_endpoint(
    simulation_id: str,
    db: Session = Depends(get_db),
) -> SimulationTimelineResponse:
    simulation = get_simulation_or_404(db, simulation_id)
    if simulation is None:
        raise HTTPException(status_code=404, detail="Simulation not found.")

    scenes = list(
        db.scalars(
            select(SceneRun)
            .where(SceneRun.simulation_run_id == simulation.id)
            .order_by(SceneRun.scene_index.asc())
        ).all()
    )
    artifacts = get_scene_artifacts(db, simulation.id)
    artifact_lookup = {(item.scene_run_id, item.artifact_type): item.payload for item in artifacts}
    return SimulationTimelineResponse(
        simulation_id=simulation.id,
        scenes=[
            build_timeline_preview(simulation.id, scene, artifact_lookup)
            for scene in scenes
        ],
    )


@router.get(
    "/simulations/{simulation_id}/relationships",
    response_model=SimulationRelationshipsResponse,
)
def get_simulation_relationships_endpoint(
    simulation_id: str,
    db: Session = Depends(get_db),
) -> SimulationRelationshipsResponse:
    simulation = get_simulation_or_404(db, simulation_id)
    if simulation is None:
        raise HTTPException(status_code=404, detail="Simulation not found.")

    relationships = list(
        db.scalars(
            select(RelationshipState).where(RelationshipState.simulation_run_id == simulation.id)
        ).all()
    )
    participants = get_simulation_participants(db, simulation)
    participant_lookup = {participant.id: participant for participant in participants}
    override_lookup = get_override_lookup(db, simulation.id)
    return SimulationRelationshipsResponse(
        simulation_id=simulation.id,
        participants=build_participant_cards(participants, override_lookup),
        relationships=build_relationship_cards(relationships, participant_lookup),
    )


@router.get(
    "/simulations/{simulation_id}/relationship-graph",
    response_model=SimulationRelationshipGraphResponse,
)
def get_simulation_relationship_graph_endpoint(
    simulation_id: str,
    db: Session = Depends(get_db),
) -> SimulationRelationshipGraphResponse:
    simulation = get_simulation_or_404(db, simulation_id)
    if simulation is None:
        raise HTTPException(status_code=404, detail="Simulation not found.")

    relationships = list(
        db.scalars(
            select(RelationshipState).where(RelationshipState.simulation_run_id == simulation.id)
        ).all()
    )
    participants = get_simulation_participants(db, simulation)
    participant_lookup = {participant.id: participant for participant in participants}
    relationship_cards = build_relationship_cards(relationships, participant_lookup)
    hot_pairs = build_hot_pairs(relationships, participant_lookup)
    isolated_participants = build_isolated_participants(relationships, participant_lookup)
    return SimulationRelationshipGraphResponse(
        simulation_id=simulation.id,
        group_tension_summary=build_group_tension_summary(hot_pairs, isolated_participants),
        nodes=build_graph_nodes(relationships, participant_lookup),
        edges=build_graph_edges(relationships, participant_lookup),
        strongest_signals=relationship_cards[:6],
        hot_pairs=hot_pairs,
        isolated_participants=isolated_participants,
    )


@router.get(
    "/simulations/{simulation_id}/personalities",
    response_model=SimulationPersonalitiesResponse,
)
def get_simulation_personalities_endpoint(
    simulation_id: str,
    db: Session = Depends(get_db),
) -> SimulationPersonalitiesResponse:
    simulation = get_simulation_or_404(db, simulation_id)
    if simulation is None:
        raise HTTPException(status_code=404, detail="Simulation not found.")

    participants = {item.id: item for item in get_simulation_participants(db, simulation)}
    overrides = list(
        db.scalars(
            select(ParticipantPersonalityOverride)
            .where(ParticipantPersonalityOverride.simulation_run_id == simulation.id)
            .order_by(ParticipantPersonalityOverride.created_at.asc())
        ).all()
    )
    return SimulationPersonalitiesResponse(
        simulation_id=simulation.id,
        personalities=[
            PersonalityRecord(
                participant_id=override.participant_id,
                name=participants[override.participant_id].name,
                cast_role=participants[override.participant_id].cast_role,
                editable_personality=override.override_data,
                changed_fields=override.changed_fields,
                preset_slug=override.preset_slug,
            )
            for override in overrides
            if override.participant_id in participants
        ],
    )


def build_timeline_preview(
    simulation_id: str,
    scene: SceneRun,
    artifact_lookup: dict[tuple[str, str], dict],
) -> TimelineScenePreview:
    replay_payload = artifact_lookup.get((scene.id, "scene_replay_dto"))
    referee_payload = artifact_lookup.get((scene.id, "scene_referee_result"))
    tension = None
    summary = scene.summary
    if replay_payload:
        summary = replay_payload.get("summary") or summary
        tension = replay_payload.get("next_tension")
    elif referee_payload:
        summary = referee_payload.get("scene_summary") or summary
        tension = referee_payload.get("next_tension")

    return TimelineScenePreview(
        scene_run_id=scene.id,
        scene_code=scene.scene_code,
        scene_index=scene.scene_index,
        status=scene.status,
        summary=summary,
        tension=tension,
        replay_url=f"/simulations/{simulation_id}/scenes/{scene.id}",
    )


def get_override_lookup(db: Session, simulation_id: str) -> dict[str, dict]:
    overrides = list(
        db.scalars(
            select(ParticipantPersonalityOverride)
            .where(ParticipantPersonalityOverride.simulation_run_id == simulation_id)
            .order_by(ParticipantPersonalityOverride.created_at.asc())
        ).all()
    )
    return {
        override.participant_id: override.override_data
        for override in overrides
    }


def build_participant_cards(
    participants: list[ParticipantProfile],
    override_lookup: dict[str, dict] | None = None,
) -> list[ParticipantCard]:
    override_lookup = override_lookup or {}
    return [
        ParticipantCard(
            participant_id=item.id,
            name=item.name,
            cast_role=item.cast_role,
            display_order=item.display_order,
            personality_summary=item.personality_summary,
            editable_personality=override_lookup.get(item.id, item.editable_personality),
        )
        for item in participants
    ]


def build_relationship_cards(
    relationships: list[RelationshipState],
    participants: dict[str, ParticipantProfile],
) -> list[RelationshipCard]:
    cards = []
    for item in relationships:
        source = participants.get(item.source_participant_id)
        target = participants.get(item.target_participant_id)
        if source is None or target is None:
            continue
        cards.append(
            RelationshipCard(
                source_participant_id=item.source_participant_id,
                source_name=source.name,
                target_participant_id=item.target_participant_id,
                target_name=target.name,
                relationship_kind=item.relationship_kind,
                status=item.status,
                trend=item.recent_trend,
                top_reasons=item.notes[:3],
                surface_metrics=build_relationship_surface_metrics(item.metrics),
                last_event_tags=item.last_event_tags,
            )
        )
    cards.sort(
        key=lambda item: (
            item.surface_metrics.get("attraction", 0)
            + item.surface_metrics.get("trust", 0)
            + item.surface_metrics.get("comfort", 0)
        ),
        reverse=True,
    )
    return cards


def build_hot_pairs(
    relationships: list[RelationshipState],
    participants: dict[str, ParticipantProfile],
) -> list[HotPair]:
    pair_scores: dict[tuple[str, str], int] = defaultdict(int)
    for relationship in relationships:
        if relationship.source_participant_id not in participants or relationship.target_participant_id not in participants:
            continue
        pair_key = tuple(sorted((relationship.source_participant_id, relationship.target_participant_id)))
        pair_scores[pair_key] += edge_score(relationship.metrics)

    hot_pairs = []
    for (participant_a_id, participant_b_id), combined_score in sorted(
        pair_scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:4]:
        participant_a = participants[participant_a_id]
        participant_b = participants[participant_b_id]
        hot_pairs.append(
            HotPair(
                participant_a_id=participant_a_id,
                participant_a_name=participant_a.name,
                participant_b_id=participant_b_id,
                participant_b_name=participant_b.name,
                combined_score=combined_score,
                summary=(
                    f"{participant_a.name} 和 {participant_b.name} 目前是最容易继续升温的一条线。"
                ),
            )
        )
    return hot_pairs


def build_isolated_participants(
    relationships: list[RelationshipState],
    participants: dict[str, ParticipantProfile],
) -> list[ParticipantCard]:
    totals: dict[str, int] = defaultdict(int)
    for relationship in relationships:
        if relationship.source_participant_id in participants:
            totals[relationship.source_participant_id] += edge_score(relationship.metrics)
        if relationship.target_participant_id in participants:
            totals[relationship.target_participant_id] += edge_score(relationship.metrics)

    sorted_participants = sorted(
        participants.values(),
        key=lambda participant: totals.get(participant.id, 0),
    )
    return build_participant_cards(sorted_participants[:2])


def build_group_tension_summary(
    hot_pairs: list[HotPair],
    isolated_participants: list[ParticipantCard],
) -> str:
    if hot_pairs and isolated_participants:
        return (
            f"当前最热的是 {hot_pairs[0].participant_a_name} 与 {hot_pairs[0].participant_b_name}，"
            f"而 {isolated_participants[0].name} 更像在多人场里暂时站在边缘。"
        )
    if hot_pairs:
        return hot_pairs[0].summary
    if isolated_participants:
        return f"{isolated_participants[0].name} 目前更像观察者，还没形成稳定连接。"
    return "多人关系图正在形成，还没有足够清晰的热区和边缘位。"


def build_graph_nodes(
    relationships: list[RelationshipState],
    participants: dict[str, ParticipantProfile],
) -> list[RelationshipGraphNode]:
    outgoing: dict[str, int] = defaultdict(int)
    incoming: dict[str, int] = defaultdict(int)
    for relationship in relationships:
        score = edge_score(relationship.metrics)
        outgoing[relationship.source_participant_id] += score
        incoming[relationship.target_participant_id] += score

    return [
        RelationshipGraphNode(
            participant_id=participant.id,
            name=participant.name,
            cast_role=participant.cast_role,
            outgoing_score=outgoing.get(participant.id, 0),
            incoming_score=incoming.get(participant.id, 0),
            total_score=outgoing.get(participant.id, 0) + incoming.get(participant.id, 0),
        )
        for participant in participants.values()
    ]


def build_graph_edges(
    relationships: list[RelationshipState],
    participants: dict[str, ParticipantProfile],
) -> list[RelationshipGraphEdge]:
    edges = []
    for relationship in relationships:
        source = participants.get(relationship.source_participant_id)
        target = participants.get(relationship.target_participant_id)
        if source is None or target is None:
            continue
        metrics = build_relationship_surface_metrics(relationship.metrics)
        strongest_metric = None
        if metrics:
            strongest_metric = max(metrics.items(), key=lambda item: item[1])[0]
        edges.append(
            RelationshipGraphEdge(
                source_participant_id=relationship.source_participant_id,
                source_name=source.name,
                target_participant_id=relationship.target_participant_id,
                target_name=target.name,
                score=edge_score(relationship.metrics),
                status=relationship.status,
                trend=relationship.recent_trend,
                strongest_metric=strongest_metric,
                last_event_tags=relationship.last_event_tags,
            )
        )
    edges.sort(key=lambda item: item.score, reverse=True)
    return edges


def build_rounds(
    messages: list[AgentTurnPayload],
    scene_plan: SceneOrchestratorPlan | None,
) -> list[SceneRound]:
    grouped: dict[int, list[AgentTurnPayload]] = defaultdict(list)
    for message in messages:
        grouped[message.round_index].append(message)
    rounds = []
    for round_index in sorted(grouped):
        phase_label = None
        if scene_plan and round_index - 1 < len(scene_plan.phase_outline):
            phase_label = scene_plan.phase_outline[round_index - 1]
        rounds.append(
            SceneRound(
                round_index=round_index,
                phase_label=phase_label,
                turns=grouped[round_index],
            )
        )
    return rounds


def build_speaker_switch_summary(messages: list[AgentTurnPayload]) -> list[SpeakerSwitchSummary]:
    turn_counts: dict[str, int] = defaultdict(int)
    addressed_counts: dict[str, int] = defaultdict(int)
    speaker_names: dict[str, str] = {}
    for message in messages:
        turn_counts[message.speaker_participant_id] += 1
        speaker_names[message.speaker_participant_id] = message.speaker_name
        for target_id in message.target_participant_ids:
            addressed_counts[target_id] += 1
    return [
        SpeakerSwitchSummary(
            participant_id=participant_id,
            name=speaker_names.get(participant_id, participant_id),
            turn_count=count,
            addressed_count=addressed_counts.get(participant_id, 0),
        )
        for participant_id, count in sorted(turn_counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def build_group_state_after_scene(
    messages: list[AgentTurnPayload],
    relationship_deltas: list[dict],
    participant_lookup: dict[str, ParticipantProfile],
) -> dict:
    topic_counts: dict[str, int] = defaultdict(int)
    attention_counts: dict[str, int] = defaultdict(int)
    pair_pressure: dict[tuple[str, str], int] = defaultdict(int)
    for message in messages:
        for topic in message.topic_tags:
            topic_counts[topic] += 1
        for target_id in message.target_participant_ids:
            attention_counts[target_id] += 1
    for delta in relationship_deltas:
        pair_key = tuple(sorted((delta["source_participant_id"], delta["target_participant_id"])))
        pair_pressure[pair_key] += sum(abs(value) for value in delta.get("changes", {}).values())

    dominant_topics = [topic for topic, _ in sorted(topic_counts.items(), key=lambda item: item[1], reverse=True)[:4]]
    attention_distribution = [
        {
            "participant_id": participant_id,
            "name": participant_lookup.get(participant_id).name if participant_lookup.get(participant_id) else participant_id,
            "mentions": count,
        }
        for participant_id, count in sorted(attention_counts.items(), key=lambda item: item[1], reverse=True)
    ]
    tension_pairs = [
        {
            "participant_ids": list(pair_key),
            "names": [
                participant_lookup.get(pair_key[0]).name if participant_lookup.get(pair_key[0]) else pair_key[0],
                participant_lookup.get(pair_key[1]).name if participant_lookup.get(pair_key[1]) else pair_key[1],
            ],
            "pressure": pressure,
        }
        for pair_key, pressure in sorted(pair_pressure.items(), key=lambda item: item[1], reverse=True)[:3]
    ]
    isolated_ids = [
        participant_id
        for participant_id in participant_lookup
        if attention_counts.get(participant_id, 0) == 0
    ]
    return {
        "dominant_topics": dominant_topics,
        "attention_distribution": attention_distribution,
        "tension_pairs": tension_pairs,
        "isolated_participants": [
            participant_lookup[participant_id].name
            for participant_id in isolated_ids
            if participant_id in participant_lookup
        ],
    }


def edge_score(metrics: dict) -> int:
    return (
        metrics.get("attraction", 0)
        + metrics.get("trust", 0)
        + metrics.get("comfort", 0)
        + metrics.get("curiosity", 0)
    )


def serialize_simulation(simulation: SimulationRun) -> SimulationResponse:
    return SimulationResponse(
        id=simulation.id,
        project_id=simulation.project_id,
        status=simulation.status,
        current_scene_index=simulation.current_scene_index,
        current_scene_code=simulation.current_scene_code,
        latest_scene_summary=simulation.latest_scene_summary,
        latest_audit_snippet=simulation.latest_audit_snippet,
        created_at=simulation.created_at,
    )
