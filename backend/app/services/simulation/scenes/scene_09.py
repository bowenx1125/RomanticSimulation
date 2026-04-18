from __future__ import annotations

import hashlib
import random
from collections import defaultdict

from app.models import SceneRun, SimulationRun
from app.schemas.runtime import (
    SceneDecisionResult,
    SceneEvent,
    SceneOrchestratorPlan,
    SceneRefereeResult,
    SceneRelationshipDelta,
    SceneRuntimeExecution,
)
from app.services.simulation.scene_config import SCENE_CONFIG
from app.services.simulation.scene_registry import SCENE_09_CODE
from app.services.simulation.scenes.synthetic_rounds import build_scene_09_synthetic_rounds
from app.services.simulation.service import clamp


COMMITMENT_LEVELS = ["committed", "leaning", "wavering", "withdrawn"]

SCENE_09_MULTIPLIER = 1.2


def execute_scene_09_runtime(
    simulation: SimulationRun,
    scene_run: SceneRun,
    context: dict,
    input_summary: dict,
    plan: SceneOrchestratorPlan,
) -> SceneRuntimeExecution:
    rng = build_scene_09_rng(simulation.id, scene_run.id)
    decision_results = resolve_scene_09_decisions(context, rng)
    relationship_deltas = derive_scene_09_relationship_deltas(decision_results)
    major_events = summarize_scene_09_events(decision_results)
    scene_summary = summarize_scene_09_results(decision_results)
    next_tension = build_scene_09_next_tension(context, decision_results, relationship_deltas)
    memory_updates = derive_scene_09_participant_memories(context, decision_results)

    referee_result = SceneRefereeResult(
        scene_id=SCENE_09_CODE,
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
        conflict_test_results=[],
        decision_results=decision_results,
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
        "major_events": [e.model_dump() for e in referee_result.major_events],
        "relationship_deltas": [d.model_dump() for d in referee_result.relationship_deltas],
        "pair_date_results": [],
        "competition_map": [],
        "selection_results": [],
        "signal_results": [],
        "missed_expectations": [],
        "invitation_results": [],
        "competition_outcomes": [],
        "conflict_test_results": [],
        "decision_results": [item.model_dump() for item in referee_result.decision_results],
        "final_settlement_results": [],
        "rounds": build_scene_09_synthetic_rounds(plan, decision_results),
        "group_state_after_scene": {
            "dominant_topics": ["decision_night", "final_choice", "commitment"],
            "scene_level": SCENE_CONFIG[SCENE_09_CODE]["scene_level"],
        },
        "next_tension": referee_result.next_tension,
        "replay_url": f"/simulations/{simulation.id}/scenes/{scene_run.id}",
    }
    return SceneRuntimeExecution(
        input_summary=input_summary,
        orchestrator_plan=plan,
        orchestrator_raw=plan.model_dump(),
        messages=[],
        referee_result=referee_result,
        referee_raw=referee_result.model_dump(),
        replay_payload=replay_payload,
    )


def build_scene_09_rng(simulation_id: str, scene_run_id: str) -> random.Random:
    seed_text = f"{simulation_id}:{scene_run_id}:{SCENE_09_CODE}"
    seed = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:16], 16)
    return random.Random(seed)


def build_scene_09_decision_seed(context: dict) -> dict:
    participants = context["participants"]
    relationship_map = context["relationship_map"]
    seeds = []
    for participant in participants:
        candidates = []
        for other in participants:
            if other.id == participant.id:
                continue
            rel = relationship_map.get((participant.id, other.id))
            if rel is None:
                continue
            metrics = rel.metrics or {}
            score = _composite_score(metrics)
            candidates.append({
                "target_id": other.id,
                "target_name": other.name,
                "composite_score": round(score, 1),
            })
        candidates.sort(key=lambda c: c["composite_score"], reverse=True)
        seeds.append({
            "participant_id": participant.id,
            "participant_name": participant.name,
            "top_candidates": candidates[:3],
        })
    return {"decision_seeds": seeds}


def _composite_score(metrics: dict) -> float:
    return (
        metrics.get("attraction", 0) * 1.0
        + metrics.get("trust", 0) * 1.2
        + metrics.get("comfort", 0) * 0.8
        + metrics.get("understood", 0) * 0.7
        + metrics.get("commitment_alignment", 0) * 0.6
        - metrics.get("conflict", 0) * 1.0
        - metrics.get("disappointment", 0) * 0.8
        - metrics.get("anxiety", 0) * 0.4
    )


