from __future__ import annotations

import json
import math
import random
import re
from copy import copy
from collections import defaultdict
from datetime import datetime, timezone

from openai import OpenAI
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    AgentTurn,
    AuditLog,
    ParticipantProfile,
    ParticipantPersonalityOverride,
    ParticipantSceneMemory,
    RelationshipState,
    SceneArtifact,
    SceneEventLink,
    SceneMessage,
    SceneRun,
    SimulationRun,
    StateSnapshot,
)
from app.schemas.runtime import (
    AgentTurnPayload,
    ParticipantCard,
    PlanParticipant,
    SceneEvent,
    SceneOrchestratorPlan,
    SceneRefereeResult,
    SceneRelationshipDelta,
    SceneRuntimeExecution,
)
from app.services.simulation.scene_config import SCENE_CONFIG
from app.services.simulation.scene_registry import (
    PHASE3_SCENE_REGISTRY,
    SCENE_01_CODE,
    SCENE_02_CODE,
    SCENE_03_CODE,
    SCENE_04_CODE,
    SCENE_05_CODE,
    SCENE_06_CODE,
    SCENE_07_CODE,
)
from app.services.simulation.scenes.scene_03 import (
    build_scene_03_interest_target,
    execute_scene_03_runtime,
)
from app.services.simulation.scenes.scene_04 import (
    apply_scene_04_strategy_bias,
    apply_scene_04_turn_strategy_bias,
    build_scene_04_competition_seed_pairs,
    build_scene_04_focus_target,
    derive_scene_04_competition_map,
)
from app.services.simulation.scenes.scene_05 import (
    build_scene_05_seed,
    execute_scene_05_runtime,
)
from app.services.simulation.scenes.scene_06 import (
    build_scene_06_seed,
    execute_scene_06_runtime,
)
from app.services.simulation.scenes.scene_07 import (
    build_scene_07_invitation_seed,
    execute_scene_07_runtime,
)
from app.services.simulation.service import (
    build_relationship_surface_metrics,
    clamp,
    derive_recent_trend,
    derive_relationship_status,
    enqueue_scene,
    get_simulation_participants,
)


TURN_SYSTEM_PROMPT = """
你是恋爱模拟器 Phase 3 的单个 Participant Agent。
你只扮演当前 speaker，不能代替其他人发言，也不能决定最终关系结果。
你必须只返回一个 JSON 对象，不要输出任何解释、markdown、代码块。

硬性规则：
1. utterance 只写当前 speaker 的话，不超过 2 句。
2. behavior_summary 用一句话概括语气、动作或氛围。
3. intent_tags 只写 1-3 个短标签。
4. target_participant_ids 只能写当前 speaker 主要在对谁发起动作。
5. next_speaker_suggestions 只写 1-2 个你认为最自然的下一位。
6. self_observation 只能是当前 speaker 的主观感受。
""".strip()

ALLOWED_INTENT_TAGS = {
    "break_ice",
    "build_comfort",
    "signal_interest",
    "probe_depth",
    "test_chemistry",
    "show_stability",
    "show_humor",
    "protect_self_image",
    "observe_reaction",
    "redirect_topic",
    "tease_lightly",
    "invite_group",
}


def execute_scene_runtime(
    db: Session,
    scene_run: SceneRun,
    simulation: SimulationRun,
) -> SceneRuntimeExecution:
    if scene_run.retry_count > 0:
        reset_scene_runtime_records(db, scene_run.id)

    context = build_scene_context(db, simulation, scene_run.scene_code)
    input_summary = build_input_summary(context)
    plan = build_scene_orchestrator_plan(context)
    replace_scene_artifact(
        db,
        simulation.id,
        scene_run.id,
        "scene_orchestrator_plan",
        plan.model_dump(),
        commit=True,
    )
    persist_plan_audit_logs(db, simulation.id, scene_run.id, input_summary, plan.model_dump())

    if scene_run.scene_code == SCENE_03_CODE:
        return execute_scene_03_runtime(simulation, scene_run, context, input_summary, plan)
    if scene_run.scene_code == SCENE_05_CODE:
        return execute_scene_05_runtime(simulation, scene_run, context, input_summary, plan)
    if scene_run.scene_code == SCENE_06_CODE:
        return execute_scene_06_runtime(simulation, scene_run, context, input_summary, plan)
    if scene_run.scene_code == SCENE_07_CODE:
        return execute_scene_07_runtime(simulation, scene_run, context, input_summary, plan)

    transcript: list[AgentTurnPayload] = []
    for turn_index in range(1, plan.max_turns + 1):
        speaker_id = choose_next_speaker(context, plan, transcript)
        if speaker_id is None:
            break
        started_at = datetime.now(timezone.utc)
        input_payload = build_agent_input(context, plan, transcript, turn_index, speaker_id)
        turn, raw_output, normalized_input = generate_agent_turn(
            context,
            plan,
            transcript,
            turn_index,
            speaker_id,
            input_payload,
        )
        transcript.append(turn)
        persist_turn_records(
            db,
            simulation.id,
            scene_run.id,
            started_at,
            turn,
            raw_output,
            normalized_input,
        )
        if should_stop_scene(context, plan, transcript):
            break

    referee_result = build_referee_result(context, plan, transcript)
    replay_payload = {
        "simulation_id": simulation.id,
        "scene_run_id": scene_run.id,
        "scene_code": scene_run.scene_code,
        "scene_index": scene_run.scene_index,
        "status": "completed",
        "summary": referee_result.scene_summary,
        "scene_plan": plan.model_dump(),
        "messages": [message.model_dump() for message in transcript],
        "major_events": [event.model_dump() for event in referee_result.major_events],
        "relationship_deltas": [
            relationship_delta.model_dump()
            for relationship_delta in referee_result.relationship_deltas
        ],
        "competition_map": [item.model_dump() for item in referee_result.competition_map],
        "selection_results": [item.model_dump() for item in referee_result.selection_results],
        "signal_results": [item.model_dump() for item in referee_result.signal_results],
        "missed_expectations": [item.model_dump() for item in referee_result.missed_expectations],
        "invitation_results": [item.model_dump() for item in referee_result.invitation_results],
        "competition_outcomes": [item.model_dump() for item in referee_result.competition_outcomes],
        "next_tension": referee_result.next_tension,
        "replay_url": f"/simulations/{simulation.id}/scenes/{scene_run.id}",
    }
    return SceneRuntimeExecution(
        input_summary=input_summary,
        orchestrator_plan=plan,
        orchestrator_raw=plan.model_dump(),
        messages=transcript,
        referee_result=referee_result,
        referee_raw=referee_result.model_dump(),
        replay_payload=replay_payload,
    )



