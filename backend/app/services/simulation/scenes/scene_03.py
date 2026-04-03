from __future__ import annotations

import hashlib
import random
from collections import defaultdict

from app.models import SceneRun, SimulationRun
from app.schemas.runtime import (
    SceneEvent,
    SceneOrchestratorPlan,
    ScenePairDateResult,
    SceneRefereeResult,
    SceneRelationshipDelta,
    SceneRuntimeExecution,
)
from app.services.simulation.scene_config import SCENE_CONFIG
from app.services.simulation.scene_registry import SCENE_03_CODE
from app.services.simulation.service import clamp


def execute_scene_03_runtime(
    simulation: SimulationRun,
    scene_run: SceneRun,
    context: dict,
    input_summary: dict,
    plan: SceneOrchestratorPlan,
) -> SceneRuntimeExecution:
    rng = build_scene_03_rng(simulation.id, scene_run.id)
    matching_plan = build_scene_03_matching_plan(context, rng)
    pair_results = [
        run_scene_03_pair_date(
            context,
            pair["pair_index"],
            pair["participant_a_id"],
            pair["participant_b_id"],
            rng,
        )
        for pair in matching_plan["pairs"]
    ]
    ripple_deltas = derive_scene_03_emotion_ripples(
        context,
        matching_plan,
        pair_results,
    )
    relationship_deltas = derive_scene_03_relationship_deltas(pair_results, ripple_deltas)
    major_events = summarize_scene_03_events(context, pair_results, matching_plan)
    scene_summary = summarize_scene_03_results(context, pair_results, matching_plan)
    next_tension = build_scene_03_next_tension(context, pair_results, relationship_deltas)
    memory_updates = derive_scene_03_participant_memories(context, relationship_deltas)

    referee_result = SceneRefereeResult(
        scene_id=SCENE_03_CODE,
        scene_summary=scene_summary,
        major_events=major_events,
        relationship_deltas=relationship_deltas,
        pair_date_results=pair_results,
        competition_map=[],
        selection_results=[],
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
            "dominant_topics": [],
            "attention_distribution": [],
            "tension_pairs": [],
            "isolated_participants": [],
            "matching_plan": matching_plan,
            "scene_level": SCENE_CONFIG[SCENE_03_CODE]["scene_level"],
        },
        "next_tension": referee_result.next_tension,
        "replay_url": f"/simulations/{simulation.id}/scenes/{scene_run.id}",
    }
    return SceneRuntimeExecution(
        input_summary=input_summary,
        orchestrator_plan=plan,
        orchestrator_raw={
            **plan.model_dump(),
            "matching_plan": matching_plan,
        },
        messages=[],
        referee_result=referee_result,
        referee_raw={
            **referee_result.model_dump(),
            "matching_plan": matching_plan,
        },
        replay_payload=replay_payload,
    )


def build_scene_03_rng(simulation_id: str, scene_run_id: str) -> random.Random:
    seed_text = f"{simulation_id}:{scene_run_id}:{SCENE_03_CODE}"
    seed = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:16], 16)
    return random.Random(seed)


def build_scene_03_interest_target(context: dict, participant_id: str) -> str | None:
    best_target = None
    best_score = -10**9
    for other in context["participants"]:
        if other.id == participant_id:
            continue
        forward = context["relationship_map"].get((participant_id, other.id))
        backward = context["relationship_map"].get((other.id, participant_id))
        forward_metrics = forward.metrics if forward else {}
        backward_metrics = backward.metrics if backward else {}
        score = (
            forward_metrics.get("attraction", 0) * 1.3
            + forward_metrics.get("curiosity", 0)
            + forward_metrics.get("expectation", 0)
            + backward_metrics.get("curiosity", 0) * 0.6
            - forward_metrics.get("anxiety", 0) * 0.25
        )
        if score > best_score:
            best_score = score
            best_target = other.id
    return best_target


