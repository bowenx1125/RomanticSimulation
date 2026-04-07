from __future__ import annotations

import hashlib
import random
from collections import defaultdict

from app.models import SceneRun, SimulationRun
from app.schemas.runtime import (
    SceneEvent,
    SceneOrchestratorPlan,
    SceneRefereeResult,
    SceneRelationshipDelta,
    SceneRuntimeExecution,
    SceneSelectionResult,
)
from app.services.simulation.scene_config import SCENE_CONFIG
from app.services.simulation.scene_registry import SCENE_05_CODE
from app.services.simulation.service import clamp


def execute_scene_05_runtime(
    simulation: SimulationRun,
    scene_run: SceneRun,
    context: dict,
    input_summary: dict,
    plan: SceneOrchestratorPlan,
) -> SceneRuntimeExecution:
    rng = build_scene_05_rng(simulation.id, scene_run.id)
    selection_plan = build_scene_05_selection_plan(context, rng)
    selection_results = resolve_scene_05_selection_outcomes(context, selection_plan)
    relationship_deltas = derive_scene_05_relationship_deltas(selection_results)
    major_events = summarize_scene_05_events(selection_results)
    scene_summary = summarize_scene_05_results(context, selection_results)
    next_tension = build_scene_05_next_tension(context, selection_results, relationship_deltas)
    memory_updates = derive_scene_05_participant_memories(context, relationship_deltas)

    referee_result = SceneRefereeResult(
        scene_id=SCENE_05_CODE,
        scene_summary=scene_summary,
        major_events=major_events,
        relationship_deltas=relationship_deltas,
        pair_date_results=[],
        competition_map=[],
        selection_results=selection_results,
        signal_results=[],
        missed_expectations=[],
        invitation_results=[],
        competition_outcomes=[],
        participant_memory_updates=memory_updates,
        next_tension=next_tension,
    )
    replay_payload = {
        "simulation_id": simulation.id,
        "scene_run_id": scene_run.id,
        "scene_code": scene_run.scene_code,
        "scene_index": scene_run.scene_index,
        "status": "completed",
        "summary": referee_result.scene_summary,
        "scene_plan": plan.model_dump(),
        "messages": [],
        "major_events": [event.model_dump() for event in referee_result.major_events],
        "relationship_deltas": [
            relationship_delta.model_dump()
            for relationship_delta in referee_result.relationship_deltas
        ],
        "pair_date_results": [item.model_dump() for item in referee_result.pair_date_results],
        "competition_map": [item.model_dump() for item in referee_result.competition_map],
        "selection_results": [item.model_dump() for item in referee_result.selection_results],
        "signal_results": [item.model_dump() for item in referee_result.signal_results],
        "missed_expectations": [item.model_dump() for item in referee_result.missed_expectations],
        "invitation_results": [item.model_dump() for item in referee_result.invitation_results],
        "competition_outcomes": [item.model_dump() for item in referee_result.competition_outcomes],
        "group_state_after_scene": {
            "dominant_topics": ["choice", "reciprocity", "mismatch"],
            "attention_distribution": [],
            "tension_pairs": [],
            "isolated_participants": [],
            "selection_plan": selection_plan,
            "scene_level": SCENE_CONFIG[SCENE_05_CODE]["scene_level"],
        },
        "next_tension": referee_result.next_tension,
        "replay_url": f"/simulations/{simulation.id}/scenes/{scene_run.id}",
    }
    return SceneRuntimeExecution(
        input_summary=input_summary,
        orchestrator_plan=plan,
        orchestrator_raw={
            **plan.model_dump(),
            "selection_plan": selection_plan,
        },
        messages=[],
        referee_result=referee_result,
        referee_raw={
            **referee_result.model_dump(),
            "selection_plan": selection_plan,
        },
        replay_payload=replay_payload,
    )


def build_scene_05_rng(simulation_id: str, scene_run_id: str) -> random.Random:
    seed_text = f"{simulation_id}:{scene_run_id}:{SCENE_05_CODE}"
    seed = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:16], 16)
    return random.Random(seed)