def apply_scene_runtime_result(
    db: Session,
    scene_run: SceneRun,
    simulation: SimulationRun,
    execution: SceneRuntimeExecution,
) -> None:
    participants = get_simulation_participants(db, simulation)
    participant_lookup = {item.id: item for item in participants}
    relationship_stmt = select(RelationshipState).where(
        RelationshipState.simulation_run_id == simulation.id
    )
    relationships = {
        (item.source_participant_id, item.target_participant_id): item
        for item in db.scalars(relationship_stmt).all()
    }

    for delta in execution.referee_result.relationship_deltas:
        relationship = relationships.get((delta.source_participant_id, delta.target_participant_id))
        if relationship is None:
            continue
        metrics = dict(relationship.metrics)
        for key, value in delta.changes.items():
            metrics[key] = clamp(metrics.get(key, 0) + value, 0, 100)
        relationship.metrics = metrics
        relationship.status = derive_relationship_status(metrics)
        relationship.recent_trend = derive_recent_trend(delta.changes)
        relationship.notes = [delta.reason] + relationship.notes[:4]
        relationship.last_event_tags = delta.event_tags
        relationship.updated_by_scene_run_id = scene_run.id
        db.add(relationship)

    persist_scene_memories(
        db,
        simulation.id,
        scene_run.id,
        participant_lookup,
        execution.referee_result,
    )
    persist_scene_event_links(
        db,
        simulation.id,
        scene_run.id,
        execution.referee_result.major_events,
    )
    update_participant_soul_state(participant_lookup, execution.referee_result, scene_run.scene_code)

    scene_run.status = "completed"
    scene_run.summary = execution.referee_result.scene_summary
    scene_run.director_output = {
        "scene_orchestrator_plan": execution.orchestrator_plan.model_dump(),
        "scene_referee_result": execution.referee_result.model_dump(),
    }
    scene_run.finished_at = datetime.now(timezone.utc)
    db.add(scene_run)

    snapshot_payload = {
        "scene_id": scene_run.scene_code,
        "participants": [
            {
                "participant_id": item.id,
                "name": item.name,
                "cast_role": item.cast_role,
                "editable_personality": item.editable_personality,
            }
            for item in participants
        ],
        "relationships": [
            {
                "source_participant_id": source_id,
                "source_name": participant_lookup[source_id].name,
                "target_participant_id": target_id,
                "target_name": participant_lookup[target_id].name,
                "status": relationship.status,
                "recent_trend": relationship.recent_trend,
                "metrics": relationship.metrics,
                "notes": relationship.notes,
                "last_event_tags": relationship.last_event_tags,
            }
            for (source_id, target_id), relationship in relationships.items()
            if source_id in participant_lookup and target_id in participant_lookup
        ],
    }
    db.add(
        StateSnapshot(
            simulation_run_id=simulation.id,
            scene_run_id=scene_run.id,
            snapshot=snapshot_payload,
        )
    )

    replace_scene_artifact(
        db,
        simulation.id,
        scene_run.id,
        "scene_referee_result",
        execution.referee_result.model_dump(),
        commit=False,
    )
    replace_scene_artifact(
        db,
        simulation.id,
        scene_run.id,
        "scene_replay_dto",
        execution.replay_payload,
        commit=False,
    )

    for audit_log in [
        AuditLog(
            simulation_run_id=simulation.id,
            scene_run_id=scene_run.id,
            log_type="participant_agent_outputs",
            payload={"messages": [message.model_dump() for message in execution.messages]},
        ),
        AuditLog(
            simulation_run_id=simulation.id,
            scene_run_id=scene_run.id,
            log_type="scene_referee_result",
            payload=execution.referee_result.model_dump(),
        ),
        AuditLog(
            simulation_run_id=simulation.id,
            scene_run_id=scene_run.id,
            log_type="applied_state_changes",
            payload={
                "relationship_deltas": [
                    item.model_dump() for item in execution.referee_result.relationship_deltas
                ]
            },
        ),
    ]:
        db.add(audit_log)

    simulation.latest_scene_summary = execution.referee_result.scene_summary
    simulation.latest_audit_snippet = execution.referee_result.next_tension
    advance_simulation_after_scene(db, simulation, scene_run)
    db.add(simulation)
    db.commit()


def build_scene_context(db: Session, simulation: SimulationRun, scene_code: str) -> dict:
    participants = get_simulation_participants(db, simulation)
    override_lookup = {
        row.participant_id: row.override_data
        for row in db.scalars(
            select(ParticipantPersonalityOverride).where(
                ParticipantPersonalityOverride.simulation_run_id == simulation.id
            )
        ).all()
    }
    participants = [
        apply_runtime_personality_override(participant, override_lookup.get(participant.id))
        for participant in participants
    ]
    relationship_map = {
        (item.source_participant_id, item.target_participant_id): item
        for item in db.scalars(
            select(RelationshipState).where(RelationshipState.simulation_run_id == simulation.id)
        ).all()
    }
    memory_rows = list(
        db.scalars(
            select(ParticipantSceneMemory)
            .where(ParticipantSceneMemory.simulation_run_id == simulation.id)
            .order_by(ParticipantSceneMemory.created_at.desc())
        ).all()
    )
    selected_participants = select_scene_participants(scene_code, participants, relationship_map)
    memory_lookup: dict[str, list[ParticipantSceneMemory]] = defaultdict(list)
    for row in memory_rows:
        memory_lookup[row.participant_id].append(row)

    return {
        "scene_id": scene_code,
        "simulation_id": simulation.id,
        "project_id": simulation.project_id,
        "strategy_cards": simulation.strategy_cards,
        "participants": selected_participants,
        "participant_lookup": {item.id: item for item in selected_participants},
        "all_participants": participants,
        "relationship_map": relationship_map,
        "memory_lookup": memory_lookup,
    }


def apply_runtime_personality_override(
    participant: ParticipantProfile,
    override_data: dict | None,
) -> ParticipantProfile:
    if not override_data:
        return participant
    participant_copy = copy(participant)
    participant_copy.editable_personality = override_data
    participant_copy.attachment_style = override_data.get(
        "attachment_style",
        participant.attachment_style,
    )
    participant_copy.commitment_goal = override_data.get(
        "commitment_goal",
        participant.commitment_goal,
    )
    return participant_copy