def apply_scene_03_strategy_bias(
    strategy_cards: list[str],
    forward_metrics: dict,
    backward_metrics: dict,
    familiarity_score: float,
) -> float:
    weight = 1.0
    mutual_interest = (
        forward_metrics.get("attraction", 0)
        + forward_metrics.get("curiosity", 0)
        + backward_metrics.get("attraction", 0)
        + backward_metrics.get("curiosity", 0)
    ) / 4
    novelty = max(0.0, 100.0 - familiarity_score)

    if "influence_matching" in strategy_cards:
        weight += 0.55 * (mutual_interest / 100)
    if "explore_unknown" in strategy_cards:
        weight += 0.6 * (novelty / 100)
    if "accept_randomness" in strategy_cards:
        weight = 1.0 + (weight - 1.0) * 0.25

    if not any(card in strategy_cards for card in ["influence_matching", "explore_unknown", "accept_randomness"]):
        weight += 0.12 * (mutual_interest / 100)

    return max(0.2, weight)


def weighted_choice(
    candidates: list[str],
    weights: list[float],
    rng: random.Random,
) -> str:
    total = sum(weights)
    if total <= 0:
        return rng.choice(candidates)
    cursor = rng.random() * total
    rolling = 0.0
    for candidate, weight in zip(candidates, weights):
        rolling += weight
        if cursor <= rolling:
            return candidate
    return candidates[-1]


def build_scene_03_matching_plan(context: dict, rng: random.Random) -> dict:
    remaining_ids = [participant.id for participant in context["participants"]]
    rng.shuffle(remaining_ids)
    pairs = []
    pair_index = 1

    while len(remaining_ids) >= 2:
        anchor_id = remaining_ids.pop(0)
        candidate_ids = list(remaining_ids)
        candidate_weights = []
        for candidate_id in candidate_ids:
            forward = context["relationship_map"].get((anchor_id, candidate_id))
            backward = context["relationship_map"].get((candidate_id, anchor_id))
            forward_metrics = forward.metrics if forward else {}
            backward_metrics = backward.metrics if backward else {}
            familiarity_score = (
                forward_metrics.get("comfort", 0)
                + forward_metrics.get("trust", 0)
                + forward_metrics.get("understood", 0)
                + backward_metrics.get("comfort", 0)
                + backward_metrics.get("trust", 0)
                + backward_metrics.get("understood", 0)
            ) / 6
            strategy_weight = apply_scene_03_strategy_bias(
                context["strategy_cards"],
                forward_metrics,
                backward_metrics,
                familiarity_score,
            )
            random_jitter = 0.88 + rng.random() * 0.24
            candidate_weights.append(strategy_weight * random_jitter)

        chosen_id = weighted_choice(candidate_ids, candidate_weights, rng)
        remaining_ids.remove(chosen_id)
        pairs.append(
            {
                "pair_index": pair_index,
                "participant_a_id": anchor_id,
                "participant_b_id": chosen_id,
            }
        )
        pair_index += 1

    waiting_participant_id = remaining_ids[0] if remaining_ids else None
    return {
        "pairs": pairs,
        "waiting_participant_id": waiting_participant_id,
    }


