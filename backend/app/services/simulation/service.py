from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    ParticipantPersonalityOverride,
    ParticipantProfile,
    PersonalityPreset,
    Project,
    RelationshipState,
    SceneArtifact,
    SceneMessage,
    SceneRun,
    SimulationRun,
    StateSnapshot,
)
from app.schemas.project import ParticipantImportPayload, ParticipantImportRequest, ProjectCreateRequest
from app.schemas.simulation import SimulationCreateRequest
from app.services.simulation.scene_registry import (
    PHASE3_SCENE_REGISTRY,
    SCENE_01_CODE,
)


BUILTIN_PERSONALITY_PRESETS = [
    {
        "slug": "steady-anchor",
        "name": "稳态支点",
        "description": "更稳定、更耐受冲突，适合多人互动中的安全感角色。",
        "values": {
            "extroversion": 48,
            "initiative": 52,
            "emotional_openness": 44,
            "attachment_style": "secure",
            "conflict_style": "steady_boundary",
            "self_esteem_stability": 72,
        },
    },
    {
        "slug": "spark-chaser",
        "name": "火花追逐者",
        "description": "更外向主动，追求互动火花，也更容易制造张力。",
        "values": {
            "extroversion": 78,
            "initiative": 74,
            "emotional_openness": 68,
            "attachment_style": "anxious",
            "conflict_style": "press_then_clarify",
            "self_esteem_stability": 45,
        },
    },
    {
        "slug": "careful-observer",
        "name": "谨慎观察者",
        "description": "不抢中心但持续判断场内信号，对被理解感更敏感。",
        "values": {
            "extroversion": 34,
            "initiative": 39,
            "emotional_openness": 42,
            "attachment_style": "avoidant",
            "conflict_style": "observe_then_withdraw",
            "self_esteem_stability": 58,
        },
    },
]