def select_scene_participants(
    scene_code: str,
    participants: list[ParticipantProfile],
    relationship_map: dict[tuple[str, str], RelationshipState],
) -> list[ParticipantProfile]:
    if scene_code in {SCENE_03_CODE, SCENE_04_CODE, SCENE_05_CODE, SCENE_06_CODE, SCENE_07_CODE}:
        return participants
    if scene_code == SCENE_01_CODE or len(participants) <= 4:
        return participants[:5]

    scored = []
    for participant in participants:
        edge_score = 0
        for other in participants:
            if participant.id == other.id:
                continue
            forward = relationship_map.get((participant.id, other.id))
            backward = relationship_map.get((other.id, participant.id))
            if forward is not None:
                edge_score += forward.metrics.get("curiosity", 0) + forward.metrics.get("attraction", 0)
            if backward is not None:
                edge_score += backward.metrics.get("curiosity", 0)
        scored.append((edge_score, participant))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored[:4]]


def build_input_summary(context: dict) -> dict:
    payload = {
        "scene_id": context["scene_id"],
        "scene_level": SCENE_CONFIG[context["scene_id"]].get("scene_level"),
        "simulation_id": context["simulation_id"],
        "project_id": context["project_id"],
        "strategy_cards": context["strategy_cards"],
        "participants": [
            {
                "participant_id": item.id,
                "name": item.name,
                "cast_role": item.cast_role,
            }
            for item in context["participants"]
        ],
    }
    if context["scene_id"] == SCENE_03_CODE:
        payload["candidate_pool_size"] = len(context["participants"])
        payload["interest_targets"] = {
            participant.id: build_scene_03_interest_target(context, participant.id)
            for participant in context["participants"]
        }
    if context["scene_id"] == SCENE_04_CODE:
        payload["competition_seed_pairs"] = build_scene_04_competition_seed_pairs(context)
    if context["scene_id"] == SCENE_05_CODE:
        payload["selection_seed"] = build_scene_05_seed(context)
    if context["scene_id"] == SCENE_06_CODE:
        payload["signal_seed"] = build_scene_06_seed(context)
    if context["scene_id"] == SCENE_07_CODE:
        payload["invitation_seed"] = build_scene_07_invitation_seed(context)
    return payload


def build_scene_orchestrator_plan(context: dict) -> SceneOrchestratorPlan:
    config = SCENE_CONFIG[context["scene_id"]]
    participants = context["participants"]
    return SceneOrchestratorPlan(
        scene_id=context["scene_id"],
        scene_goal=config["scene_goal"],
        scene_frame=config["scene_frame"],
        scene_level=config.get("scene_level"),
        participants=[
            PlanParticipant(
                participant_id=item.id,
                name=item.name,
                cast_role=item.cast_role,
            )
            for item in participants
        ],
        min_turns=config["min_turns"],
        max_turns=min(config["max_turns"], PHASE3_SCENE_REGISTRY[context["scene_id"]]["max_turns"]),
        planned_rounds=config["planned_rounds"],
        active_tension=build_active_tension(context),
        stop_condition=build_stop_condition(context["scene_id"]),
        scheduler_notes=[
            "优先让被点名、被忽略和刚制造 tension 的人获得回应机会。",
            "禁止单一角色连续霸屏超过 2 次。",
            "鼓励非中心角色之间直接互动，而不是都只对同一个人说话。",
        ],
        phase_outline=config["phase_outline"],
        participant_directives=[
            {
                "participant_id": item.id,
                "directive": build_participant_directive(item, context["scene_id"]),
            }
            for item in participants
        ],
    )


def build_active_tension(context: dict) -> str:
    if context["scene_id"] == SCENE_01_CODE:
        return "第一轮好感正在形成，但谁会主动继续接话、谁更像在观察别人，马上会影响下一场自由交流的站位。"
    if context["scene_id"] == SCENE_03_CODE:
        return "随机配对会打破最初期待：有人会意外升温，也有人会因没匹到在意对象而焦虑上升。"
    if context["scene_id"] == SCENE_04_CODE:
        return "随机约会后的关系被放回全员晚餐场，公开注意力与旁观解读会迅速放大竞争感和安全感差异。"
    if context["scene_id"] == SCENE_05_CODE:
        return "每个人都要主动选 1 人交流，互选会升温，错位与落空会放大不安并重排关系方向。"
    if context["scene_id"] == SCENE_06_CODE:
        return "每位参与者都将发送私密信号，期待落空与误判会直接影响谁敢在下一场主动邀约。"
    if context["scene_id"] == SCENE_07_CODE:
        return "每个人都要把信号转成主动邀约，竞争与被拒会快速拉开心理和关系分层。"
    return "表面舒服和真正被理解正在分化，有人会继续靠近，也有人会因为多人气氛开始误读彼此。"


def build_stop_condition(scene_id: str) -> str:
    if scene_id == SCENE_01_CODE:
        return "至少完成 2 轮有效互动，并出现 2 次交叉追问和 1 次非中心角色被注意到。"
    if scene_id == SCENE_03_CODE:
        return "所有随机 1v1 约会（含可能的轮空观察位）都完成并产出配对级结果。"
    if scene_id == SCENE_04_CODE:
        return "至少完成 2 轮以上多人晚餐互动，并形成注意力偏移、竞争信号和观察者视角。"
    if scene_id == SCENE_05_CODE:
        return "每位参与者完成一次主动选择并至少形成一轮针对性交流，输出互选/单选/错位结果。"
    if scene_id == SCENE_06_CODE:
        return "每位参与者至少完成一条私密信号发送，并输出接收结果与期待落空结果。"
    if scene_id == SCENE_07_CODE:
        return "所有参与者完成主动邀约并解析竞争、拒绝、fallback 或退场结果。"
    return "至少完成 2 轮以上多人对话，并形成下一场可能的靠近、误会或竞争张力。"


