from __future__ import annotations

import hashlib
import random
from collections import defaultdict

from app.models import SceneRun, SimulationRun
from app.schemas.runtime import (
    SceneConflictTestResult,
    SceneEvent,
    SceneOrchestratorPlan,
    SceneRefereeResult,
    SceneRelationshipDelta,
    SceneRuntimeExecution,
)
from app.services.simulation.scene_config import SCENE_CONFIG
from app.services.simulation.scene_registry import SCENE_08_CODE
from app.services.simulation.scenes.synthetic_rounds import build_scene_08_synthetic_rounds
from app.services.simulation.service import clamp


CONFLICT_TOPICS = [
    {
        "topic": "未来生活规划分歧",
        "description": "一方想定居大城市追求事业，另一方倾向回老家过安稳生活。",
        "primary_metrics": {"conflict": 12, "trust": -6, "anxiety": 10, "comfort": -8},
        "repair_metrics": {"trust": 4, "conflict": -5, "comfort": 3, "anxiety": -4},
    },
    {
        "topic": "亲密关系边界认知",
        "description": "对私人空间、社交自由和异性朋友的底线完全不同。",
        "primary_metrics": {"conflict": 14, "trust": -8, "anxiety": 12, "comfort": -6},
        "repair_metrics": {"trust": 5, "conflict": -6, "comfort": 4, "anxiety": -5},
    },
    {
        "topic": "家庭责任与个人自由",
        "description": "对原生家庭的介入程度和婚后生活独立性有根本分歧。",
        "primary_metrics": {"conflict": 11, "trust": -5, "anxiety": 9, "comfort": -7},
        "repair_metrics": {"trust": 3, "conflict": -4, "comfort": 3, "anxiety": -3},
    },
    {
        "topic": "经济观与消费习惯",
        "description": "一方注重储蓄安全感，另一方认为钱应该用来提升生活品质。",
        "primary_metrics": {"conflict": 10, "trust": -4, "anxiety": 8, "comfort": -5},
        "repair_metrics": {"trust": 3, "conflict": -4, "comfort": 2, "anxiety": -3},
    },
    {
        "topic": "情绪表达与冲突处理方式",
        "description": "一方习惯冷处理，另一方需要立刻沟通解决，沉默被解读为不在乎。",
        "primary_metrics": {"conflict": 13, "trust": -7, "anxiety": 11, "comfort": -9},
        "repair_metrics": {"trust": 5, "conflict": -5, "comfort": 5, "anxiety": -6},
    },
]

SCENE_08_MULTIPLIER = 1.3


def execute_scene_08_runtime(
    simulation: SimulationRun,
    scene_run: SceneRun,
    context: dict,
    input_summary: dict,
    plan: SceneOrchestratorPlan,
) -> SceneRuntimeExecution:
    rng = build_scene_08_rng(simulation.id, scene_run.id)
    conflict_pairs = build_scene_08_conflict_pairs(context)
    conflict_test_results = resolve_scene_08_conflicts(context, conflict_pairs, rng)
    relationship_deltas = derive_scene_08_relationship_deltas(conflict_test_results)
    major_events = summarize_scene_08_events(conflict_test_results)
    scene_summary = summarize_scene_08_results(conflict_test_results)
    next_tension = build_scene_08_next_tension(context, conflict_test_results, relationship_deltas)
    memory_updates = derive_scene_08_participant_memories(context, conflict_test_results)

    referee_result = SceneRefereeResult(
        scene_id=SCENE_08_CODE,
        scene_summary=scene_summary,
        major_events=major_events,
        relationship_deltas=relationship_deltas,
        pair_date_results=[],
        competition_map=[],
        selection_results=[],
        signal_results=[],
        missed_expectations=[],
        invitation_results=[],
        competition_outcomes=[],
        conflict_test_results=conflict_test_results,
        decision_results=[],
        final_settlement_results=[],
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
            delta.model_dump() for delta in referee_result.relationship_deltas
        ],
        "pair_date_results": [],
        "competition_map": [],
        "selection_results": [],
        "signal_results": [],
        "missed_expectations": [],
        "invitation_results": [],
        "competition_outcomes": [],
        "conflict_test_results": [item.model_dump() for item in referee_result.conflict_test_results],
        "decision_results": [],
        "final_settlement_results": [],
        "rounds": build_scene_08_synthetic_rounds(plan, conflict_test_results),
        "group_state_after_scene": {
            "dominant_topics": ["conflict_test", "value_clash", "repair_or_collapse"],
            "attention_distribution": [],
            "tension_pairs": [],
            "isolated_participants": [],
            "conflict_pairs": [
                {
                    "participant_a_id": pair["participant_a_id"],
                    "participant_b_id": pair["participant_b_id"],
                    "closeness_score": pair["closeness_score"],
                }
                for pair in conflict_pairs
            ],
            "scene_level": SCENE_CONFIG[SCENE_08_CODE]["scene_level"],
        },
        "next_tension": referee_result.next_tension,
        "replay_url": f"/simulations/{simulation.id}/scenes/{scene_run.id}",
    }
    return SceneRuntimeExecution(
        input_summary=input_summary,
        orchestrator_plan=plan,
        orchestrator_raw={
            **plan.model_dump(),
            "conflict_pairs": conflict_pairs,
        },
        messages=[],
        referee_result=referee_result,
        referee_raw={
            **referee_result.model_dump(),
            "conflict_pairs": conflict_pairs,
        },
        replay_payload=replay_payload,
    )