def resolve_scene_09_decisions(
    context: dict,
    rng: random.Random,
) -> list[SceneDecisionResult]:
    participants = context["participants"]
    relationship_map = context["relationship_map"]
    strategy_cards = set(context.get("strategy_cards", []))
    results: list[SceneDecisionResult] = []

    for participant in participants:
        personality = participant.editable_personality or {}
        stability = personality.get("self_esteem_stability", 50)
        attachment = personality.get("attachment_style", "secure")

        candidates = _rank_candidates(participant, participants, relationship_map)

        if not candidates:
            results.append(_build_withdrawn_result(participant))
            continue

        top = candidates[0]
        top_metrics = top["metrics"]
        wavering_targets = [
            c["target_name"]
            for c in candidates[1:3]
            if c["composite"] > top["composite"] * 0.7
        ]

        total_cost = (
            top_metrics.get("conflict", 0)
            + top_metrics.get("disappointment", 0) * 0.8
            + top_metrics.get("anxiety", 0) * 0.5
        )

        commitment_level = _determine_commitment(
            top["composite"], total_cost, stability, attachment,
            wavering_targets, strategy_cards, rng,
        )

        if commitment_level == "withdrawn":
            final_target_id = None
            final_target_name = None
        else:
            final_target_id = top["target_id"]
            final_target_name = top["target_name"]

        cost_text = _build_cost_assessment(participant.name, top, total_cost, commitment_level)
        reason_text = _build_decision_reason(participant.name, final_target_name, commitment_level, wavering_targets)
        key_events = _build_decision_key_events(participant.name, final_target_name, commitment_level, wavering_targets)

        deltas = _build_decision_deltas(
            participant, final_target_id, final_target_name, commitment_level, top_metrics
        )

        event_tags = ["decision_night", commitment_level, "scene_09_level_03"]
        results.append(
            SceneDecisionResult(
                participant_id=participant.id,
                participant_name=participant.name,
                final_target_participant_id=final_target_id,
                final_target_name=final_target_name,
                wavering_targets=wavering_targets,
                commitment_level=commitment_level,
                cost_assessment=cost_text,
                decision_reason=reason_text,
                key_events=key_events,
                relationship_deltas=deltas,
                event_tags=event_tags,
                level_semantic=SCENE_CONFIG[SCENE_09_CODE]["scene_level"],
            )
        )

    return results


def _rank_candidates(participant, participants, relationship_map) -> list[dict]:
    candidates = []
    for other in participants:
        if other.id == participant.id:
            continue
        rel = relationship_map.get((participant.id, other.id))
        if rel is None:
            continue
        metrics = rel.metrics or {}
        candidates.append({
            "target_id": other.id,
            "target_name": other.name,
            "composite": _composite_score(metrics),
            "metrics": metrics,
        })
    candidates.sort(key=lambda c: c["composite"], reverse=True)
    return candidates


def _build_withdrawn_result(participant) -> SceneDecisionResult:
    return SceneDecisionResult(
        participant_id=participant.id,
        participant_name=participant.name,
        final_target_participant_id=None,
        final_target_name=None,
        wavering_targets=[],
        commitment_level="withdrawn",
        cost_assessment="没有足够的关系基础做出有意义的选择。",
        decision_reason="缺乏有效候选对象。",
        key_events=["参与者未建立足够的关系连接。"],
        relationship_deltas=[],
        event_tags=["decision_night", "withdrawn", "no_candidate"],
        level_semantic=SCENE_CONFIG[SCENE_09_CODE]["scene_level"],
    )


def _determine_commitment(
    composite: float,
    total_cost: float,
    stability: int,
    attachment: str,
    wavering_targets: list[str],
    strategy_cards: set[str],
    rng: random.Random,
) -> str:
    if composite < 80:
        level = "withdrawn"
    elif total_cost > 50 and stability < 45:
        level = "wavering"
    elif len(wavering_targets) > 0 and attachment == "anxious":
        level = "wavering"
    elif composite >= 200 and total_cost < 30:
        level = "committed"
    else:
        level = "leaning"

    if "go_all_in" in strategy_cards:
        if level == "leaning":
            level = "committed"
        elif level == "wavering":
            level = "leaning"
    if "play_safe" in strategy_cards and level == "committed":
        level = "leaning"

    jitter = rng.random() * 15
    if attachment == "anxious" and jitter > 10 and level == "committed":
        level = "leaning"

    return level