def run_scene_03_pair_date(
    context: dict,
    pair_index: int,
    participant_a_id: str,
    participant_b_id: str,
    rng: random.Random,
) -> ScenePairDateResult:
    participant_a = context["participant_lookup"][participant_a_id]
    participant_b = context["participant_lookup"][participant_b_id]
    rel_ab = context["relationship_map"].get((participant_a_id, participant_b_id))
    rel_ba = context["relationship_map"].get((participant_b_id, participant_a_id))
    metrics_ab = rel_ab.metrics if rel_ab else {}
    metrics_ba = rel_ba.metrics if rel_ba else {}

    initial_heat = (
        metrics_ab.get("attraction", 0)
        + metrics_ba.get("attraction", 0)
        + metrics_ab.get("curiosity", 0)
        + metrics_ba.get("curiosity", 0)
    ) / 4
    mismatch_penalty = abs(
        (participant_a.editable_personality or {}).get("emotional_openness", 50)
        - (participant_b.editable_personality or {}).get("emotional_openness", 50)
    ) * 0.2
    comfort_base = (
        metrics_ab.get("comfort", 0)
        + metrics_ba.get("comfort", 0)
        + metrics_ab.get("trust", 0)
        + metrics_ba.get("trust", 0)
    ) / 4
    spark_score = clamp(int(round(initial_heat * 0.6 + comfort_base * 0.3 - mismatch_penalty + rng.randint(-9, 9))), 0, 100)

    if spark_score >= 65:
        spark_level = "spark"
        summary = f"{participant_a.name} 和 {participant_b.name} 在随机约会中迅速找到共振点，互动明显升温。"
        key_events = [
            "双方都给出具体追问而不是停在礼貌寒暄。",
            "临近结束时主动表达想在下一场继续了解彼此。",
        ]
        delta_ab = {"attraction": 7, "curiosity": 5, "expectation": 4, "anxiety": -2}
        delta_ba = {"attraction": 6, "curiosity": 5, "expectation": 3, "anxiety": -2}
        tags = ["random_match", "unexpected_warmup", "scene_03_level_01"]
    elif spark_score <= 42:
        spark_level = "no_spark"
        summary = f"{participant_a.name} 和 {participant_b.name} 的互动偏礼貌，完成交流但没有明显火花。"
        key_events = [
            "对话能维持，但核心话题很快回到安全区。",
            "双方都没有抛出下一场继续靠近的信号。",
        ]
        delta_ab = {"attraction": -2, "expectation": -3, "anxiety": 2}
        delta_ba = {"attraction": -2, "expectation": -2, "anxiety": 2}
        tags = ["random_match", "flat_connection", "scene_03_level_01"]
    else:
        spark_level = "mixed"
        summary = f"{participant_a.name} 和 {participant_b.name} 出现了局部好感，但仍在观望是否值得继续。"
        key_events = [
            "至少一次话题延伸触发了新的好奇心。",
            "互动结束时态度偏积极，但尚未形成稳定期待。",
        ]
        delta_ab = {"curiosity": 4, "expectation": 1, "attraction": 2}
        delta_ba = {"curiosity": 3, "expectation": 1, "attraction": 2}
        tags = ["random_match", "partial_warmup", "scene_03_level_01"]

    reasons = [f"{summary} 关键点：{key_events[0]}", f"{summary} 关键点：{key_events[1]}"]
    pair_deltas = [
        SceneRelationshipDelta(
            source_participant_id=participant_a_id,
            target_participant_id=participant_b_id,
            changes=delta_ab,
            reason=reasons[0],
            event_tags=tags,
        ),
        SceneRelationshipDelta(
            source_participant_id=participant_b_id,
            target_participant_id=participant_a_id,
            changes=delta_ba,
            reason=reasons[1],
            event_tags=tags,
        ),
    ]
    return ScenePairDateResult(
        pair_index=pair_index,
        participant_ids=[participant_a_id, participant_b_id],
        participant_names=[participant_a.name, participant_b.name],
        interaction_type="pair_date",
        spark_level=spark_level,
        summary=summary,
        key_events=key_events[:2],
        relationship_deltas=pair_deltas,
        affects_future_candidate=spark_level != "no_spark",
        level_semantic=SCENE_CONFIG[SCENE_03_CODE]["scene_level"],
    )