def build_scene_08_rng(simulation_id: str, scene_run_id: str) -> random.Random:
    seed_text = f"{simulation_id}:{scene_run_id}:{SCENE_08_CODE}"
    seed = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:16], 16)
    return random.Random(seed)


def build_scene_08_conflict_pairs(context: dict) -> list[dict]:
    participants = context["participants"]
    relationship_map = context["relationship_map"]
    pair_scores: list[dict] = []

    seen = set()
    for p_a in participants:
        for p_b in participants:
            if p_a.id >= p_b.id:
                continue
            key = (p_a.id, p_b.id)
            if key in seen:
                continue
            seen.add(key)

            forward = relationship_map.get((p_a.id, p_b.id))
            backward = relationship_map.get((p_b.id, p_a.id))
            f_metrics = forward.metrics if forward else {}
            b_metrics = backward.metrics if backward else {}

            closeness = (
                f_metrics.get("attraction", 0) * 0.8
                + f_metrics.get("trust", 0) * 1.0
                + f_metrics.get("comfort", 0) * 0.6
                + f_metrics.get("understood", 0) * 0.5
                + b_metrics.get("attraction", 0) * 0.8
                + b_metrics.get("trust", 0) * 1.0
                + b_metrics.get("comfort", 0) * 0.6
                + b_metrics.get("understood", 0) * 0.5
            )
            pair_scores.append({
                "participant_a_id": p_a.id,
                "participant_a_name": p_a.name,
                "participant_b_id": p_b.id,
                "participant_b_name": p_b.name,
                "closeness_score": closeness,
            })

    pair_scores.sort(key=lambda item: item["closeness_score"], reverse=True)
    max_pairs = max(2, len(participants) // 2)
    return pair_scores[:max_pairs]


def build_scene_08_conflict_seed(context: dict) -> dict:
    pairs = build_scene_08_conflict_pairs(context)
    return {
        "conflict_pairs": [
            {
                "participant_a_id": pair["participant_a_id"],
                "participant_b_id": pair["participant_b_id"],
                "closeness_score": round(pair["closeness_score"], 1),
            }
            for pair in pairs
        ],
    }


def resolve_scene_08_conflicts(
    context: dict,
    conflict_pairs: list[dict],
    rng: random.Random,
) -> list[SceneConflictTestResult]:
    strategy_cards = set(context.get("strategy_cards", []))
    available_topics = list(CONFLICT_TOPICS)
    rng.shuffle(available_topics)
    results: list[SceneConflictTestResult] = []

    for pair_index, pair in enumerate(conflict_pairs):
        topic = available_topics[pair_index % len(available_topics)]
        p_a_id = pair["participant_a_id"]
        p_b_id = pair["participant_b_id"]
        p_a = context["participant_lookup"][p_a_id]
        p_b = context["participant_lookup"][p_b_id]

        forward = context["relationship_map"].get((p_a_id, p_b_id))
        backward = context["relationship_map"].get((p_b_id, p_a_id))
        f_metrics = forward.metrics if forward else {}
        b_metrics = backward.metrics if backward else {}

        avg_trust = (f_metrics.get("trust", 30) + b_metrics.get("trust", 30)) / 2
        avg_comfort = (f_metrics.get("comfort", 30) + b_metrics.get("comfort", 30)) / 2
        existing_conflict = (f_metrics.get("conflict", 10) + b_metrics.get("conflict", 10)) / 2

        p_a_personality = p_a.editable_personality or {}
        p_b_personality = p_b.editable_personality or {}
        p_a_stability = p_a_personality.get("self_esteem_stability", 50)
        p_b_stability = p_b_personality.get("self_esteem_stability", 50)
        avg_stability = (p_a_stability + p_b_stability) / 2

        p_a_conflict_style = p_a_personality.get("conflict_style", "avoid_then_explode")
        p_b_conflict_style = p_b_personality.get("conflict_style", "avoid_then_explode")

        intensity_score = (
            existing_conflict * 0.3
            + (100 - avg_trust) * 0.25
            + (100 - avg_stability) * 0.2
            + rng.random() * 25
        )
        if intensity_score >= 60:
            conflict_intensity = "high"
        elif intensity_score >= 35:
            conflict_intensity = "medium"
        else:
            conflict_intensity = "low"

        base_conflict_changes = dict(topic["primary_metrics"])
        for key in base_conflict_changes:
            base_conflict_changes[key] = int(round(base_conflict_changes[key] * SCENE_08_MULTIPLIER))

        if "repair_quickly" in strategy_cards:
            repair_bonus = 1.4
        elif "stand_ground_calmly" in strategy_cards:
            repair_bonus = 0.8
        else:
            repair_bonus = 1.0

        repair_success_chance = (
            avg_trust * 0.3
            + avg_comfort * 0.2
            + avg_stability * 0.25
            + (20 if _is_compatible_conflict_style(p_a_conflict_style, p_b_conflict_style) else -10)
            + rng.random() * 20
        )
        if "retreat_and_observe" in strategy_cards:
            repair_success_chance += 8

        survived = repair_success_chance >= 38

        if survived:
            repair_changes = dict(topic["repair_metrics"])
            for key in repair_changes:
                repair_changes[key] = int(round(repair_changes[key] * repair_bonus))

            net_changes_a_to_b = {}
            net_changes_b_to_a = {}
            for key in set(list(base_conflict_changes.keys()) + list(repair_changes.keys())):
                net = base_conflict_changes.get(key, 0) + repair_changes.get(key, 0)
                net_changes_a_to_b[key] = clamp(net, -18, 18)
                net_changes_b_to_a[key] = clamp(int(round(net * 0.85)), -18, 18)

            outcome_type = "survived_with_repair"
            summary = (
                f"{p_a.name} 与 {p_b.name} 在「{topic['topic']}」上产生激烈分歧，"
                f"但通过沟通完成了关系修复，信任经受住了考验。"
            )
            key_events = [
                f"冲突话题：{topic['description']}",
                "双方在冲突升级后尝试了修复性沟通。",
                "关系虽受冲击但核心信任结构保留。",
            ]
        else:
            net_changes_a_to_b = {}
            net_changes_b_to_a = {}
            collapse_extra = {"disappointment": 8, "expectation": -6, "exclusivity_pressure": -4}
            for key in set(list(base_conflict_changes.keys()) + list(collapse_extra.keys())):
                net = base_conflict_changes.get(key, 0) + collapse_extra.get(key, 0)
                net_changes_a_to_b[key] = clamp(net, -18, 18)
                net_changes_b_to_a[key] = clamp(int(round(net * 0.9)), -18, 18)

            outcome_type = "collapsed"
            summary = (
                f"{p_a.name} 与 {p_b.name} 在「{topic['topic']}」上无法达成共识，"
                f"关系信任结构出现严重裂痕。"
            )
            key_events = [
                f"冲突话题：{topic['description']}",
                "沟通陷入僵局，双方均感到被误解。",
                "关系信任结构崩塌，后续推进面临极高成本。",
            ]

        deltas = [
            SceneRelationshipDelta(
                source_participant_id=p_a_id,
                target_participant_id=p_b_id,
                changes={k: v for k, v in net_changes_a_to_b.items() if v != 0},
                reason=f"冲突测试「{topic['topic']}」后 {p_a.name} 对 {p_b.name} 的关系变化。",
                event_tags=["conflict_test", f"intensity_{conflict_intensity}", outcome_type],
            ),
            SceneRelationshipDelta(
                source_participant_id=p_b_id,
                target_participant_id=p_a_id,
                changes={k: v for k, v in net_changes_b_to_a.items() if v != 0},
                reason=f"冲突测试「{topic['topic']}」后 {p_b.name} 对 {p_a.name} 的关系变化。",
                event_tags=["conflict_test", f"intensity_{conflict_intensity}", outcome_type],
            ),
        ]

        event_tags = ["conflict_test", f"intensity_{conflict_intensity}", outcome_type, "scene_08_level_03"]

        results.append(
            SceneConflictTestResult(
                pair_index=pair_index + 1,
                participant_a_id=p_a_id,
                participant_a_name=p_a.name,
                participant_b_id=p_b_id,
                participant_b_name=p_b.name,
                conflict_topic=topic["topic"],
                conflict_intensity=conflict_intensity,
                outcome_type=outcome_type,
                survived=survived,
                summary=summary,
                key_events=key_events,
                relationship_deltas=deltas,
                event_tags=event_tags,
                level_semantic=SCENE_CONFIG[SCENE_08_CODE]["scene_level"],
            )
        )

    return results


def _is_compatible_conflict_style(style_a: str, style_b: str) -> bool:
    compatible_pairs = {
        ("steady_boundary", "press_then_clarify"),
        ("steady_boundary", "steady_boundary"),
        ("press_then_clarify", "steady_boundary"),
    }
    return (style_a, style_b) in compatible_pairs


def derive_scene_08_relationship_deltas(
    conflict_test_results: list[SceneConflictTestResult],
) -> list[SceneRelationshipDelta]:
    delta_map: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    reason_map: dict[tuple[str, str], list[str]] = defaultdict(list)
    tag_map: dict[tuple[str, str], set[str]] = defaultdict(set)

    for result in conflict_test_results:
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


def summarize_scene_08_events(
    conflict_test_results: list[SceneConflictTestResult],
) -> list[SceneEvent]:
    events = []
    for index, item in enumerate(conflict_test_results, start=1):
        events.append(
            SceneEvent(
                title=f"冲突测试 {index}: {item.participant_a_name} vs {item.participant_b_name}",
                description=item.summary,
                event_tags=item.event_tags,
                source_participant_id=item.participant_a_id,
                target_participant_ids=[item.participant_b_id],
                linked_turn_indices=[index],
            )
        )
    return events[:8]


def summarize_scene_08_results(
    conflict_test_results: list[SceneConflictTestResult],
) -> str:
    if not conflict_test_results:
        return "本场未形成有效的冲突测试结果。"

    survived_count = sum(1 for item in conflict_test_results if item.survived)
    collapsed_count = sum(1 for item in conflict_test_results if not item.survived)
    high_intensity = sum(1 for item in conflict_test_results if item.conflict_intensity == "high")

    lines = ["冲突测试完成，关系线进入价值观压力检验阶段。"]
    lines.append(
        f"共测试 {len(conflict_test_results)} 对关系线，"
        f"存活 {survived_count} 对，崩塌 {collapsed_count} 对，"
        f"其中高强度冲突 {high_intensity} 对。"
    )

    most_damaged = max(
        conflict_test_results,
        key=lambda item: sum(
            abs(v) for d in item.relationship_deltas for v in d.changes.values()
        ),
    )
    lines.append(
        f"波动最大的关系线是 {most_damaged.participant_a_name} 与 {most_damaged.participant_b_name}，"
        f"冲突话题为「{most_damaged.conflict_topic}」。"
    )
    lines.append("冲突后的变量波动将直接影响 scene_09_decision_night 中的最终选择。")
    return " ".join(lines)


def build_scene_08_next_tension(
    context: dict,
    conflict_test_results: list[SceneConflictTestResult],
    relationship_deltas: list[SceneRelationshipDelta],
) -> str:
    collapsed = [item for item in conflict_test_results if not item.survived]
    if collapsed:
        item = collapsed[0]
        return (
            f"scene_09_decision_night 中，{item.participant_a_name} 与 {item.participant_b_name} "
            f"的关系已在冲突中崩塌，双方需要重新评估是否还有修复可能，或转向其他对象。"
        )

    survived = [item for item in conflict_test_results if item.survived]
    if survived:
        item = max(
            survived,
            key=lambda r: sum(
                abs(v) for d in r.relationship_deltas for v in d.changes.values()
            ),
        )
        return (
            f"scene_09_decision_night 中，{item.participant_a_name} 与 {item.participant_b_name} "
            f"虽然扛住了冲突，但信任裂痕需要在最终选择前被重新评估。"
        )

    return "scene_09_decision_night 将基于冲突后的变量波动做出最终关系取舍。"


def derive_scene_08_participant_memories(
    context: dict,
    conflict_test_results: list[SceneConflictTestResult],
) -> list[dict]:
    updates = []
    participant_involvement: dict[str, list[SceneConflictTestResult]] = defaultdict(list)
    for result in conflict_test_results:
        participant_involvement[result.participant_a_id].append(result)
        participant_involvement[result.participant_b_id].append(result)

    for participant in context["participants"]:
        involved = participant_involvement.get(participant.id, [])
        if not involved:
            continue
        most_impactful = max(
            involved,
            key=lambda r: sum(
                abs(v) for d in r.relationship_deltas for v in d.changes.values()
            ),
        )
        other_id = (
            most_impactful.participant_b_id
            if most_impactful.participant_a_id == participant.id
            else most_impactful.participant_a_id
        )
        other_name = context["participant_lookup"].get(other_id)
        other_text = other_name.name if other_name else other_id
        outcome_text = "扛住了冲突" if most_impactful.survived else "关系在冲突中崩塌"

        updates.append({
            "participant_id": participant.id,
            "memory_type": "scene_takeaway",
            "target_participant_ids": [other_id],
            "summary": (
                f"{participant.name} 在冲突测试中与 {other_text} {outcome_text}，"
                f"话题是「{most_impactful.conflict_topic}」。"
            ),
            "importance": clamp(
                55 + sum(
                    abs(v)
                    for d in most_impactful.relationship_deltas
                    for v in d.changes.values()
                ),
                40,
                95,
            ),
            "event_tags": most_impactful.event_tags,
        })
    return updates