def _build_decision_deltas(
    participant, final_target_id, final_target_name, commitment_level, top_metrics
) -> list[SceneRelationshipDelta]:
    if not final_target_id:
        return []
    if commitment_level == "committed":
        changes = {
            "trust": clamp(6, -18, 18),
            "exclusivity_pressure": clamp(8, -18, 18),
            "commitment_alignment": clamp(5, -18, 18),
            "anxiety": clamp(-4, -18, 18),
        }
    elif commitment_level == "leaning":
        changes = {
            "trust": clamp(3, -18, 18),
            "exclusivity_pressure": clamp(4, -18, 18),
            "commitment_alignment": clamp(2, -18, 18),
        }
    elif commitment_level == "wavering":
        changes = {
            "anxiety": clamp(5, -18, 18),
            "exclusivity_pressure": clamp(-3, -18, 18),
            "disappointment": clamp(3, -18, 18),
        }
    else:
        return []
    return [
        SceneRelationshipDelta(
            source_participant_id=participant.id,
            target_participant_id=final_target_id,
            changes={k: v for k, v in changes.items() if v != 0},
            reason=f"{participant.name} 在选择夜以 {commitment_level} 态度锁定 {final_target_name}。",
            event_tags=["decision_night", commitment_level],
        ),
    ]


def _build_cost_assessment(name: str, top: dict, total_cost: float, commitment_level: str) -> str:
    if commitment_level == "withdrawn":
        return f"{name} 评估后认为所有关系线的代价都太高，选择退出。"
    cost_label = "低" if total_cost < 25 else ("中等" if total_cost < 50 else "高")
    return (
        f"{name} 对 {top['target_name']} 的综合评分为 {round(top['composite'], 1)}，"
        f"关系代价评估为{cost_label}（冲突+失望+焦虑 = {round(total_cost, 1)}）。"
    )


def _build_decision_reason(name: str, target_name, commitment_level: str, wavering: list) -> str:
    if commitment_level == "committed":
        return f"{name} 经过全面评估，坚定选择 {target_name} 作为最终对象。"
    if commitment_level == "leaning":
        if wavering:
            return f"{name} 倾向于 {target_name}，但仍对 {'、'.join(wavering)} 有所犹豫。"
        return f"{name} 倾向于 {target_name}，但尚未完全确信。"
    if commitment_level == "wavering":
        return f"{name} 对 {target_name} 和 {'、'.join(wavering or ['其他人'])} 之间摇摆不定。"
    return f"{name} 决定不做出选择，退出竞争。"


def _build_decision_key_events(name: str, target_name, commitment_level: str, wavering: list) -> list[str]:
    events = []
    if commitment_level == "committed":
        events.append(f"{name} 明确锁定 {target_name}，释放强承诺信号。")
    elif commitment_level == "leaning":
        events.append(f"{name} 对 {target_name} 表现出明显倾向。")
        if wavering:
            events.append(f"但 {'、'.join(wavering)} 仍在备选范围内。")
    elif commitment_level == "wavering":
        events.append(f"{name} 在多个对象间持续犹豫。")
    else:
        events.append(f"{name} 选择退出，不参与最终配对。")
    return events


def derive_scene_09_relationship_deltas(
    decision_results: list[SceneDecisionResult],
) -> list[SceneRelationshipDelta]:
    delta_map: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    reason_map: dict[tuple[str, str], list[str]] = defaultdict(list)
    tag_map: dict[tuple[str, str], set[str]] = defaultdict(set)

    for result in decision_results:
        for delta in result.relationship_deltas:
            key = (delta.source_participant_id, delta.target_participant_id)
            for mk, mv in delta.changes.items():
                delta_map[key][mk] += mv
            reason_map[key].append(delta.reason)
            tag_map[key].update(delta.event_tags)

    merged = []
    for (source_id, target_id), changes in delta_map.items():
        normalized = {k: clamp(v, -18, 18) for k, v in changes.items() if v != 0}
        if not normalized:
            continue
        reasons = list(dict.fromkeys(reason_map[(source_id, target_id)]))
        merged.append(
            SceneRelationshipDelta(
                source_participant_id=source_id,
                target_participant_id=target_id,
                changes=normalized,
                reason="；".join(reasons[:2]),
                event_tags=sorted(tag_map[(source_id, target_id)]),
            )
        )
    return merged