def build_participant_directive(participant: ParticipantProfile, scene_id: str) -> str:
    personality = participant.editable_personality or {}
    if scene_id == SCENE_01_CODE:
        if personality.get("initiative", 50) >= 65:
            return "主动接话，但不要抢成独角戏，尽量把别人拉进同一个话题。"
        if personality.get("emotional_openness", 50) <= 40:
            return "保持克制，先通过观察和短句试探别人。"
        return "在自然接话中展示个性，并判断谁值得下一场继续聊。"
    if scene_id == SCENE_03_CODE:
        if personality.get("initiative", 50) >= 65:
            return "在随机约会里主动发起一个具体问题，但不要把一次聊得来等同于确定对象。"
        if personality.get("emotional_openness", 50) <= 40:
            return "先用安全话题试探，再决定是否暴露真实偏好。"
        return "在随机 1v1 中验证真实吸引，记录这次连接是否值得下一层继续观察。"
    if scene_id == SCENE_04_CODE:
        if personality.get("self_esteem_stability", 50) >= 65:
            return "在多人晚餐里保持稳定表达，既回应目标对象也留给旁观者可读信号。"
        if personality.get("initiative", 50) >= 65:
            return "主动发言并观察竞争线变化，避免把公开偏好释放推成失控对位。"
        return "先观察注意力分布，再在关键节点介入，避免完全边缘化。"
    if scene_id == SCENE_05_CODE:
        if personality.get("initiative", 50) >= 65:
            return "尽快给出主动选择，并在交流里验证是否值得继续推进。"
        if personality.get("emotional_openness", 50) <= 40:
            return "先给出谨慎选择，再通过短交流确认安全感和被理解感。"
        return "在一次明确选择里表达真实倾向，同时识别互选或错位信号。"
    if scene_id == SCENE_06_CODE:
        if personality.get("initiative", 50) >= 65 and personality.get("emotional_openness", 50) >= 60:
            return "给出一条更明确的私密信号，并准备承受未获回流时的情绪波动。"
        if personality.get("self_esteem_stability", 50) <= 45:
            return "用更保守的表达保护自我形象，同时避免把期待拉到过高。"
        return "完成至少一条私密表达，并在揭示后重新校准期待与信任。"
    if scene_id == SCENE_07_CODE:
        if personality.get("initiative", 50) >= 68:
            return "优先主动发起邀约，并在竞争时保持清晰立场。"
        if personality.get("self_esteem_stability", 50) <= 45:
            return "若首邀受挫，谨慎评估 fallback 或退场，避免失控对位。"
        return "把私密信号转成可执行邀约，并在被拒后保持策略弹性。"
    if personality.get("emotional_openness", 50) >= 60:
        return "把话题推进到更具体的关系看法，同时留意谁真的在认真回应。"
    return "先接住他人的深一点话题，再决定是否暴露更多真实偏好。"


def choose_next_speaker(
    context: dict,
    plan: SceneOrchestratorPlan,
    transcript: list[AgentTurnPayload],
) -> str | None:
    participants = context["participants"]
    if not participants:
        return None
    counts = defaultdict(int)
    for turn in transcript:
        counts[turn.speaker_participant_id] += 1

    last_turn = transcript[-1] if transcript else None
    min_count = min(counts.get(item.id, 0) for item in participants) if transcript else 0
    best_id = None
    best_score = -10**9
    for participant in participants:
        personality = participant.editable_personality or {}
        score = 10
        score += int(personality.get("initiative", 50)) / 12
        score += int(personality.get("extroversion", 50)) / 15
        score -= counts.get(participant.id, 0) * 3
        if counts.get(participant.id, 0) == min_count:
            score += 5
        if last_turn:
            if participant.id in last_turn.target_participant_ids:
                score += 8
            if participant.id in last_turn.next_speaker_suggestions:
                score += 4
            if last_turn.speaker_participant_id == participant.id:
                score -= 9
                if len(transcript) >= 2 and transcript[-2].speaker_participant_id == participant.id:
                    score -= 20
        if not transcript:
            score += int(personality.get("initiative", 50)) / 6
        if context["scene_id"] == SCENE_04_CODE:
            score += apply_scene_04_strategy_bias(context, participant, counts, last_turn)
        best_score = max(best_score, score)
        if score == best_score:
            best_id = participant.id
    return best_id


def build_agent_input(
    context: dict,
    plan: SceneOrchestratorPlan,
    transcript: list[AgentTurnPayload],
    turn_index: int,
    speaker_id: str,
) -> dict:
    speaker = context["participant_lookup"][speaker_id]
    outgoing_relationships = []
    incoming_relationships = []
    for participant in context["participants"]:
        if participant.id == speaker_id:
            continue
        forward = context["relationship_map"].get((speaker_id, participant.id))
        backward = context["relationship_map"].get((participant.id, speaker_id))
        outgoing_relationships.append(
            {
                "participant_id": participant.id,
                "name": participant.name,
                "metrics": forward.metrics if forward else {},
                "status": forward.status if forward else "observing",
            }
        )
        incoming_relationships.append(
            {
                "participant_id": participant.id,
                "name": participant.name,
                "metrics": backward.metrics if backward else {},
                "status": backward.status if backward else "observing",
            }
        )

    return {
        "scene_id": context["scene_id"],
        "turn_index": turn_index,
        "speaker": {
            "participant_id": speaker.id,
            "name": speaker.name,
            "cast_role": speaker.cast_role,
            "background_summary": speaker.background_summary,
            "personality_summary": speaker.personality_summary,
            "editable_personality": speaker.editable_personality,
        },
        "scene_goal": plan.scene_goal,
        "active_tension": plan.active_tension,
        "strategy_cards": context["strategy_cards"],
        "scene_04_focus_target": build_scene_04_focus_target(context, speaker_id)
        if context["scene_id"] == SCENE_04_CODE
        else None,
        "recent_transcript": [item.model_dump() for item in transcript[-5:]],
        "outgoing_relationships": outgoing_relationships,
        "incoming_relationships": incoming_relationships,
        "recent_memories": [
            {
                "summary": memory.summary,
                "event_tags": memory.event_tags,
            }
            for memory in context["memory_lookup"].get(speaker.id, [])[:3]
        ],
        "other_participants": [
            {
                "participant_id": item.id,
                "name": item.name,
                "cast_role": item.cast_role,
                "personality_summary": item.personality_summary,
            }
            for item in context["participants"]
            if item.id != speaker.id
        ],
    }