def build_scene_05_seed(context: dict) -> dict:
    return {
        participant.id: [
            item["target_participant_id"]
            for item in build_scene_05_candidate_scores(context, participant.id)[:2]
        ]
        for participant in context["participants"]
    }


def build_scene_05_candidate_scores(context: dict, selector_id: str) -> list[dict]:
    strategy_cards = set(context.get("strategy_cards", []))
    candidates = []
    for participant in context["participants"]:
        if participant.id == selector_id:
            continue
        forward = context["relationship_map"].get((selector_id, participant.id))
        backward = context["relationship_map"].get((participant.id, selector_id))
        forward_metrics = forward.metrics if forward else {}
        backward_metrics = backward.metrics if backward else {}

        attraction = forward_metrics.get("attraction", 0)
        trust = forward_metrics.get("trust", 0)
        curiosity = forward_metrics.get("curiosity", 0)
        understood = forward_metrics.get("understood", 0)
        incoming_interest = backward_metrics.get("attraction", 0) + backward_metrics.get("curiosity", 0)

        base_score = attraction * 1.1 + trust + curiosity * 0.8 + understood * 0.6
        strategy_used = "default_balanced"
        if "choose_by_emotion" in strategy_cards:
            base_score = attraction * 1.5 + curiosity + incoming_interest * 0.3
            strategy_used = "choose_by_emotion"
        elif "choose_by_stability" in strategy_cards:
            base_score = trust * 1.6 + understood + forward_metrics.get("comfort", 0) * 0.8
            strategy_used = "choose_by_stability"
        elif "test_uncertain_target" in strategy_cards:
            base_score = attraction * 1.2 + curiosity * 1.2 + max(0, 60 - trust)
            strategy_used = "test_uncertain_target"
        elif "wait_to_be_chosen" in strategy_cards:
            base_score = incoming_interest * 1.2 + trust * 0.8 + backward_metrics.get("trust", 0) * 0.6
            strategy_used = "wait_to_be_chosen"

        candidates.append(
            {
                "selector_participant_id": selector_id,
                "target_participant_id": participant.id,
                "score": base_score,
                "strategy_used": strategy_used,
            }
        )
    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates


def build_scene_05_selection_plan(context: dict, rng: random.Random) -> dict:
    choices = []
    for participant in context["participants"]:
        ranked = build_scene_05_candidate_scores(context, participant.id)
        if not ranked:
            continue
        top_slice = ranked[: min(2, len(ranked))]
        jittered = [item["score"] + rng.random() * 0.6 for item in top_slice]
        pick_index = 0 if jittered[0] >= max(jittered) else jittered.index(max(jittered))
        choice = top_slice[pick_index]
        target_id = choice["target_participant_id"]
        target_name = context["participant_lookup"][target_id].name
        choices.append(
            {
                "selector_participant_id": participant.id,
                "selected_target_participant_id": target_id,
                "strategy_used": choice["strategy_used"],
                "reason": f"{participant.name} 在当前关系图中更倾向选择 {target_name} 进行主动交流。",
            }
        )
    return {
        "scene_id": SCENE_05_CODE,
        "choices": choices,
    }