def summarize_scene_09_events(
    decision_results: list[SceneDecisionResult],
) -> list[SceneEvent]:
    events = []
    for item in decision_results:
        events.append(
            SceneEvent(
                title=f"选择夜决定：{item.participant_name}",
                description=item.decision_reason,
                event_tags=item.event_tags,
                source_participant_id=item.participant_id,
                target_participant_ids=[item.final_target_participant_id] if item.final_target_participant_id else [],
            )
        )
    return events[:8]


def summarize_scene_09_results(
    decision_results: list[SceneDecisionResult],
) -> str:
    if not decision_results:
        return "选择夜未产生有效决策结果。"

    committed = [r for r in decision_results if r.commitment_level == "committed"]
    leaning = [r for r in decision_results if r.commitment_level == "leaning"]
    wavering = [r for r in decision_results if r.commitment_level == "wavering"]
    withdrawn = [r for r in decision_results if r.commitment_level == "withdrawn"]

    lines = ["选择夜完成，所有参与者做出了最终取舍。"]
    parts = []
    if committed:
        parts.append(f"坚定选择 {len(committed)} 人")
    if leaning:
        parts.append(f"倾向但犹豫 {len(leaning)} 人")
    if wavering:
        parts.append(f"摇摆不定 {len(wavering)} 人")
    if withdrawn:
        parts.append(f"退出竞争 {len(withdrawn)} 人")
    lines.append("、".join(parts) + "。")

    mutual_pairs = _find_mutual_pairs(decision_results)
    if mutual_pairs:
        pair_texts = [f"{a} ↔ {b}" for a, b in mutual_pairs]
        lines.append(f"互选配对：{'、'.join(pair_texts)}。")

    lines.append("选择夜结果将直接决定 scene_10_final_confession 的告白对象和最终结算。")
    return " ".join(lines)


def _find_mutual_pairs(decision_results: list[SceneDecisionResult]) -> list[tuple[str, str]]:
    choices: dict[str, str | None] = {}
    name_map: dict[str, str] = {}
    for r in decision_results:
        choices[r.participant_id] = r.final_target_participant_id
        name_map[r.participant_id] = r.participant_name

    pairs = []
    seen = set()
    for pid, tid in choices.items():
        if tid and choices.get(tid) == pid:
            key = tuple(sorted([pid, tid]))
            if key not in seen:
                seen.add(key)
                pairs.append((name_map[pid], name_map.get(tid, tid)))
    return pairs


def build_scene_09_next_tension(
    context: dict,
    decision_results: list[SceneDecisionResult],
    relationship_deltas: list[SceneRelationshipDelta],
) -> str:
    mutual_pairs = _find_mutual_pairs(decision_results)
    wavering = [r for r in decision_results if r.commitment_level == "wavering"]

    if mutual_pairs:
        pair_text = "、".join(f"{a} ↔ {b}" for a, b in mutual_pairs)
        return (
            f"scene_10_final_confession 中，互选配对 {pair_text} 将进入最终告白，"
            "但告白是否成功仍取决于全局变量和关系故事的完整性。"
        )
    if wavering:
        names = "、".join(r.participant_name for r in wavering[:2])
        return (
            f"scene_10_final_confession 中，{names} 的摇摆尚未收敛，"
            "最终告白可能出现意外反转。"
        )
    return "scene_10_final_confession 将根据选择夜结果输出最终关系结算和完整故事。"


def derive_scene_09_participant_memories(
    context: dict,
    decision_results: list[SceneDecisionResult],
) -> list[dict]:
    updates = []
    for result in decision_results:
        target_id = result.final_target_participant_id
        if target_id:
            target_name = result.final_target_name or target_id
            summary_text = (
                f"{result.participant_name} 在选择夜以 {result.commitment_level} 态度选择了 {target_name}。"
            )
        else:
            target_id = result.participant_id
            summary_text = f"{result.participant_name} 在选择夜决定退出，不做最终选择。"

        updates.append({
            "participant_id": result.participant_id,
            "memory_type": "scene_takeaway",
            "target_participant_ids": [target_id] if target_id else [],
            "summary": summary_text,
            "importance": clamp(
                60 + (15 if result.commitment_level == "committed" else 5),
                40,
                95,
            ),
            "event_tags": result.event_tags,
        })
    return updates