def generate_agent_turn(
    context: dict,
    plan: SceneOrchestratorPlan,
    transcript: list[AgentTurnPayload],
    turn_index: int,
    speaker_id: str,
    input_payload: dict,
) -> tuple[AgentTurnPayload, dict | str, dict]:
    settings = get_settings()
    if settings.director_provider_mode == "mock" or (
        settings.director_provider_mode == "auto" and not settings.dashscope_api_key
    ):
        turn = build_mock_turn(context, transcript, turn_index, speaker_id)
        return turn, turn.model_dump(), input_payload
    if turn_index > 2:
        turn = build_mock_turn(context, transcript, turn_index, speaker_id)
        return turn, {"fallback": "deterministic_tail_after_live_opening", **turn.model_dump()}, input_payload

    try:
        raw_payload = call_json_llm(TURN_SYSTEM_PROMPT, input_payload)
        normalized = normalize_turn_payload(raw_payload, context, transcript, turn_index, speaker_id)
        return AgentTurnPayload.model_validate(normalized), raw_payload, input_payload
    except Exception:  # noqa: BLE001
        turn = build_mock_turn(context, transcript, turn_index, speaker_id)
        return turn, {"fallback": "mock_turn_after_live_failure", **turn.model_dump()}, input_payload


def build_mock_turn(
    context: dict,
    transcript: list[AgentTurnPayload],
    turn_index: int,
    speaker_id: str,
) -> AgentTurnPayload:
    speaker = context["participant_lookup"][speaker_id]
    targets = [item.id for item in context["participants"] if item.id != speaker_id]
    target_id = targets[turn_index % len(targets)] if targets else speaker_id
    target_name = context["participant_lookup"].get(target_id, speaker).name
    round_index = 1 + math.floor((turn_index - 1) / max(1, len(context["participants"]) - 1))
    last_turn = transcript[-1] if transcript else None
    addressed_from_turn_id = f"turn_{last_turn.turn_index:04d}" if last_turn else None

    if context["scene_id"] == SCENE_01_CODE:
        utterance = (
            f"我是{speaker.name}，刚才听到你提到通勤和节目节奏，"
            f"{target_name} 你会更在意一个人是不是先让现场轻松起来吗？"
        )
        intent_tags = ["break_ice", "probe_depth"]
        topic_tags = ["first_impression", "commute", "group_energy"]
    elif context["scene_id"] == SCENE_04_CODE:
        utterance = (
            f"在这种多人晚餐里我更在意谁会把回应说具体。"
            f"{target_name}，你刚才那句更像真心还是礼貌？"
        )
        intent_tags = ["signal_interest", "invite_group"]
        topic_tags = ["group_dinner", "attention_shift", "competition_signal"]
    else:
        utterance = (
            f"如果真的要在这里继续了解一个人，我会更在意对方有没有把话听进去。"
            f"{target_name}，你会更看重舒服还是更看重来电？"
        )
        intent_tags = ["probe_depth", "signal_interest"]
        topic_tags = ["comfort", "understanding", "relationship_goal"]

    if turn_index % 3 == 0 and len(targets) > 1:
        target_id = targets[(turn_index + 1) % len(targets)]
        target_name = context["participant_lookup"][target_id].name
        utterance = utterance.replace("你会", f"{target_name}，你会")
        if context["scene_id"] == SCENE_04_CODE:
            intent_tags = ["protect_self_image", "invite_group"]
            topic_tags = ["group_dinner", "observer_reaction", "competition_signal"]
        else:
            intent_tags = ["build_comfort", "invite_group"]

    return AgentTurnPayload(
        speaker_participant_id=speaker_id,
        speaker_name=speaker.name,
        turn_index=turn_index,
        round_index=round_index,
        utterance=utterance,
        behavior_summary="语气自然，带一点试探，同时给别人留下接话空间。",
        intent_tags=intent_tags,
        target_participant_ids=[target_id] if target_id != speaker_id else [],
        addressed_from_turn_id=addressed_from_turn_id,
        topic_tags=topic_tags,
        next_speaker_suggestions=[target_id] if target_id != speaker_id else [],
        self_observation="我在看谁会认真接这一步，而不是只给礼貌回应。",
    )


def normalize_turn_payload(
    raw_payload: dict | str,
    context: dict,
    transcript: list[AgentTurnPayload],
    turn_index: int,
    speaker_id: str,
) -> dict:
    if isinstance(raw_payload, str):
        try:
            payload = json.loads(extract_json_block(raw_payload))
        except json.JSONDecodeError:
            payload = {}
    else:
        payload = raw_payload

    fallback = build_mock_turn(context, transcript, turn_index, speaker_id).model_dump()
    participant_lookup = context["participant_lookup"]

    target_ids = [
        item
        for item in payload.get("target_participant_ids", fallback["target_participant_ids"])
        if item in participant_lookup and item != speaker_id
    ]
    next_ids = [
        item
        for item in payload.get("next_speaker_suggestions", fallback["next_speaker_suggestions"])
        if item in participant_lookup and item != speaker_id
    ]
    intent_tags = [
        tag
        for tag in payload.get("intent_tags", fallback["intent_tags"])
        if tag in ALLOWED_INTENT_TAGS
    ][:3]

    return {
        "speaker_participant_id": speaker_id,
        "speaker_name": participant_lookup[speaker_id].name,
        "turn_index": turn_index,
        "round_index": payload.get("round_index") or fallback["round_index"],
        "utterance": str(payload.get("utterance") or fallback["utterance"])[:240],
        "behavior_summary": str(payload.get("behavior_summary") or fallback["behavior_summary"])[:160],
        "intent_tags": intent_tags or fallback["intent_tags"],
        "target_participant_ids": target_ids or fallback["target_participant_ids"],
        "addressed_from_turn_id": payload.get("addressed_from_turn_id") or fallback["addressed_from_turn_id"],
        "topic_tags": payload.get("topic_tags", fallback["topic_tags"])[:4],
        "next_speaker_suggestions": next_ids or fallback["next_speaker_suggestions"],
        "self_observation": str(payload.get("self_observation") or fallback["self_observation"])[:180],
    }


def should_stop_scene(
    context: dict,
    plan: SceneOrchestratorPlan,
    transcript: list[AgentTurnPayload],
) -> bool:
    if len(transcript) >= plan.max_turns:
        return True
    if len(transcript) < plan.min_turns:
        return False

    unique_speakers = {item.speaker_participant_id for item in transcript}
    cross_talk_count = sum(1 for item in transcript if item.addressed_from_turn_id)
    non_center_interactions = 0
    if transcript:
        first_speaker = transcript[0].speaker_participant_id
        for item in transcript[1:]:
            if item.target_participant_ids and any(target != first_speaker for target in item.target_participant_ids):
                non_center_interactions += 1

    return (
        len(unique_speakers) >= min(3, len(context["participants"]))
        and cross_talk_count >= 2
        and non_center_interactions >= 1
    )