def create_project(db: Session, payload: ProjectCreateRequest) -> Project:
    project = Project(name=payload.name, description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_project_or_404(db: Session, project_id: str) -> Project | None:
    return db.get(Project, project_id)


def import_participants(
    db: Session,
    project: Project,
    payload: ParticipantImportRequest,
) -> list[ParticipantProfile]:
    participants: list[ParticipantProfile] = []
    existing_stmt = select(ParticipantProfile).where(ParticipantProfile.project_id == project.id)
    for existing in db.scalars(existing_stmt).all():
        db.delete(existing)
    db.flush()

    for index, item in enumerate(payload.participants):
        editable_personality = build_editable_personality(item)
        participant = ParticipantProfile(
            project_id=project.id,
            name=item.name,
            cast_role=item.cast_role,
            age=item.age,
            city=item.city,
            occupation=item.occupation,
            background_summary=item.background_summary,
            personality_summary=item.personality_summary,
            attachment_style=editable_personality["attachment_style"],
            appearance_tags=item.appearance_tags,
            personality_tags=item.personality_tags,
            preferred_traits=item.preferred_traits,
            disliked_traits=item.disliked_traits,
            commitment_goal=editable_personality["commitment_goal"],
            imported_payload=item.model_dump(),
            editable_personality=editable_personality,
            soul_data=build_soul_data(item, editable_personality),
            is_active=item.is_active,
            display_order=item.display_order if item.display_order is not None else index,
        )
        db.add(participant)
        participants.append(participant)

    db.commit()
    for participant in participants:
        db.refresh(participant)
    return participants


def deep_merge_dict(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            nested = dict(merged[key])
            nested.update(value)
            merged[key] = nested
        else:
            merged[key] = value
    return merged


def build_editable_personality(payload: ParticipantImportPayload) -> dict:
    editable = {
        "extroversion": 50,
        "initiative": 50,
        "emotional_openness": 50,
        "attachment_style": payload.attachment_style or "secure",
        "conflict_style": "avoid_then_explode",
        "self_esteem_stability": 50,
        "pace_preference": "gradual_but_clear",
        "commitment_goal": payload.commitment_goal or "serious_relationship",
        "preferred_traits": payload.preferred_traits,
        "disliked_traits": payload.disliked_traits,
        "boundaries": {
            "hard_boundaries": [],
            "soft_boundaries": [],
        },
        "expression_style": {
            "communication_style": "balanced",
            "reassurance_need": "medium",
        },
    }
    if payload.editable_personality is not None:
        editable.update(payload.editable_personality.model_dump())
    return editable


def sync_participant_personality(participant: ParticipantProfile, editable_personality: dict) -> None:
    payload = dict(participant.imported_payload or {})
    payload["editable_personality"] = editable_personality
    payload["attachment_style"] = editable_personality["attachment_style"]
    payload["commitment_goal"] = editable_personality["commitment_goal"]
    payload["preferred_traits"] = editable_personality.get("preferred_traits", [])
    payload["disliked_traits"] = editable_personality.get("disliked_traits", [])
    participant.imported_payload = payload
    participant.editable_personality = editable_personality
    participant.attachment_style = editable_personality["attachment_style"]
    participant.commitment_goal = editable_personality["commitment_goal"]
    participant.preferred_traits = editable_personality.get("preferred_traits", [])
    participant.disliked_traits = editable_personality.get("disliked_traits", [])
    participant.soul_data = build_soul_data(
        ParticipantImportPayload.model_validate(payload),
        editable_personality,
    )


def build_soul_data(payload: ParticipantImportPayload, editable_personality: dict) -> dict:
    return {
        "agent_name": payload.name,
        "cast_role": payload.cast_role,
        "stable_profile": {
            "basic_info": {
                "age": payload.age,
                "city": payload.city,
                "job": payload.occupation,
                "appearance_tags": payload.appearance_tags,
            },
            "personality_core": {
                "extroversion": editable_personality["extroversion"],
                "initiative": editable_personality["initiative"],
                "emotional_openness": editable_personality["emotional_openness"],
                "attachment_style": editable_personality["attachment_style"],
                "conflict_style": editable_personality["conflict_style"],
                "self_esteem_stability": editable_personality["self_esteem_stability"],
            },
            "dating_preferences": {
                "preferred_traits": editable_personality["preferred_traits"],
                "disliked_traits": editable_personality["disliked_traits"],
                "pace_preference": editable_personality["pace_preference"],
                "commitment_goal": editable_personality["commitment_goal"],
            },
            "boundaries": editable_personality["boundaries"],
            "expression_style": editable_personality["expression_style"],
        },
        "dynamic_state": {
            "mood_baseline": 50,
            "emotional_energy": 58,
            "social_fatigue": 22,
            "self_doubt": clamp(60 - editable_personality["self_esteem_stability"] // 2, 18, 72),
            "current_goal": "form_a_clear_read_on_people",
            "last_scene_summary": None,
        },
        "relationships": {},
        "scene_memory": {
            "completed_scenes": [],
            "notable_events": [],
        },
        "explanation_hooks": {
            "core_pattern": build_core_pattern(editable_personality),
            "growth_edge": build_growth_edge(editable_personality),
        },
    }


def build_core_pattern(editable_personality: dict) -> str:
    attachment_style = editable_personality["attachment_style"]
    if attachment_style == "anxious":
        return "对不确定和竞争信号更敏感，容易放大暧昧中的细微变化。"
    if attachment_style == "avoidant":
        return "会先保护边界，再决定是否暴露真实情绪。"
    return "先观察关系是否稳定，再逐步增加投入。"


def build_growth_edge(editable_personality: dict) -> str:
    if editable_personality["initiative"] < 45:
        return "如果能更早主动接住关键话题，会减少被动错位。"
    if editable_personality["emotional_openness"] < 45:
        return "如果能更直接表达真实感受，会减少误解累积。"
    return "如果能在多人场里更明确确认目标，会减少摇摆成本。"


def create_simulation(
    db: Session,
    project: Project,
    payload: SimulationCreateRequest,
) -> tuple[SimulationRun, SceneRun]:
    ensure_personality_presets(db)
    participants = get_active_participants(db, project.id)
    participant_lookup = {participant.id: participant for participant in participants}
    selected_ids = payload.selected_participant_ids or [participant.id for participant in participants]
    if len(set(selected_ids)) != len(selected_ids):
        raise ValueError("selected_participant_ids contains duplicates.")

    missing_ids = [participant_id for participant_id in selected_ids if participant_id not in participant_lookup]
    if missing_ids:
        raise ValueError(f"Unknown participant ids: {', '.join(missing_ids)}")

    selected_participants = [participant_lookup[participant_id] for participant_id in selected_ids]
    scene_codes = resolve_scene_pack(payload.scene_pack_config)
    personality_overrides = {
        participant_id: override.model_dump()
        for participant_id, override in payload.participant_personality_overrides.items()
    }
    if len(selected_participants) < 3:
        raise ValueError("Project must include at least 3 active participants.")

    simulation = SimulationRun(
        project_id=project.id,
        status="queued",
        current_scene_index=1,
        current_scene_code=SCENE_01_CODE,
        strategy_cards=payload.strategy_cards,
    )
    db.add(simulation)
    db.flush()

    first_scene: SceneRun | None = None
    for scene_code, meta in ordered_scene_registry(scene_codes):
        scene_run = SceneRun(
            simulation_run_id=simulation.id,
            project_id=project.id,
            scene_index=meta["scene_index"],
            scene_code=scene_code,
            status="queued" if scene_code == SCENE_01_CODE else "pending",
        )
        db.add(scene_run)
        if scene_code == SCENE_01_CODE:
            first_scene = scene_run

    for participant in selected_participants:
        override_data = deep_merge_dict(
            participant.editable_personality or {},
            personality_overrides.get(participant.id, {}),
        )
        db.add(
            ParticipantPersonalityOverride(
                project_id=project.id,
                simulation_run_id=simulation.id,
                participant_id=participant.id,
                source_type="simulation_setup",
                preset_slug=None,
                override_data=override_data,
                changed_fields=calculate_personality_changed_fields(
                    participant.imported_payload,
                    override_data,
                ),
            )
        )

    for source in selected_participants:
        source_personality = personality_overrides.get(source.id)
        if source_personality:
            source_shadow = ParticipantProfile(
                id=source.id,
                editable_personality=deep_merge_dict(source.editable_personality or {}, source_personality),
                appearance_tags=source.appearance_tags,
                personality_tags=source.personality_tags,
                attachment_style=source.attachment_style,
                preferred_traits=source.preferred_traits,
                disliked_traits=source.disliked_traits,
            )
        else:
            source_shadow = source
        for target in selected_participants:
            if source.id == target.id:
                continue
            target_personality = personality_overrides.get(target.id)
            if target_personality:
                target_shadow = ParticipantProfile(
                    id=target.id,
                    editable_personality=deep_merge_dict(
                        target.editable_personality or {},
                        target_personality,
                    ),
                    appearance_tags=target.appearance_tags,
                    personality_tags=target.personality_tags,
                    attachment_style=target.attachment_style,
                    preferred_traits=target.preferred_traits,
                    disliked_traits=target.disliked_traits,
                )
            else:
                target_shadow = target
            metrics = build_initial_relationship_metrics(source_shadow, target_shadow)
            db.add(
                RelationshipState(
                    project_id=project.id,
                    simulation_run_id=simulation.id,
                    source_participant_id=source.id,
                    target_participant_id=target.id,
                    relationship_kind="social_interest",
                    metrics=metrics,
                    status=derive_relationship_status(metrics),
                    recent_trend="observing",
                    notes=["初始关系已根据导入资料和人格配置建立。"],
                    last_event_tags=["initial_seed"],
                )
            )

    db.commit()
    db.refresh(simulation)
    if first_scene is None:
        raise ValueError("Scene registry must include scene_01_intro.")
    db.refresh(first_scene)
    return simulation, first_scene


def resolve_scene_pack(scene_pack_config: dict | None) -> list[str]:
    if not scene_pack_config:
        return list(PHASE3_SCENE_REGISTRY.keys())
    requested = scene_pack_config.get("scene_codes")
    if not isinstance(requested, list) or not requested:
        return list(PHASE3_SCENE_REGISTRY.keys())
    valid_codes = [scene_code for scene_code in requested if scene_code in PHASE3_SCENE_REGISTRY]
    return valid_codes or list(PHASE3_SCENE_REGISTRY.keys())


def ordered_scene_registry(scene_codes: list[str] | None = None) -> list[tuple[str, dict]]:
    allowed = set(scene_codes or PHASE3_SCENE_REGISTRY.keys())
    return sorted(
        [
            (scene_code, meta)
            for scene_code, meta in PHASE3_SCENE_REGISTRY.items()
            if scene_code in allowed
        ],
        key=lambda item: item[1]["scene_index"],
    )


def ensure_personality_presets(db: Session) -> None:
    existing = {
        item.slug
        for item in db.scalars(select(PersonalityPreset)).all()
    }
    created = False
    for preset in BUILTIN_PERSONALITY_PRESETS:
        if preset["slug"] in existing:
            continue
        db.add(PersonalityPreset(**preset))
        created = True
    if created:
        db.commit()


def list_personality_presets(db: Session) -> list[PersonalityPreset]:
    ensure_personality_presets(db)
    stmt = select(PersonalityPreset).order_by(PersonalityPreset.created_at.asc())
    return list(db.scalars(stmt).all())


def calculate_personality_changed_fields(imported_payload: dict, editable_personality: dict) -> list[str]:
    baseline = build_editable_personality(ParticipantImportPayload.model_validate(imported_payload))
    changed = []
    for key, value in editable_personality.items():
        if baseline.get(key) != value:
            changed.append(key)
    return changed


def get_active_participants(db: Session, project_id: str) -> list[ParticipantProfile]:
    stmt = (
        select(ParticipantProfile)
        .where(
            ParticipantProfile.project_id == project_id,
            ParticipantProfile.is_active.is_(True),
        )
        .order_by(ParticipantProfile.display_order.asc(), ParticipantProfile.created_at.asc())
    )
    return list(db.scalars(stmt).all())


def get_project_participant_or_404(
    db: Session,
    project_id: str,
    participant_id: str,
) -> ParticipantProfile | None:
    stmt = select(ParticipantProfile).where(
        ParticipantProfile.project_id == project_id,
        ParticipantProfile.id == participant_id,
    )
    return db.scalar(stmt)


def update_project_participant_personality(
    db: Session,
    participant: ParticipantProfile,
    editable_personality: dict,
) -> ParticipantProfile:
    sync_participant_personality(participant, editable_personality)
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant


def apply_preset_to_project_participants(
    db: Session,
    project: Project,
    preset_slug: str,
    participant_ids: list[str],
) -> list[ParticipantProfile]:
    preset = db.scalar(select(PersonalityPreset).where(PersonalityPreset.slug == preset_slug))
    if preset is None:
        raise ValueError(f"Unknown preset: {preset_slug}")

    participants = get_active_participants(db, project.id)
    participant_lookup = {participant.id: participant for participant in participants}
    target_ids = participant_ids or list(participant_lookup.keys())
    missing_ids = [participant_id for participant_id in target_ids if participant_id not in participant_lookup]
    if missing_ids:
        raise ValueError(f"Unknown participant ids: {', '.join(missing_ids)}")

    for participant_id in target_ids:
        participant = participant_lookup[participant_id]
        editable_personality = deep_merge_dict(participant.editable_personality or {}, preset.values or {})
        sync_participant_personality(participant, editable_personality)
        db.add(participant)

    db.commit()
    refreshed = get_active_participants(db, project.id)
    return [participant for participant in refreshed if participant.id in target_ids]


def get_participant_lookup(db: Session, project_id: str) -> dict[str, ParticipantProfile]:
    return {item.id: item for item in get_active_participants(db, project_id)}


def get_simulation_participants(db: Session, simulation: SimulationRun) -> list[ParticipantProfile]:
    override_ids = list(
        db.scalars(
            select(ParticipantPersonalityOverride.participant_id)
            .where(ParticipantPersonalityOverride.simulation_run_id == simulation.id)
            .order_by(ParticipantPersonalityOverride.created_at.asc())
        ).all()
    )
    if not override_ids:
        return get_active_participants(db, simulation.project_id)

    participants = {
        participant.id: participant
        for participant in db.scalars(
            select(ParticipantProfile)
            .where(
                ParticipantProfile.project_id == simulation.project_id,
                ParticipantProfile.id.in_(override_ids),
            )
            .order_by(ParticipantProfile.display_order.asc(), ParticipantProfile.created_at.asc())
        ).all()
    }
    return [participants[participant_id] for participant_id in override_ids if participant_id in participants]


def get_simulation_or_404(db: Session, simulation_id: str) -> SimulationRun | None:
    return db.get(SimulationRun, simulation_id)


def build_initial_relationship_metrics(
    source: ParticipantProfile,
    target: ParticipantProfile,
) -> dict:
    source_personality = source.editable_personality or {}
    target_personality = target.editable_personality or {}
    preferred_traits = set(source_personality.get("preferred_traits", source.preferred_traits or []))
    disliked_traits = set(source_personality.get("disliked_traits", source.disliked_traits or []))
    target_tags = set((target.appearance_tags or []) + (target.personality_tags or []))
    overlap = len(preferred_traits & target_tags)
    dislikes = len(disliked_traits & target_tags)

    initiative_gap = abs(
        int(source_personality.get("initiative", 50)) - int(target_personality.get("initiative", 50))
    )
    openness_gap = abs(
        int(source_personality.get("emotional_openness", 50))
        - int(target_personality.get("emotional_openness", 50))
    )
    commitment_alignment = (
        64
        if source_personality.get("commitment_goal") == target_personality.get("commitment_goal")
        else 44
    )
    attachment_style = str(source_personality.get("attachment_style", source.attachment_style or "")).lower()
    anxiety_base = 56 if attachment_style == "anxious" else 30 if attachment_style == "secure" else 40
    extroversion = int(source_personality.get("extroversion", 50))
    initiative = int(source_personality.get("initiative", 50))

    attraction = clamp(34 + overlap * 8 - dislikes * 6 + extroversion // 12, 18, 84)
    comfort = clamp(30 + overlap * 4 - dislikes * 3 + max(0, 15 - initiative_gap) // 2, 18, 72)
    trust = clamp(24 + overlap * 3 + int(source_personality.get("self_esteem_stability", 50)) // 12, 18, 58)
    curiosity = clamp(40 + overlap * 5 + initiative // 10 - dislikes * 2, 18, 82)
    understood = clamp(26 + max(0, 18 - openness_gap) // 2, 18, 62)

    return {
        "initial_attraction": attraction,
        "attraction": clamp(attraction - 2, 18, 82),
        "trust": trust,
        "comfort": comfort,
        "understood": understood,
        "expectation": clamp(32 + overlap * 4 + initiative // 15, 18, 70),
        "disappointment": 6,
        "conflict": 3,
        "anxiety": clamp(anxiety_base + dislikes * 3 - overlap * 2, 18, 72),
        "curiosity": curiosity,
        "exclusivity_pressure": 10,
        "commitment_alignment": commitment_alignment,
    }


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, int(value)))


def derive_relationship_status(metrics: dict) -> str:
    attraction = metrics["attraction"]
    trust = metrics["trust"]
    comfort = metrics["comfort"]
    understood = metrics["understood"]
    expectation = metrics["expectation"]
    disappointment = metrics["disappointment"]
    conflict = metrics["conflict"]
    anxiety = metrics["anxiety"]
    curiosity = metrics["curiosity"]
    commitment_alignment = metrics["commitment_alignment"]

    if attraction >= 70 and trust >= 68 and commitment_alignment >= 65 and conflict < 35:
        return "paired"
    if attraction < 25 and trust < 25:
        return "out"
    if disappointment >= 75:
        return "out"
    if trust < 35 and conflict >= 60:
        return "blocked"
    if commitment_alignment < 35:
        return "blocked"
    if attraction < 45 or curiosity < 35:
        if disappointment >= 50:
            return "cooling"
    if attraction >= 60 and (anxiety >= 55 or conflict >= 50):
        return "unstable"
    if (
        attraction >= 65
        and trust >= 60
        and understood >= 55
        and expectation >= 55
        and conflict < 45
    ):
        return "heating_up"
    if attraction >= 50 and comfort >= 50 and trust >= 45 and conflict < 40:
        return "warming"
    return "observing"


def derive_recent_trend(changes: dict[str, int]) -> str:
    positive = sum(value for value in changes.values() if value > 0)
    negative = abs(sum(value for value in changes.values() if value < 0))
    if positive >= negative + 6:
        return "warming"
    if negative >= positive + 6:
        return "cooling"
    return "observing"


def enqueue_scene(scene_run_id: str) -> None:
    from app.core.queue import SCENE_QUEUE_NAME, get_redis_client

    redis_client = get_redis_client()
    redis_client.lpush(SCENE_QUEUE_NAME, scene_run_id)


def claim_scene_by_id(db: Session, scene_run_id: str, claim_timeout_seconds: int) -> SceneRun | None:
    scene_run = db.get(SceneRun, scene_run_id, with_for_update=True)
    if scene_run is None:
        return None

    now = datetime.now(timezone.utc)
    was_failed = scene_run.status == "failed"
    is_stale = (
        scene_run.status in {"claimed", "running"}
        and scene_run.claimed_at is not None
        and scene_run.claimed_at < now - timedelta(seconds=claim_timeout_seconds)
    )
    if scene_run.status not in {"queued", "failed"} and not is_stale:
        return None

    scene_run.status = "claimed"
    scene_run.claim_token = str(uuid4())
    scene_run.claimed_at = now
    scene_run.retry_count = scene_run.retry_count + 1 if is_stale or was_failed else scene_run.retry_count
    db.add(scene_run)
    db.commit()
    db.refresh(scene_run)
    return scene_run


def mark_simulation_running(db: Session, simulation: SimulationRun) -> None:
    simulation.status = "running"
    simulation.started_at = simulation.started_at or datetime.now(timezone.utc)
    db.add(simulation)
    db.commit()


def mark_scene_failed(db: Session, scene_run: SceneRun, simulation: SimulationRun, error_message: str) -> None:
    now = datetime.now(timezone.utc)
    scene_run.status = "failed"
    scene_run.error_message = error_message
    scene_run.finished_at = now
    simulation.status = "failed"
    simulation.error_message = error_message
    simulation.finished_at = now
    db.add(
        AuditLog(
            simulation_run_id=simulation.id,
            scene_run_id=scene_run.id,
            log_type="error_info",
            payload={"error_message": error_message},
        )
    )
    db.add(scene_run)
    db.add(simulation)
    db.commit()


def get_latest_snapshot(db: Session, simulation_id: str) -> StateSnapshot | None:
    stmt = (
        select(StateSnapshot)
        .where(StateSnapshot.simulation_run_id == simulation_id)
        .order_by(StateSnapshot.created_at.desc())
    )
    return db.scalar(stmt)


def get_recent_audit_logs(db: Session, simulation_id: str) -> list[AuditLog]:
    stmt = (
        select(AuditLog)
        .where(AuditLog.simulation_run_id == simulation_id)
        .order_by(AuditLog.created_at.desc())
        .limit(12)
    )
    return list(db.scalars(stmt).all())


def get_scene_messages(db: Session, scene_run_id: str) -> list[SceneMessage]:
    stmt = (
        select(SceneMessage)
        .where(SceneMessage.scene_run_id == scene_run_id)
        .order_by(SceneMessage.turn_index.asc(), SceneMessage.created_at.asc())
    )
    return list(db.scalars(stmt).all())


def get_scene_artifact(db: Session, scene_run_id: str, artifact_type: str) -> SceneArtifact | None:
    stmt = select(SceneArtifact).where(
        SceneArtifact.scene_run_id == scene_run_id,
        SceneArtifact.artifact_type == artifact_type,
    )
    return db.scalar(stmt)


def get_scene_artifacts(db: Session, simulation_id: str) -> list[SceneArtifact]:
    stmt = select(SceneArtifact).where(SceneArtifact.simulation_run_id == simulation_id)
    return list(db.scalars(stmt).all())


def build_relationship_surface_metrics(metrics: dict) -> dict[str, int]:
    keys = [
        "attraction",
        "trust",
        "comfort",
        "understood",
        "curiosity",
        "anxiety",
        "expectation",
    ]
    return {key: int(metrics.get(key, 0)) for key in keys}
