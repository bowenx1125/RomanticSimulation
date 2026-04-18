from __future__ import annotations

import hashlib
import random
from collections import defaultdict

from app.models import SceneRun, SimulationRun
from app.schemas.runtime import (
    SceneEvent,
    SceneExpectationMissResult,
    SceneOrchestratorPlan,
    ScenePrivateSignalResult,
    SceneRefereeResult,
    SceneRelationshipDelta,
    SceneRuntimeExecution,
)
from app.services.simulation.scene_config import SCENE_CONFIG
from app.services.simulation.scene_registry import SCENE_06_CODE
from app.services.simulation.scenes.synthetic_rounds import build_scene_06_synthetic_rounds
from app.services.simulation.service import clamp


def execute_scene_06_runtime(
    simulation: SimulationRun,
    scene_run: SceneRun,
    context: dict,
    input_summary: dict,
    plan: SceneOrchestratorPlan,
) -> SceneRuntimeExecution:
    rng = build_scene_06_rng(simulation.id, scene_run.id)
    signal_plan = build_scene_06_signal_plan(context, rng)
    signal_results = run_scene_06_private_signal(context, signal_plan)
    missed_expectations = derive_scene_06_expectation_misses(context, signal_plan)
    relationship_deltas = derive_scene_06_relationship_deltas(signal_results, missed_expectations)
    major_events = summarize_scene_06_events(signal_results, missed_expectations)
    scene_summary = summarize_scene_06_results(context, signal_results, missed_expectations)
    next_tension = build_scene_06_next_tension(context, signal_results, missed_expectations)
    memory_updates = derive_scene_06_participant_memories(context, relationship_deltas)

    referee_result = SceneRefereeResult(
        scene_id=SCENE_06_CODE,
        scene_summary=scene_summary,
        major_events=major_events,
        relationship_deltas=relationship_deltas,
        pair_date_results=[],
        competition_map=[],
        selection_results=[],
        signal_results=signal_results,
        missed_expectations=missed_expectations,
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
        "rounds": build_scene_06_synthetic_rounds(plan, signal_results, missed_expectations),
        "group_state_after_scene": {
            "dominant_topics": ["private_signal", "expectation_gap", "misread"],
            "attention_distribution": [],
            "tension_pairs": [],
            "isolated_participants": [],
            "signal_plan": signal_plan,
            "scene_level": SCENE_CONFIG[SCENE_06_CODE]["scene_level"],
        },
        "next_tension": referee_result.next_tension,
        "replay_url": f"/simulations/{simulation.id}/scenes/{scene_run.id}",
    }
    return SceneRuntimeExecution(
        input_summary=input_summary,
        orchestrator_plan=plan,
        orchestrator_raw={
            **plan.model_dump(),
            "signal_plan": signal_plan,
        },
        messages=[],
        referee_result=referee_result,
        referee_raw={
            **referee_result.model_dump(),
            "signal_plan": signal_plan,
        },
        replay_payload=replay_payload,
    )


def build_scene_06_rng(simulation_id: str, scene_run_id: str) -> random.Random:
    seed_text = f"{simulation_id}:{scene_run_id}:{SCENE_06_CODE}"
    seed = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:16], 16)
    return random.Random(seed)


def build_scene_06_seed(context: dict) -> dict:
    return {
        participant.id: [
            item["recipient_participant_id"]
            for item in build_scene_06_candidate_scores(context, participant.id)[:2]
        ]
        for participant in context["participants"]
    }


def build_scene_06_candidate_scores(context: dict, sender_id: str) -> list[dict]:
    candidates = []
    for participant in context["participants"]:
        if participant.id == sender_id:
            continue
        forward = context["relationship_map"].get((sender_id, participant.id))
        backward = context["relationship_map"].get((participant.id, sender_id))
        forward_metrics = forward.metrics if forward else {}
        backward_metrics = backward.metrics if backward else {}

        expectation = forward_metrics.get("expectation", 0)
        attraction = forward_metrics.get("attraction", 0)
        trust = forward_metrics.get("trust", 0)
        curiosity = forward_metrics.get("curiosity", 0)
        incoming_interest = backward_metrics.get("expectation", 0) + backward_metrics.get("attraction", 0)

        score = (
            expectation * 1.3
            + attraction
            + trust * 0.9
            + curiosity * 0.6
            + incoming_interest * 0.35
        )
        candidates.append(
            {
                "sender_participant_id": sender_id,
                "recipient_participant_id": participant.id,
                "score": score,
            }
        )
    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates


def build_scene_06_signal_plan(context: dict, rng: random.Random) -> dict:
    strategy_cards = set(context.get("strategy_cards", []))
    signal_style = "ambiguous"
    if "send_clear_signal" in strategy_cards:
        signal_style = "clear"
    elif "protect_self_image" in strategy_cards:
        signal_style = "guarded"
    elif "signal_multiple_targets" in strategy_cards:
        signal_style = "multi_target"
    elif "keep_ambiguity" in strategy_cards:
        signal_style = "ambiguous"

    max_targets = 2 if "signal_multiple_targets" in strategy_cards else 1
    plan_items = []
    for sender in context["participants"]:
        ranked = build_scene_06_candidate_scores(context, sender.id)
        if not ranked:
            continue

        top_slice = ranked[: min(3, len(ranked))]
        jittered = sorted(
            (
                {
                    **item,
                    "score": item["score"] + rng.random() * 0.9,
                }
                for item in top_slice
            ),
            key=lambda item: item["score"],
            reverse=True,
        )
        chosen = jittered[: max_targets]
        recipient_ids = [item["recipient_participant_id"] for item in chosen]
        recipient_names = [context["participant_lookup"][item_id].name for item_id in recipient_ids]
        plan_items.append(
            {
                "sender_participant_id": sender.id,
                "recipient_participant_ids": recipient_ids,
                "signal_style": signal_style,
                "reason": f"{sender.name} 在当前关系图里更倾向向 {'、'.join(recipient_names)} 释放私密信号。",
            }
        )

    return {
        "scene_id": SCENE_06_CODE,
        "scene_level": SCENE_CONFIG[SCENE_06_CODE]["scene_level"],
        "strategy_cards": sorted(strategy_cards),
        "signal_plan": plan_items,
    }