def build_referee_result(
    context: dict,
    plan: SceneOrchestratorPlan,
    transcript: list[AgentTurnPayload],
) -> SceneRefereeResult:
    delta_map: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    reason_map: dict[tuple[str, str], list[str]] = defaultdict(list)
    event_tag_map: dict[tuple[str, str], set[str]] = defaultdict(set)
    major_events: list[SceneEvent] = []
    participant_memory_updates = []
    competition_map: list[SceneCompetitionMapItem] = []

    first_speaker = transcript[0].speaker_participant_id if transcript else None
    for turn in transcript:
        targets = turn.target_participant_ids or []
        if not targets:
            continue
        primary_target = targets[0]
        changes = impact_from_intent_tags(turn.intent_tags, context["scene_id"])
        if context["scene_id"] == SCENE_04_CODE:
            changes = apply_scene_04_turn_strategy_bias(context, turn, changes)
        merge_changes(delta_map[(turn.speaker_participant_id, primary_target)], changes)
        event_tag_map[(turn.speaker_participant_id, primary_target)].update(turn.intent_tags)
        reason_map[(turn.speaker_participant_id, primary_target)].append(turn.utterance)

        reciprocal = reciprocal_changes(changes)
        merge_changes(delta_map[(primary_target, turn.speaker_participant_id)], reciprocal)
        event_tag_map[(primary_target, turn.speaker_participant_id)].update(turn.intent_tags)
        reason_map[(primary_target, turn.speaker_participant_id)].append(
            f"{turn.speaker_name} 把注意力集中到这段互动上。"
        )

        if primary_target != first_speaker:
            for observer in context["participants"]:
                if observer.id in {turn.speaker_participant_id, primary_target}:
                    continue
                merge_changes(
                    delta_map[(observer.id, primary_target)],
                    {
                        "curiosity": 1,
                        "anxiety": 1 if "signal_interest" in turn.intent_tags else 0,
                        "competition_sense": 2 if context["scene_id"] == SCENE_04_CODE and "signal_interest" in turn.intent_tags else 0,
                    },
                )
                event_tag_map[(observer.id, primary_target)].add("indirect_observation")
                reason_map[(observer.id, primary_target)].append(
                    f"{observer.name} 在旁观中注意到 {turn.speaker_name} 对 {context['participant_lookup'][primary_target].name} 的动作。"
                )

        major_events.append(
            SceneEvent(
                title=f"{turn.speaker_name} 发起了新的互动段落",
                description=turn.utterance,
                event_tags=turn.intent_tags,
                source_participant_id=turn.speaker_participant_id,
                target_participant_ids=targets,
                linked_turn_indices=[turn.turn_index],
            )
        )

    relationship_deltas = []
    for (source_id, target_id), changes in delta_map.items():
        normalized_changes = {
            key: clamp(value, -18, 18)
            for key, value in changes.items()
            if value != 0
        }
        if not normalized_changes:
            continue
        relationship_deltas.append(
            SceneRelationshipDelta(
                source_participant_id=source_id,
                target_participant_id=target_id,
                changes=normalized_changes,
                reason="；".join(reason_map[(source_id, target_id)][:2]),
                event_tags=sorted(event_tag_map[(source_id, target_id)]),
            )
        )

    if context["scene_id"] == SCENE_04_CODE:
        competition_map = derive_scene_04_competition_map(context, transcript, relationship_deltas)
        for item in competition_map:
            relationship_deltas.append(
                SceneRelationshipDelta(
                    source_participant_id=item.source_participant_id,
                    target_participant_id=item.target_participant_id,
                    changes={
                        "competition_sense": clamp(max(1, int(round(item.competition_sense / 12))), -18, 18),
                        "anxiety": clamp(max(0, int(round(item.competition_sense / 24))), -18, 18),
                    },
                    reason=item.reason,
                    event_tags=item.event_tags,
                )
            )

    for participant in context["participants"]:
        participant_related = [
            delta
            for delta in relationship_deltas
            if delta.source_participant_id == participant.id or delta.target_participant_id == participant.id
        ]
        participant_related.sort(
            key=lambda item: sum(abs(value) for value in item.changes.values()),
            reverse=True,
        )
        top_delta = participant_related[0] if participant_related else None
        if top_delta:
            target_id = (
                top_delta.target_participant_id
                if top_delta.source_participant_id == participant.id
                else top_delta.source_participant_id
            )
            target_name = context["participant_lookup"].get(target_id, participant).name
            participant_memory_updates.append(
                {
                    "participant_id": participant.id,
                    "memory_type": "scene_takeaway",
                    "target_participant_ids": [target_id],
                    "summary": f"{participant.name} 这场最在意与 {target_name} 的互动变化。",
                    "importance": clamp(
                        40 + sum(abs(value) for value in top_delta.changes.values()),
                        35,
                        90,
                    ),
                    "event_tags": top_delta.event_tags,
                }
            )

    scene_summary = summarize_scene(context, transcript, relationship_deltas, competition_map)
    next_tension = build_next_tension(context, transcript, relationship_deltas, competition_map)
    major_events = major_events[:6]
    return SceneRefereeResult(
        scene_id=context["scene_id"],
        scene_summary=scene_summary,
        major_events=major_events,
        relationship_deltas=relationship_deltas,
        competition_map=competition_map,
        selection_results=[],
        signal_results=[],
        missed_expectations=[],
        invitation_results=[],
        competition_outcomes=[],
        participant_memory_updates=participant_memory_updates,
        next_tension=next_tension,
    )