def resolve_scene_05_selection_outcomes(
    context: dict,
    selection_plan: dict,
) -> list[SceneSelectionResult]:
    choice_lookup = {
        item["selector_participant_id"]: item["selected_target_participant_id"]
        for item in selection_plan.get("choices", [])
    }
    selected_by: dict[str, list[str]] = defaultdict(list)
    for selector_id, target_id in choice_lookup.items():
        selected_by[target_id].append(selector_id)

    results = []
    for choice in selection_plan.get("choices", []):
        selector_id = choice["selector_participant_id"]
        target_id = choice["selected_target_participant_id"]
        selector = context["participant_lookup"][selector_id]
        target = context["participant_lookup"][target_id]
        reciprocal_target = choice_lookup.get(target_id)
        is_mutual = reciprocal_target == selector_id

        if is_mutual:
            outcome_type = "mutual_selection"
            summary = f"{selector.name} 选择了 {target.name}，并获得互选回应，关系方向明显收敛。"
            key_events = [
                "双方都给出明确选择并承接对方关注点。",
                "交流中出现被理解感与继续推进意愿。",
            ]
            tags = ["mutual_selection", "scene_05_level_02"]
            deltas = [
                SceneRelationshipDelta(
                    source_participant_id=selector_id,
                    target_participant_id=target_id,
                    changes={"trust": 7, "understood": 6, "intimacy": 6, "anxiety": -2},
                    reason="互选后交流稳定推进，关系确认感明显增强。",
                    event_tags=tags,
                ),
                SceneRelationshipDelta(
                    source_participant_id=target_id,
                    target_participant_id=selector_id,
                    changes={"trust": 7, "understood": 5, "intimacy": 6, "anxiety": -2},
                    reason="互选形成双向确认，交流质量高于礼貌互动。",
                    event_tags=tags,
                ),
            ]
        elif reciprocal_target and reciprocal_target != selector_id:
            third_name = context["participant_lookup"][reciprocal_target].name
            outcome_type = "mismatch_chain"
            summary = f"{selector.name} 选择了 {target.name}，但 {target.name} 更倾向 {third_name}，形成错位链。"
            key_events = [
                "单向释放偏好后未获得回流信号。",
                "交流停在确认阶段，关系推进不稳定。",
            ]
            tags = ["mismatch_chain", "scene_05_level_02"]
            deltas = [
                SceneRelationshipDelta(
                    source_participant_id=selector_id,
                    target_participant_id=target_id,
                    changes={"trust": 1, "understood": 1, "anxiety": 4, "intimacy": 1},
                    reason="主动选择后出现错位反馈，期待与回应不一致。",
                    event_tags=tags,
                )
            ]
        else:
            outcome_type = "single_sided_selection"
            summary = f"{selector.name} 主动选择 {target.name}，但暂未形成互选。"
            key_events = [
                "表达了明确倾向但回执不足。",
                "关系保留推进可能，但不确定感上升。",
            ]
            tags = ["single_sided_selection", "scene_05_level_02"]
            deltas = [
                SceneRelationshipDelta(
                    source_participant_id=selector_id,
                    target_participant_id=target_id,
                    changes={"trust": 2, "understood": 2, "intimacy": 2, "anxiety": 3},
                    reason="主动选择带来接触增量，但未形成双向确认。",
                    event_tags=tags,
                )
            ]

        if not selected_by.get(selector_id):
            deltas.append(
                SceneRelationshipDelta(
                    source_participant_id=selector_id,
                    target_participant_id=target_id,
                    changes={"anxiety": 2},
                    reason="本轮未被任何人主动选择，安全感有所下降。",
                    event_tags=["unchosen", "scene_05_level_02"],
                )
            )

        results.append(
            SceneSelectionResult(
                selector_participant_id=selector_id,
                selector_name=selector.name,
                selected_target_participant_id=target_id,
                selected_target_name=target.name,
                outcome_type=outcome_type,
                conversation_summary=summary,
                key_events=key_events,
                relationship_deltas=deltas,
                event_tags=tags,
                level_semantic=SCENE_CONFIG[SCENE_05_CODE]["scene_level"],
            )
        )

    return results


def derive_scene_05_relationship_deltas(
    selection_results: list[SceneSelectionResult],
) -> list[SceneRelationshipDelta]:
    delta_map: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    reason_map: dict[tuple[str, str], list[str]] = defaultdict(list)
    tag_map: dict[tuple[str, str], set[str]] = defaultdict(set)

    for result in selection_results:
        for delta in result.relationship_deltas:
            key = (delta.source_participant_id, delta.target_participant_id)
            for metric_key, metric_value in delta.changes.items():
                delta_map[key][metric_key] += metric_value
            reason_map[key].append(delta.reason)
            tag_map[key].update(delta.event_tags)

    merged = []
    for (source_id, target_id), changes in delta_map.items():
        normalized_changes = {
            key: clamp(value, -18, 18)
            for key, value in changes.items()
            if value != 0
        }
        if not normalized_changes:
            continue
        reasons = []
        for reason in reason_map[(source_id, target_id)]:
            if reason not in reasons:
                reasons.append(reason)
        merged.append(
            SceneRelationshipDelta(
                source_participant_id=source_id,
                target_participant_id=target_id,
                changes=normalized_changes,
                reason="；".join(reasons[:2]),
                event_tags=sorted(tag_map[(source_id, target_id)]),
            )
        )
    return merged