def run_scene_06_private_signal(
    context: dict,
    signal_plan: dict,
) -> list[ScenePrivateSignalResult]:
    results = []
    for item in signal_plan.get("signal_plan", []):
        sender_id = item["sender_participant_id"]
        sender = context["participant_lookup"][sender_id]
        signal_style = item.get("signal_style", "ambiguous")
        recipient_ids = item.get("recipient_participant_ids", [])
        multi_target_mode = len(recipient_ids) > 1

        for recipient_id in recipient_ids:
            recipient = context["participant_lookup"][recipient_id]
            backward = context["relationship_map"].get((recipient_id, sender_id))
            backward_metrics = backward.metrics if backward else {}
            recipient_expectation = backward_metrics.get("expectation", 0)

            if signal_style == "clear":
                outcome_type = "expectation_confirmed"
                summary = f"{sender.name} 向 {recipient.name} 发出明确私密信号，表达愿意继续推进这条线。"
                interpretation = f"{recipient.name} 把这条信号解读为较高优先级关注，关系方向更清晰。"
                event_tags = ["clear_signal", "expectation_confirmed", "scene_06_level_02"]
                deltas = [
                    SceneRelationshipDelta(
                        source_participant_id=sender_id,
                        target_participant_id=recipient_id,
                        changes={"expectation": 6, "trust": 4},
                        reason="明确私密表达让关系推进意图更可读。",
                        event_tags=event_tags,
                    ),
                    SceneRelationshipDelta(
                        source_participant_id=recipient_id,
                        target_participant_id=sender_id,
                        changes={"expectation": 5, "trust": 4, "disappointment": -2},
                        reason="收到清晰且一致的私密信号，怀疑感下降。",
                        event_tags=event_tags,
                    ),
                ]
                key_events = [
                    "信号表达明确，接收方可快速判断关系方向。",
                    "双方信任与期待同步升高。",
                ]
            elif signal_style == "guarded":
                outcome_type = "guarded_signal"
                summary = f"{sender.name} 向 {recipient.name} 发送了偏防御式信号，既表达在意也保留退路。"
                interpretation = f"{recipient.name} 感到对方有关注，但仍在保护自我形象。"
                event_tags = ["guarded_signal", "protect_self_image", "scene_06_level_02"]
                deltas = [
                    SceneRelationshipDelta(
                        source_participant_id=sender_id,
                        target_participant_id=recipient_id,
                        changes={"expectation": 2, "trust": 1},
                        reason="防御式表达降低了推进速度，但保留了连接。",
                        event_tags=event_tags,
                    ),
                    SceneRelationshipDelta(
                        source_participant_id=recipient_id,
                        target_participant_id=sender_id,
                        changes={"expectation": 2, "expectation_gap": 2},
                        reason="感知到对方有意靠近，但信号强度不足以完全确认。",
                        event_tags=event_tags,
                    ),
                ]
                key_events = [
                    "表达保持谨慎，推进效率下降。",
                    "接收方对方向判断仍有不确定。",
                ]
            elif multi_target_mode:
                outcome_type = "multi_target_signal"
                summary = f"{sender.name} 向多个目标分散释放私密信号，{recipient.name} 收到其中一条。"
                interpretation = f"{recipient.name} 能感知到兴趣，但会怀疑这是否是唯一重点。"
                event_tags = ["multi_target_signal", "signal_multiple_targets", "scene_06_level_02"]
                deltas = [
                    SceneRelationshipDelta(
                        source_participant_id=sender_id,
                        target_participant_id=recipient_id,
                        changes={"expectation": 3, "trust": 1, "expectation_gap": 2},
                        reason="分散信号降低了专一性，推进存在波动。",
                        event_tags=event_tags,
                    ),
                    SceneRelationshipDelta(
                        source_participant_id=recipient_id,
                        target_participant_id=sender_id,
                        changes={"expectation": 3, "trust": -1, "disappointment": 2, "expectation_gap": 4},
                        reason="收到信号但察觉对方并非单点投入，信任出现回落。",
                        event_tags=event_tags,
                    ),
                ]
                key_events = [
                    "多目标信号降低了排他感。",
                    "接收方更容易产生误判与落差。",
                ]
            else:
                outcome_type = "ambiguous_signal"
                summary = f"{sender.name} 向 {recipient.name} 发送了模糊私密信号，表达倾向但未完全明确。"
                if recipient_expectation >= 60:
                    interpretation = f"{recipient.name} 高估了这条信号的确定性，误判风险上升。"
                    deltas = [
                        SceneRelationshipDelta(
                            source_participant_id=sender_id,
                            target_participant_id=recipient_id,
                            changes={"expectation": 2, "trust": 1},
                            reason="模糊表达保留空间，但推进有限。",
                            event_tags=["ambiguous_signal", "scene_06_level_02"],
                        ),
                        SceneRelationshipDelta(
                            source_participant_id=recipient_id,
                            target_participant_id=sender_id,
                            changes={"expectation": 3, "expectation_gap": 5, "disappointment": 3, "trust": -2},
                            reason="高期待下接收到模糊信号，出现解读偏差与落差。",
                            event_tags=["ambiguous_signal", "misread", "scene_06_level_02"],
                        ),
                    ]
                    event_tags = ["ambiguous_signal", "misread", "scene_06_level_02"]
                    key_events = [
                        "接收方把模糊表达当作更强确认。",
                        "揭示后形成期待落差。",
                    ]
                else:
                    interpretation = f"{recipient.name} 将其解读为试探性靠近，暂未形成强确认。"
                    event_tags = ["ambiguous_signal", "scene_06_level_02"]
                    deltas = [
                        SceneRelationshipDelta(
                            source_participant_id=sender_id,
                            target_participant_id=recipient_id,
                            changes={"expectation": 2, "trust": 1},
                            reason="模糊信号降低受伤风险，但推进较慢。",
                            event_tags=event_tags,
                        ),
                        SceneRelationshipDelta(
                            source_participant_id=recipient_id,
                            target_participant_id=sender_id,
                            changes={"expectation": 2, "expectation_gap": 2},
                            reason="收到模糊表达后保持谨慎观察。",
                            event_tags=event_tags,
                        ),
                    ]
                    key_events = [
                        "信号可读但不够清晰。",
                        "关系推进保留了后续确认空间。",
                    ]

            results.append(
                ScenePrivateSignalResult(
                    sender_participant_id=sender_id,
                    sender_name=sender.name,
                    recipient_participant_id=recipient_id,
                    recipient_name=recipient.name,
                    signal_summary=summary,
                    signal_clarity=signal_style,
                    recipient_interpretation=interpretation,
                    outcome_type=outcome_type,
                    key_events=key_events,
                    relationship_deltas=deltas,
                    event_tags=event_tags,
                    level_semantic=SCENE_CONFIG[SCENE_06_CODE]["scene_level"],
                )
            )
    return results