def impact_from_intent_tags(intent_tags: list[str], scene_id: str) -> dict[str, int]:
    multiplier = 0.8 if scene_id == SCENE_01_CODE else 1.0
    changes = defaultdict(int)
    for tag in intent_tags:
        if tag == "signal_interest":
            merge_changes(changes, scale_changes({"attraction": 6, "curiosity": 5, "expectation": 4}, multiplier))
        elif tag == "build_comfort":
            merge_changes(changes, scale_changes({"comfort": 6, "trust": 4, "anxiety": -3}, multiplier))
        elif tag == "probe_depth":
            merge_changes(changes, scale_changes({"understood": 5, "curiosity": 4}, multiplier))
        elif tag == "show_stability":
            merge_changes(changes, scale_changes({"trust": 5, "comfort": 3, "anxiety": -2}, multiplier))
        elif tag == "show_humor":
            merge_changes(changes, scale_changes({"comfort": 4, "curiosity": 3}, multiplier))
        elif tag == "test_chemistry":
            merge_changes(changes, scale_changes({"attraction": 4, "anxiety": 2, "curiosity": 4}, multiplier))
        elif tag == "tease_lightly":
            merge_changes(changes, scale_changes({"comfort": 2, "anxiety": 1}, multiplier))
        elif tag == "protect_self_image":
            merge_changes(changes, scale_changes({"comfort": -2, "anxiety": 3}, multiplier))
        elif tag == "invite_group":
            merge_changes(changes, scale_changes({"comfort": 3, "understood": 2}, multiplier))
    if scene_id == SCENE_04_CODE:
        if "signal_interest" in intent_tags:
            merge_changes(changes, {"competition_sense": 3, "anxiety": 1})
        if "build_comfort" in intent_tags or "show_stability" in intent_tags:
            merge_changes(changes, {"trust": 2, "anxiety": -1})
        if "protect_self_image" in intent_tags:
            merge_changes(changes, {"conflict": 2, "anxiety": 2})
    return dict(changes)