def derive_scene_03_emotion_ripples(
    context: dict,
    matching_plan: dict,
    pair_results: list[ScenePairDateResult],
) -> list[SceneRelationshipDelta]:
    partner_lookup = {}
    for pair in matching_plan["pairs"]:
        partner_lookup[pair["participant_a_id"]] = pair["participant_b_id"]
        partner_lookup[pair["participant_b_id"]] = pair["participant_a_id"]

    ripples = []
    for participant in context["participants"]:
        expected_target = build_scene_03_interest_target(context, participant.id)
        if expected_target is None:
            continue
        actual_target = partner_lookup.get(participant.id)
        if actual_target == expected_target:
            ripples.append(
                SceneRelationshipDelta(
                    source_participant_id=participant.id,
                    target_participant_id=expected_target,
                    changes={"expectation": 2, "anxiety": -1, "curiosity": 1},
                    reason="随机匹配恰好连到当前最在意对象，期待被进一步放大。",
                    event_tags=["matched_expected_target", "scene_03_level_01"],
                )
            )
            continue

        if actual_target is None and matching_plan.get("waiting_participant_id") == participant.id:
            ripples.append(
                SceneRelationshipDelta(
                    source_participant_id=participant.id,
                    target_participant_id=expected_target,
                    changes={"anxiety": 3, "expectation": -2},
                    reason="本轮轮空观察导致对在意对象的不确定感上升。",
                    event_tags=["waiting_slot", "missed_expected_target", "scene_03_level_01"],
                )
            )
        else:
            ripples.append(
                SceneRelationshipDelta(
                    source_participant_id=participant.id,
                    target_participant_id=expected_target,
                    changes={"anxiety": 2, "expectation": -2},
                    reason="未匹配到当前最在意对象，出现早期焦虑与期待回落。",
                    event_tags=["missed_expected_target", "scene_03_level_01"],
                )
            )

    no_spark_pairs = {
        tuple(sorted(item.participant_ids))
        for item in pair_results
        if item.spark_level == "no_spark"
    }
    for participant_a_id, participant_b_id in no_spark_pairs:
        ripples.append(
            SceneRelationshipDelta(
                source_participant_id=participant_a_id,
                target_participant_id=participant_b_id,
                changes={"curiosity": -1},
                reason="本轮互动缺乏火花，探索意愿略有回落。",
                event_tags=["flat_connection", "scene_03_level_01"],
            )
        )
        ripples.append(
            SceneRelationshipDelta(
                source_participant_id=participant_b_id,
                target_participant_id=participant_a_id,
                changes={"curiosity": -1},
                reason="本轮互动缺乏火花，探索意愿略有回落。",
                event_tags=["flat_connection", "scene_03_level_01"],
            )
        )
    return ripples


def derive_scene_03_relationship_deltas(
    pair_results: list[ScenePairDateResult],
    ripple_deltas: list[SceneRelationshipDelta],
) -> list[SceneRelationshipDelta]:
    delta_map: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    reason_map: dict[tuple[str, str], list[str]] = defaultdict(list)
    tag_map: dict[tuple[str, str], set[str]] = defaultdict(set)

    for pair_result in pair_results:
        for delta in pair_result.relationship_deltas:
            key = (delta.source_participant_id, delta.target_participant_id)
            for metric_key, metric_value in delta.changes.items():
                delta_map[key][metric_key] += metric_value
            reason_map[key].append(delta.reason)
            tag_map[key].update(delta.event_tags)

    for delta in ripple_deltas:
        key = (delta.source_participant_id, delta.target_participant_id)
        for metric_key, metric_value in delta.changes.items():
            delta_map[key][metric_key] += metric_value
        reason_map[key].append(delta.reason)
        tag_map[key].update(delta.event_tags)

    results = []
    for (source_id, target_id), merged in delta_map.items():
        normalized_changes = {
            key: clamp(value, -18, 18)
            for key, value in merged.items()
            if value != 0
        }
        if not normalized_changes:
            continue
        reasons = []
        for reason in reason_map[(source_id, target_id)]:
            if reason not in reasons:
                reasons.append(reason)
        results.append(
            SceneRelationshipDelta(
                source_participant_id=source_id,
                target_participant_id=target_id,
                changes=normalized_changes,
                reason="；".join(reasons[:2]),
                event_tags=sorted(tag_map[(source_id, target_id)]),
            )
        )
    return results


def summarize_scene_03_events(
    context: dict,
    pair_results: list[ScenePairDateResult],
    matching_plan: dict,
) -> list[SceneEvent]:
    events = []
    for pair_result in pair_results:
        participant_ids = pair_result.participant_ids
        events.append(
            SceneEvent(
                title=f"随机约会组 {pair_result.pair_index}: {pair_result.participant_names[0]} x {pair_result.participant_names[1]}",
                description=pair_result.summary,
                event_tags=["random_date", pair_result.spark_level, "level_01_beginning_appeal"],
                source_participant_id=participant_ids[0],
                target_participant_ids=[participant_ids[1]],
                linked_turn_indices=[pair_result.pair_index],
            )
        )
    waiting_id = matching_plan.get("waiting_participant_id")
    if waiting_id:
        waiting_name = context["participant_lookup"][waiting_id].name
        events.append(
            SceneEvent(
                title=f"{waiting_name} 本轮轮空观察",
                description="由于人数为奇数，本轮进入观察位并记录他人随机约会结果。",
                event_tags=["waiting_slot", "random_date", "level_01_beginning_appeal"],
                source_participant_id=waiting_id,
                target_participant_ids=[],
                linked_turn_indices=[len(pair_results) + 1],
            )
        )
    return events[:6]