def build_scene_06_expected_sender(context: dict, participant_id: str) -> str | None:
    best_sender = None
    best_score = -10**9
    for candidate in context["participants"]:
        if candidate.id == participant_id:
            continue
        relation = context["relationship_map"].get((participant_id, candidate.id))
        metrics = relation.metrics if relation else {}
        score = (
            metrics.get("expectation", 0) * 1.4
            + metrics.get("attraction", 0)
            + metrics.get("trust", 0) * 0.7
            - metrics.get("anxiety", 0) * 0.2
        )
        if score > best_score:
            best_score = score
            best_sender = candidate.id
    return best_sender


def derive_scene_06_expectation_misses(
    context: dict,
    signal_plan: dict,
) -> list[SceneExpectationMissResult]:
    received_from: dict[str, set[str]] = defaultdict(set)
    for item in signal_plan.get("signal_plan", []):
        sender_id = item["sender_participant_id"]
        for recipient_id in item.get("recipient_participant_ids", []):
            received_from[recipient_id].add(sender_id)

    misses = []
    for participant in context["participants"]:
        expected_from_id = build_scene_06_expected_sender(context, participant.id)
        if not expected_from_id:
            continue
        if expected_from_id in received_from.get(participant.id, set()):
            continue

        relation = context["relationship_map"].get((participant.id, expected_from_id))
        metrics = relation.metrics if relation else {}
        expectation_value = metrics.get("expectation", 0)
        gap_delta = clamp(max(3, int(round(expectation_value * 0.12))), 3, 14)
        disappointment_delta = clamp(max(2, int(round(expectation_value * 0.1))), 2, 12)
        trust_delta = -clamp(max(1, int(round(expectation_value * 0.06))), 1, 8)

        expected_name = context["participant_lookup"].get(expected_from_id)
        expected_text = expected_name.name if expected_name else expected_from_id
        reason = (
            f"{participant.name} 原本更期待收到 {expected_text} 的私密信号，"
            "但本轮揭示阶段未得到回应。"
        )
        tags = ["expectation_miss", "expectation_gap", "scene_06_level_02"]
        miss_delta = SceneRelationshipDelta(
            source_participant_id=participant.id,
            target_participant_id=expected_from_id,
            changes={
                "expectation_gap": gap_delta,
                "disappointment": disappointment_delta,
                "trust": trust_delta,
                "expectation": -min(6, max(2, gap_delta // 2)),
            },
            reason=reason,
            event_tags=tags,
        )
        misses.append(
            SceneExpectationMissResult(
                participant_id=participant.id,
                participant_name=participant.name,
                expected_from_participant_id=expected_from_id,
                expected_from_participant_name=expected_text,
                received=False,
                expectation_gap_delta=gap_delta,
                disappointment_delta=disappointment_delta,
                trust_delta=trust_delta,
                reason=reason,
                relationship_deltas=[miss_delta],
                event_tags=tags,
                level_semantic=SCENE_CONFIG[SCENE_06_CODE]["scene_level"],
            )
        )
    return misses


def derive_scene_06_relationship_deltas(
    signal_results: list[ScenePrivateSignalResult],
    missed_expectations: list[SceneExpectationMissResult],
) -> list[SceneRelationshipDelta]:
    delta_map: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    reason_map: dict[tuple[str, str], list[str]] = defaultdict(list)
    tag_map: dict[tuple[str, str], set[str]] = defaultdict(set)

    for result in signal_results:
        for delta in result.relationship_deltas:
            key = (delta.source_participant_id, delta.target_participant_id)
            for metric_key, metric_value in delta.changes.items():
                delta_map[key][metric_key] += metric_value
            reason_map[key].append(delta.reason)
            tag_map[key].update(delta.event_tags)

    for miss in missed_expectations:
        for delta in miss.relationship_deltas:
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


def summarize_scene_06_events(
    signal_results: list[ScenePrivateSignalResult],
    missed_expectations: list[SceneExpectationMissResult],
) -> list[SceneEvent]:
    events = []
    for index, item in enumerate(signal_results, start=1):
        events.append(
            SceneEvent(
                title=f"私密信号 {index}: {item.sender_name} -> {item.recipient_name}",
                description=item.signal_summary,
                event_tags=item.event_tags,
                source_participant_id=item.sender_participant_id,
                target_participant_ids=[item.recipient_participant_id],
                linked_turn_indices=[index],
            )
        )
    base_index = len(signal_results)
    for offset, miss in enumerate(missed_expectations, start=1):
        events.append(
            SceneEvent(
                title=f"期待落空: {miss.participant_name} 未收到 {miss.expected_from_participant_name} 的信号",
                description=miss.reason,
                event_tags=miss.event_tags,
                source_participant_id=miss.participant_id,
                target_participant_ids=[miss.expected_from_participant_id],
                linked_turn_indices=[base_index + offset],
            )
        )
    return events[:8]


def summarize_scene_06_results(
    context: dict,
    signal_results: list[ScenePrivateSignalResult],
    missed_expectations: list[SceneExpectationMissResult],
) -> str:
    if not signal_results:
        return "本场尚未形成有效私密信号结果。"

    clear_count = sum(1 for item in signal_results if item.signal_clarity == "clear")
    ambiguous_count = sum(1 for item in signal_results if item.signal_clarity == "ambiguous")
    guarded_count = sum(1 for item in signal_results if item.signal_clarity == "guarded")
    multi_count = sum(1 for item in signal_results if item.signal_clarity == "multi_target")

    lines = ["私密信号揭示完成，关系方向开始从公开互动转向更明确的暗线判断。"]
    lines.append(
        f"清晰信号 {clear_count} 条，模糊信号 {ambiguous_count} 条，防御信号 {guarded_count} 条，多目标信号 {multi_count} 条。"
    )
    lines.append(f"期待落空共 {len(missed_expectations)} 例，expectation_gap 已进入可见波动。")

    strongest = max(
        signal_results,
        key=lambda item: sum(abs(value) for delta in item.relationship_deltas for value in delta.changes.values()),
    )
    lines.append(f"最强私密线索来自 {strongest.sender_name} -> {strongest.recipient_name}。")
    lines.append("这些结果将直接影响 scene_07_new_date 的主动邀约竞争。")
    return " ".join(lines)


def build_scene_06_next_tension(
    context: dict,
    signal_results: list[ScenePrivateSignalResult],
    missed_expectations: list[SceneExpectationMissResult],
) -> str:
    if missed_expectations:
        top_miss = max(missed_expectations, key=lambda item: item.expectation_gap_delta + item.disappointment_delta)
        return (
            f"scene_07_new_date 中，{top_miss.participant_name} 在期待落空后的出手意愿会变得两极化，"
            f"与 {top_miss.expected_from_participant_name} 的邀约线最可能进入竞争或退缩分叉。"
        )

    clear_signal = next((item for item in signal_results if item.signal_clarity == "clear"), None)
    if clear_signal:
        return (
            f"scene_07_new_date 里，{clear_signal.sender_name} 对 {clear_signal.recipient_name} 的明确信号将提高主动邀约概率，"
            "也会吸引其他人围绕同一目标发起竞争。"
        )

    return "scene_07_new_date 将把本场的模糊与分散信号转成真实邀约决策，谁敢出手、谁会退缩会快速分化。"


def derive_scene_06_participant_memories(
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
                "summary": f"{participant.name} 在私密信号揭示后对 {target_name} 的期待被重新校准。",
                "importance": clamp(44 + sum(abs(value) for value in top.changes.values()), 35, 92),
                "event_tags": top.event_tags,
            }
        )
    return updates