def reciprocal_changes(changes: dict[str, int]) -> dict[str, int]:
    reciprocal = {}
    for key, value in changes.items():
        if value > 0:
            reciprocal[key] = max(1, value // 2)
        elif value < 0:
            reciprocal[key] = min(-1, value // 2)
    return reciprocal


def scale_changes(changes: dict[str, int], multiplier: float) -> dict[str, int]:
    return {key: int(round(value * multiplier)) for key, value in changes.items()}


def merge_changes(target: dict[str, int], updates: dict[str, int]) -> None:
    for key, value in updates.items():
        target[key] = target.get(key, 0) + value


def summarize_scene(
    context: dict,
    transcript: list[AgentTurnPayload],
    relationship_deltas: list[SceneRelationshipDelta],
    competition_map: list[SceneCompetitionMapItem] | None = None,
) -> str:
    if not transcript:
        return "本场还没有形成足够的多人互动。"
    if context["scene_id"] == SCENE_04_CODE:
        if competition_map:
            top_item = max(competition_map, key=lambda item: item.competition_sense)
            source_name = context["participant_lookup"].get(top_item.source_participant_id)
            target_name = context["participant_lookup"].get(top_item.target_participant_id)
            focus_name = context["participant_lookup"].get(top_item.focus_participant_id) if top_item.focus_participant_id else None
            source_text = source_name.name if source_name else top_item.source_participant_id
            target_text = target_name.name if target_name else top_item.target_participant_id
            focus_text = focus_name.name if focus_name else "同一目标"
            return (
                f"多人晚餐把随机约会后的信号拉回公开场，{source_text} 与 {target_text} 因 {focus_text} 形成了最明显竞争，"
                "场内稳定度与焦虑分化已开始影响下一场主动选择。"
            )
        return "多人晚餐已形成注意力偏移和观察者再判断，但竞争关系尚未完全拉开。"
    strongest = sorted(
        relationship_deltas,
        key=lambda item: sum(abs(value) for value in item.changes.values()),
        reverse=True,
    )[:2]
    if strongest:
        top_line = []
        for item in strongest:
            source_name = context["participant_lookup"][item.source_participant_id].name
            target_name = context["participant_lookup"][item.target_participant_id].name
            top_line.append(f"{source_name} -> {target_name}")
        return f"本场形成了更清晰的多人关系偏置，最明显的变化集中在 {'、'.join(top_line)}。"
    return "本场完成了至少两轮多人互动，新的好感和误读已经开始浮现。"


def build_next_tension(
    context: dict,
    transcript: list[AgentTurnPayload],
    relationship_deltas: list[SceneRelationshipDelta],
    competition_map: list[SceneCompetitionMapItem] | None = None,
) -> str:
    if context["scene_id"] == SCENE_01_CODE:
        return "下一场自由交流里，谁会继续追问、谁会只停在礼貌互动，将开始分出真正聊得来的人。"
    if context["scene_id"] == SCENE_03_CODE:
        return "进入 scene_04_group_dinner 后，随机约会里意外升温的线会被多人竞争放大；到 scene_05_conversation_choosing 时，谁会主动继续聊将被重新检验。"
    if context["scene_id"] == SCENE_04_CODE:
        if competition_map:
            top_item = max(competition_map, key=lambda item: item.competition_sense)
            source_name = context["participant_lookup"].get(top_item.source_participant_id)
            target_name = context["participant_lookup"].get(top_item.target_participant_id)
            source_text = source_name.name if source_name else top_item.source_participant_id
            target_text = target_name.name if target_name else top_item.target_participant_id
            return (
                f"scene_05_conversation_choosing 中，{source_text} 与 {target_text} 将在竞争余波里给出主动选择，"
                "晚餐里的公开信号会直接影响谁先迈出下一步。"
            )
        return "scene_05_conversation_choosing 将检验晚餐里形成的注意力偏移，谁会主动靠近、谁会因为焦虑而回避。"
    if context["scene_id"] == SCENE_06_CODE:
        return "scene_07_new_date 将把私密信号里的互相确认与期待落空转成主动邀约竞争，谁敢出手、谁会退缩将快速分化。"
    if context["scene_id"] == SCENE_07_CODE:
        return "scene_08_conflict_test 会检验邀约竞争后留下的关系线是否能扛住价值观冲突。"
    if not relationship_deltas:
        return "下一场张力仍然来自多人场里的误判与靠近。"
    hottest = max(
        relationship_deltas,
        key=lambda item: item.changes.get("expectation", 0) + item.changes.get("attraction", 0),
    )
    source_name = context["participant_lookup"].get(
        hottest.source_participant_id
    ).name if context["participant_lookup"].get(hottest.source_participant_id) else hottest.source_participant_id
    target_name = context["participant_lookup"].get(
        hottest.target_participant_id
    ).name if context["participant_lookup"].get(hottest.target_participant_id) else hottest.target_participant_id
    return (
        f"下一场最值得观察的是 {source_name} 和 {target_name} "
        "这条线会继续升温，还是因为多人环境开始错位。"
    )


def persist_scene_memories(
    db: Session,
    simulation_id: str,
    scene_run_id: str,
    participant_lookup: dict[str, ParticipantProfile],
    referee_result: SceneRefereeResult,
) -> None:
    for memory in referee_result.participant_memory_updates:
        if memory["participant_id"] not in participant_lookup:
            continue
        db.add(
            ParticipantSceneMemory(
                simulation_run_id=simulation_id,
                scene_run_id=scene_run_id,
                participant_id=memory["participant_id"],
                memory_type=memory["memory_type"],
                target_participant_ids=memory["target_participant_ids"],
                summary=memory["summary"],
                importance=memory["importance"],
                event_tags=memory["event_tags"],
            )
        )


def persist_scene_event_links(
    db: Session,
    simulation_id: str,
    scene_run_id: str,
    events: list[SceneEvent],
) -> None:
    for event in events:
        db.add(
            SceneEventLink(
                simulation_run_id=simulation_id,
                scene_run_id=scene_run_id,
                source_participant_id=event.source_participant_id,
                target_participant_ids=event.target_participant_ids,
                summary=event.description or event.title,
                event_tags=event.event_tags,
            )
        )


def update_participant_soul_state(
    participant_lookup: dict[str, ParticipantProfile],
    referee_result: SceneRefereeResult,
    scene_code: str,
) -> None:
    for participant_id, participant in participant_lookup.items():
        soul_data = dict(participant.soul_data or {})
        scene_memory = dict(soul_data.get("scene_memory", {}))
        completed_scenes = list(scene_memory.get("completed_scenes", []))
        if scene_code not in completed_scenes:
            completed_scenes.append(scene_code)
        scene_memory["completed_scenes"] = completed_scenes
        dynamic_state = dict(soul_data.get("dynamic_state", {}))
        dynamic_state["last_scene_summary"] = referee_result.scene_summary
        soul_data["scene_memory"] = scene_memory
        soul_data["dynamic_state"] = dynamic_state
        participant.soul_data = soul_data


def advance_simulation_after_scene(db: Session, simulation: SimulationRun, scene_run: SceneRun) -> None:
    next_scene = db.scalar(
        select(SceneRun).where(
            SceneRun.simulation_run_id == simulation.id,
            SceneRun.scene_index == scene_run.scene_index + 1,
        )
    )
    if next_scene is None:
        simulation.status = "completed"
        simulation.current_scene_index = scene_run.scene_index
        simulation.current_scene_code = scene_run.scene_code
        simulation.finished_at = datetime.now(timezone.utc)
        return

    next_scene.status = "queued"
    simulation.status = "running"
    simulation.current_scene_index = next_scene.scene_index
    simulation.current_scene_code = next_scene.scene_code
    simulation.finished_at = None
    db.add(next_scene)
    enqueue_scene(next_scene.id)


def persist_turn_records(
    db: Session,
    simulation_id: str,
    scene_run_id: str,
    started_at: datetime,
    turn: AgentTurnPayload,
    raw_output: dict | str,
    input_payload: dict,
) -> None:
    db.add(
        AgentTurn(
            simulation_run_id=simulation_id,
            scene_run_id=scene_run_id,
            turn_index=turn.turn_index,
            guest_id=turn.speaker_participant_id,
            agent_name=turn.speaker_name,
            status="completed",
            input_payload=input_payload,
            raw_output=raw_output if isinstance(raw_output, dict) else {"raw_text": raw_output},
            normalized_output=turn.model_dump(),
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
        )
    )
    db.add(
        SceneMessage(
            simulation_run_id=simulation_id,
            scene_run_id=scene_run_id,
            turn_index=turn.turn_index,
            speaker_guest_id=turn.speaker_participant_id,
            speaker_name=turn.speaker_name,
            message_role="agent",
            utterance=turn.utterance,
            behavior_summary=turn.behavior_summary,
            intent_tags=turn.intent_tags,
            target_guest_ids=turn.target_participant_ids,
            visible_context_summary=input_payload,
            raw_output=raw_output if isinstance(raw_output, dict) else {"raw_text": raw_output},
        )
    )
    db.commit()


def persist_plan_audit_logs(
    db: Session,
    simulation_id: str,
    scene_run_id: str,
    input_summary: dict,
    plan_payload: dict,
) -> None:
    for audit_log in [
        AuditLog(
            simulation_run_id=simulation_id,
            scene_run_id=scene_run_id,
            log_type="scene_input_summary",
            payload=input_summary,
        ),
        AuditLog(
            simulation_run_id=simulation_id,
            scene_run_id=scene_run_id,
            log_type="scene_orchestrator_plan",
            payload=plan_payload,
        ),
    ]:
        db.add(audit_log)
    db.commit()


def reset_scene_runtime_records(db: Session, scene_run_id: str) -> None:
    for model in [AgentTurn, SceneMessage, SceneArtifact, ParticipantSceneMemory, SceneEventLink]:
        if model in {ParticipantSceneMemory, SceneEventLink}:
            db.execute(delete(model).where(model.scene_run_id == scene_run_id))
        else:
            db.execute(delete(model).where(model.scene_run_id == scene_run_id))
    db.commit()


def replace_scene_artifact(
    db: Session,
    simulation_id: str,
    scene_run_id: str,
    artifact_type: str,
    payload: dict,
    *,
    commit: bool,
) -> None:
    existing = db.scalar(
        select(SceneArtifact).where(
            SceneArtifact.scene_run_id == scene_run_id,
            SceneArtifact.artifact_type == artifact_type,
        )
    )
    if existing is None:
        db.add(
            SceneArtifact(
                simulation_run_id=simulation_id,
                scene_run_id=scene_run_id,
                artifact_type=artifact_type,
                payload=payload,
            )
        )
    else:
        existing.payload = payload
        db.add(existing)
    if commit:
        db.commit()


def call_json_llm(system_prompt: str, payload: dict) -> dict | str:
    settings = get_settings()
    client = OpenAI(
        api_key=settings.dashscope_api_key,
        base_url=settings.dashscope_base_url,
        timeout=10.0,
    )
    completion = client.chat.completions.create(
        model=settings.director_model,
        temperature=0.9,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False),
            },
        ],
        response_format={"type": "json_object"},
    )
    message_content = completion.choices[0].message.content or "{}"
    try:
        return json.loads(extract_json_block(message_content))
    except json.JSONDecodeError:
        return message_content


def extract_json_block(text: str) -> str:
    match = re.search(r"\{.*\}", text, flags=re.S)
    return match.group(0) if match else text