def summarize_scene_05_events(selection_results: list[SceneSelectionResult]) -> list[SceneEvent]:
    events = []
    for index, result in enumerate(selection_results, start=1):
        events.append(
            SceneEvent(
                title=f"主动选择 {index}: {result.selector_name} -> {result.selected_target_name}",
                description=result.conversation_summary,
                event_tags=result.event_tags,
                source_participant_id=result.selector_participant_id,
                target_participant_ids=[result.selected_target_participant_id],
                linked_turn_indices=[index],
            )
        )
    return events[:6]


def summarize_scene_05_results(
    context: dict,
    selection_results: list[SceneSelectionResult],
) -> str:
    if not selection_results:
        return "本场尚未形成有效的主动选择结果。"
    mutual_count = sum(1 for item in selection_results if item.outcome_type == "mutual_selection")
    mismatch_count = sum(1 for item in selection_results if item.outcome_type == "mismatch_chain")
    single_count = sum(1 for item in selection_results if item.outcome_type == "single_sided_selection")

    lines = ["主动选择交流完成，关系方向出现明显分层。"]
    lines.append(f"互选 {mutual_count} 组，单向选择 {single_count} 组，错位链 {mismatch_count} 组。")
    strongest = max(
        selection_results,
        key=lambda item: sum(abs(value) for delta in item.relationship_deltas for value in delta.changes.values()),
    )
    lines.append(f"最关键的一条线是 {strongest.selector_name} -> {strongest.selected_target_name}。")
    lines.append("这些结果将进入 Scene 06 的私密表达阶段继续检验。")
    return " ".join(lines)


def build_scene_05_next_tension(
    context: dict,
    selection_results: list[SceneSelectionResult],
    relationship_deltas: list[SceneRelationshipDelta],
) -> str:
    mutual = next((item for item in selection_results if item.outcome_type == "mutual_selection"), None)
    if mutual:
        return (
            f"scene_06_private_signal 中，{mutual.selector_name} 与 {mutual.selected_target_name} 的互选线将面临私密确认，"
            "同时其他错位关系会在暗线里继续发酵。"
        )
    if relationship_deltas:
        peak = max(relationship_deltas, key=lambda item: item.changes.get("anxiety", 0) + item.changes.get("intimacy", 0))
        source_name = context["participant_lookup"].get(peak.source_participant_id)
        target_name = context["participant_lookup"].get(peak.target_participant_id)
        source_text = source_name.name if source_name else peak.source_participant_id
        target_text = target_name.name if target_name else peak.target_participant_id
        return (
            f"scene_06_private_signal 会放大 {source_text} 对 {target_text} 的期待差，"
            "scene_07_new_date 再次邀约时将出现更清晰的进攻与回避分化。"
        )
    return "scene_06_private_signal 将检验这轮主动选择的真实强度，scene_07_new_date 会把错位关系推入新的竞争。"


def derive_scene_05_participant_memories(
    context: dict,
    relationship_deltas: list[SceneRelationshipDelta],
) -> list[dict]:
    updates = []
    for participant in context["participants"]:
        related = [
            item
            for item in relationship_deltas
            if item.source_participant_id == participant.id
        ]
        if not related:
            continue
        related.sort(
            key=lambda item: sum(abs(value) for value in item.changes.values()),
            reverse=True,
        )
        top = related[0]
        target = context["participant_lookup"].get(top.target_participant_id)
        target_name = target.name if target else top.target_participant_id
        updates.append(
            {
                "participant_id": participant.id,
                "memory_type": "scene_takeaway",
                "target_participant_ids": [top.target_participant_id],
                "summary": f"{participant.name} 在主动选择后对 {target_name} 的关系判断被重新校准。",
                "importance": clamp(42 + sum(abs(value) for value in top.changes.values()), 35, 90),
                "event_tags": top.event_tags,
            }
        )
    return updates