def summarize_scene_03_results(
    context: dict,
    pair_results: list[ScenePairDateResult],
    matching_plan: dict,
) -> str:
    if not pair_results:
        return "本场未形成有效随机约会结果。"
    warm_pairs = [item for item in pair_results if item.spark_level == "spark"]
    flat_pairs = [item for item in pair_results if item.spark_level == "no_spark"]
    mixed_pairs = [item for item in pair_results if item.spark_level == "mixed"]

    lines = ["随机约会完成，早期关系出现明显分化。"]
    if warm_pairs:
        first = warm_pairs[0]
        lines.append(
            f"偶然升温组合：{first.participant_names[0]} 与 {first.participant_names[1]}。"
        )
    if flat_pairs:
        first = flat_pairs[0]
        lines.append(
            f"无明显火花组合：{first.participant_names[0]} 与 {first.participant_names[1]}。"
        )
    if mixed_pairs and not warm_pairs:
        first = mixed_pairs[0]
        lines.append(
            f"潜在可继续观察：{first.participant_names[0]} 与 {first.participant_names[1]}。"
        )
    waiting_id = matching_plan.get("waiting_participant_id")
    if waiting_id:
        lines.append(f"{context['participant_lookup'][waiting_id].name} 本轮轮空，情绪波动更依赖旁观解读。")
    lines.append("这些变化仍属于 level_01 末段信号，后续 level_02 将重新检验。")
    return " ".join(lines)


def build_scene_03_next_tension(
    context: dict,
    pair_results: list[ScenePairDateResult],
    relationship_deltas: list[SceneRelationshipDelta],
) -> str:
    warm_pair = next((item for item in pair_results if item.spark_level == "spark"), None)
    if warm_pair:
        return (
            f"进入 scene_04_group_dinner 后，{warm_pair.participant_names[0]} 与 {warm_pair.participant_names[1]} "
            "会面对多人竞争放大；到 scene_05_conversation_choosing，是否继续主动靠近将被再次验证。"
        )
    if relationship_deltas:
        strongest = max(
            relationship_deltas,
            key=lambda item: item.changes.get("anxiety", 0) + item.changes.get("curiosity", 0),
        )
        source_name = context["participant_lookup"].get(strongest.source_participant_id)
        target_name = context["participant_lookup"].get(strongest.target_participant_id)
        source_text = source_name.name if source_name else strongest.source_participant_id
        target_text = target_name.name if target_name else strongest.target_participant_id
        return (
            f"scene_04_group_dinner 将重点放大 {source_text} 对 {target_text} 的不确定感，"
            "并在 scene_05_conversation_choosing 中转化为明确追聊或回避选择。"
        )
    return "scene_04_group_dinner 会把随机后的微弱信号拉进多人竞争，scene_05_conversation_choosing 将迫使每个人给出下一步对象偏好。"


def derive_scene_03_participant_memories(
    context: dict,
    relationship_deltas: list[SceneRelationshipDelta],
) -> list[dict]:
    memory_updates = []
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
        memory_updates.append(
            {
                "participant_id": participant.id,
                "memory_type": "scene_takeaway",
                "target_participant_ids": [top.target_participant_id],
                "summary": f"{participant.name} 在随机约会后对 {target_name} 的判断发生变化。",
                "importance": clamp(
                    42 + sum(abs(value) for value in top.changes.values()),
                    35,
                    88,
                ),
                "event_tags": top.event_tags,
            }
        )
    return memory_updates
