from __future__ import annotations

import hashlib
import random
from collections import defaultdict

from app.models import SceneRun, SimulationRun
from app.schemas.runtime import (
    SceneEvent,
    SceneFinalSettlementResult,
    SceneOrchestratorPlan,
    SceneRefereeResult,
    SceneRelationshipDelta,
    SceneRuntimeExecution,
)
from app.services.simulation.scene_config import SCENE_CONFIG
from app.services.simulation.scene_registry import SCENE_10_CODE
from app.services.simulation.scenes.synthetic_rounds import build_scene_10_synthetic_rounds
from app.services.simulation.service import clamp


ROMANCE_SCORE_WEIGHTS = {
    "attraction": 1.0,
    "trust": 1.3,
    "comfort": 0.8,
    "understood": 0.9,
    "commitment_alignment": 1.1,
    "curiosity": 0.4,
    "conflict": -1.2,
    "disappointment": -1.0,
    "anxiety": -0.5,
    "exclusivity_pressure": 0.3,
}


def execute_scene_10_runtime(
    simulation: SimulationRun,
    scene_run: SceneRun,
    context: dict,
    input_summary: dict,
    plan: SceneOrchestratorPlan,
) -> SceneRuntimeExecution:
    rng = build_scene_10_rng(simulation.id, scene_run.id)
    settlement_results = resolve_scene_10_settlements(context, rng)
    relationship_deltas = derive_scene_10_relationship_deltas(settlement_results)
    major_events = summarize_scene_10_events(settlement_results)
    scene_summary = summarize_scene_10_results(settlement_results)
    next_tension = "模拟结束，所有关系线已完成最终结算。"
    memory_updates = derive_scene_10_participant_memories(context, settlement_results)

    referee_result = SceneRefereeResult(
        scene_id=SCENE_10_CODE,
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
        decision_results=[],
        final_settlement_results=settlement_results,
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
        "decision_results": [],
        "final_settlement_results": [item.model_dump() for item in referee_result.final_settlement_results],
        "rounds": build_scene_10_synthetic_rounds(plan, settlement_results),
        "group_state_after_scene": {
            "dominant_topics": ["final_confession", "settlement", "story_output"],
            "scene_level": SCENE_CONFIG[SCENE_10_CODE]["scene_level"],
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


def build_scene_10_rng(simulation_id: str, scene_run_id: str) -> random.Random:
    seed_text = f"{simulation_id}:{scene_run_id}:{SCENE_10_CODE}"
    seed = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:16], 16)
    return random.Random(seed)


def build_scene_10_settlement_seed(context: dict) -> dict:
    participants = context["participants"]
    relationship_map = context["relationship_map"]
    seeds = []
    for participant in participants:
        best_target = None
        best_score = -999
        for other in participants:
            if other.id == participant.id:
                continue
            rel = relationship_map.get((participant.id, other.id))
            if rel is None:
                continue
            metrics = rel.metrics or {}
            score = _compute_romance_score(metrics)
            if score > best_score:
                best_score = score
                best_target = other
        seeds.append({
            "participant_id": participant.id,
            "participant_name": participant.name,
            "best_target_id": best_target.id if best_target else None,
            "best_target_name": best_target.name if best_target else None,
            "romance_score": round(best_score, 1),
        })
    return {"settlement_seeds": seeds}


def _compute_romance_score(metrics: dict) -> float:
    score = 0.0
    for key, weight in ROMANCE_SCORE_WEIGHTS.items():
        score += metrics.get(key, 0) * weight
    return score


def resolve_scene_10_settlements(
    context: dict,
    rng: random.Random,
) -> list[SceneFinalSettlementResult]:
    participants = context["participants"]
    relationship_map = context["relationship_map"]
    strategy_cards = set(context.get("strategy_cards", []))

    scene_09_artifact = context.get("previous_scene_artifact", {})
    scene_09_decisions = scene_09_artifact.get("decision_results", [])
    decision_map: dict[str, dict] = {}
    for d in scene_09_decisions:
        if isinstance(d, dict):
            decision_map[d.get("participant_id", "")] = d

    participant_best: dict[str, tuple[str, float, dict]] = {}
    for participant in participants:
        best_id = None
        best_score = -999.0
        best_metrics: dict = {}

        scene_09_choice = decision_map.get(participant.id, {})
        preferred_target = scene_09_choice.get("final_target_participant_id")

        for other in participants:
            if other.id == participant.id:
                continue
            rel = relationship_map.get((participant.id, other.id))
            if rel is None:
                continue
            metrics = rel.metrics or {}
            score = _compute_romance_score(metrics)

            if other.id == preferred_target:
                score += 25

            if score > best_score:
                best_score = score
                best_id = other.id
                best_metrics = metrics

        participant_best[participant.id] = (best_id or "", best_score, best_metrics)

    mutual_pairs = _find_mutual_commitments(participant_best)

    results: list[SceneFinalSettlementResult] = []
    settled_ids: set[str] = set()

    for p_a_id, p_b_id in mutual_pairs:
        p_a = context["participant_lookup"][p_a_id]
        p_b = context["participant_lookup"][p_b_id]
        _, score_a, metrics_a = participant_best[p_a_id]
        _, score_b, metrics_b = participant_best[p_b_id]
        avg_score = (score_a + score_b) / 2

        final_status, level_met = _determine_final_status(metrics_a, metrics_b)
        romance_int = clamp(int(round(avg_score / 5)), 0, 100)
        if "romantic_boost" in strategy_cards:
            romance_int = clamp(romance_int + 5, 0, 100)

        turning_points = _build_turning_points(p_a.name, p_b.name, metrics_a, metrics_b)
        story = _build_relationship_story(p_a.name, p_b.name, final_status, turning_points, romance_int)

        success_reasons = []
        failure_reasons = []
        if final_status == "paired":
            success_reasons = [
                "双方在冲突测试中存活",
                "选择夜互选匹配",
                "关键指标（信任、吸引力、承诺对齐）均达标",
            ]
        elif final_status == "open_ending":
            failure_reasons = ["关系有基础但尚未达到配对门槛"]
        else:
            failure_reasons = ["信任或吸引力不足", "冲突累积导致关系降级"]

        for pid, pname, partner_id, partner_name, r_score in [
            (p_a_id, p_a.name, p_b_id, p_b.name, romance_int),
            (p_b_id, p_b.name, p_a_id, p_a.name, romance_int),
        ]:
            results.append(
                SceneFinalSettlementResult(
                    participant_id=pid,
                    participant_name=pname,
                    partner_participant_id=partner_id,
                    partner_name=partner_name,
                    final_status=final_status,
                    romance_score=r_score,
                    key_turning_points=turning_points,
                    success_reasons=success_reasons,
                    failure_reasons=failure_reasons,
                    relationship_story=story,
                    level_requirement_met=level_met,
                    event_tags=["final_confession", final_status, "scene_10_level_03"],
                    level_semantic=SCENE_CONFIG[SCENE_10_CODE]["scene_level"],
                )
            )
            settled_ids.add(pid)

    for participant in participants:
        if participant.id in settled_ids:
            continue
        best_id, best_score, best_metrics = participant_best[participant.id]
        partner = context["participant_lookup"].get(best_id)
        partner_name = partner.name if partner else None
        romance_int = clamp(int(round(best_score / 5)), 0, 100)

        if best_score >= 150 and best_metrics.get("trust", 0) >= 55:
            final_status = "open_ending"
            level_met = False
            failure_reasons = ["对方未互选，关系无法确认为配对。"]
            success_reasons = []
        else:
            final_status = "out"
            level_met = False
            failure_reasons = ["关系积累不足或冲突过高，无法进入配对。"]
            success_reasons = []

        turning_points = _build_solo_turning_points(participant.name, partner_name, best_metrics)
        story = _build_solo_story(participant.name, partner_name, final_status, turning_points, romance_int)

        results.append(
            SceneFinalSettlementResult(
                participant_id=participant.id,
                participant_name=participant.name,
                partner_participant_id=best_id if best_id else None,
                partner_name=partner_name,
                final_status=final_status,
                romance_score=romance_int,
                key_turning_points=turning_points,
                success_reasons=success_reasons,
                failure_reasons=failure_reasons,
                relationship_story=story,
                level_requirement_met=level_met,
                event_tags=["final_confession", final_status, "scene_10_level_03"],
                level_semantic=SCENE_CONFIG[SCENE_10_CODE]["scene_level"],
            )
        )

    return results


def _find_mutual_commitments(
    participant_best: dict[str, tuple[str, float, dict]],
) -> list[tuple[str, str]]:
    pairs = []
    seen: set[tuple[str, str]] = set()
    for p_id, (best_id, _, _) in participant_best.items():
        if not best_id:
            continue
        other_best = participant_best.get(best_id)
        if other_best and other_best[0] == p_id:
            key = tuple(sorted([p_id, best_id]))
            if key not in seen:
                seen.add(key)
                pairs.append((p_id, best_id))
    return pairs


def _determine_final_status(
    metrics_a: dict, metrics_b: dict,
) -> tuple[str, bool]:
    avg_attraction = (metrics_a.get("attraction", 0) + metrics_b.get("attraction", 0)) / 2
    avg_trust = (metrics_a.get("trust", 0) + metrics_b.get("trust", 0)) / 2
    avg_commitment = (
        metrics_a.get("commitment_alignment", 0) + metrics_b.get("commitment_alignment", 0)
    ) / 2
    avg_conflict = (metrics_a.get("conflict", 0) + metrics_b.get("conflict", 0)) / 2

    if avg_attraction >= 70 and avg_trust >= 68 and avg_commitment >= 65 and avg_conflict < 35:
        return "paired", True
    if avg_attraction >= 55 and avg_trust >= 50 and avg_conflict < 50:
        return "open_ending", False
    return "out", False


def _build_turning_points(name_a: str, name_b: str, metrics_a: dict, metrics_b: dict) -> list[str]:
    points = []
    avg_attraction = (metrics_a.get("attraction", 0) + metrics_b.get("attraction", 0)) / 2
    avg_trust = (metrics_a.get("trust", 0) + metrics_b.get("trust", 0)) / 2
    avg_conflict = (metrics_a.get("conflict", 0) + metrics_b.get("conflict", 0)) / 2

    if avg_attraction >= 65:
        points.append(f"{name_a} 与 {name_b} 之间的吸引力始终处于高位。")
    if avg_trust >= 60:
        points.append("双方在多次互动中建立了稳固的信任基础。")
    if avg_conflict >= 30:
        points.append("经历过价值观冲突的考验，关系承受了压力。")
    if metrics_a.get("understood", 0) >= 55 or metrics_b.get("understood", 0) >= 55:
        points.append("至少一方感到被深层理解。")
    if not points:
        points.append("关系在多场互动中逐步发展。")
    return points[:4]


def _build_solo_turning_points(name: str, partner_name: str | None, metrics: dict) -> list[str]:
    points = []
    if metrics.get("attraction", 0) >= 55:
        points.append(f"{name} 对 {partner_name or '对方'} 有较强好感，但未获得对等回应。")
    if metrics.get("conflict", 0) >= 40:
        points.append("冲突积累过高，成为关系推进的障碍。")
    if metrics.get("disappointment", 0) >= 35:
        points.append("期望落差持续扩大，信任受损。")
    if not points:
        points.append(f"{name} 在整个过程中未找到足够匹配的对象。")
    return points[:3]


def _build_relationship_story(
    name_a: str, name_b: str, final_status: str,
    turning_points: list[str], romance_score: int,
) -> str:
    tp_text = " ".join(turning_points)
    if final_status == "paired":
        return (
            f"{name_a} 与 {name_b} 从初见到经历冲突，最终确认了彼此的心意。"
            f"{tp_text} "
            f"最终恋爱可能性评分为 {romance_score} 分，双方成功配对。"
        )
    if final_status == "open_ending":
        return (
            f"{name_a} 与 {name_b} 之间有明确的好感基础，但尚未完全跨过配对门槛。"
            f"{tp_text} "
            f"最终恋爱可能性评分为 {romance_score} 分，关系留有开放结局。"
        )
    return (
        f"{name_a} 与 {name_b} 的关系在尝试中未能走到最后。"
        f"{tp_text} "
        f"最终恋爱可能性评分为 {romance_score} 分。"
    )


def _build_solo_story(
    name: str, partner_name: str | None, final_status: str,
    turning_points: list[str], romance_score: int,
) -> str:
    tp_text = " ".join(turning_points)
    target = partner_name or "任何对象"
    if final_status == "open_ending":
        return (
            f"{name} 对 {target} 有好感但未获互选。"
            f"{tp_text} "
            f"恋爱可能性评分为 {romance_score} 分，关系留有余地。"
        )
    return (
        f"{name} 未能与 {target} 建立足够的关系基础。"
        f"{tp_text} "
        f"恋爱可能性评分为 {romance_score} 分。"
    )


def derive_scene_10_relationship_deltas(
    settlement_results: list[SceneFinalSettlementResult],
) -> list[SceneRelationshipDelta]:
    deltas = []
    seen: set[tuple[str, str]] = set()
    for result in settlement_results:
        if not result.partner_participant_id:
            continue
        key = (result.participant_id, result.partner_participant_id)
        if key in seen:
            continue
        seen.add(key)

        if result.final_status == "paired":
            changes = {
                "trust": clamp(8, -18, 18),
                "commitment_alignment": clamp(10, -18, 18),
                "exclusivity_pressure": clamp(6, -18, 18),
                "anxiety": clamp(-6, -18, 18),
                "conflict": clamp(-4, -18, 18),
            }
        elif result.final_status == "open_ending":
            changes = {
                "trust": clamp(3, -18, 18),
                "anxiety": clamp(4, -18, 18),
                "expectation": clamp(-3, -18, 18),
            }
        else:
            changes = {
                "disappointment": clamp(6, -18, 18),
                "trust": clamp(-4, -18, 18),
                "expectation": clamp(-5, -18, 18),
            }

        deltas.append(
            SceneRelationshipDelta(
                source_participant_id=result.participant_id,
                target_participant_id=result.partner_participant_id,
                changes={k: v for k, v in changes.items() if v != 0},
                reason=f"最终结算：{result.participant_name} 与 {result.partner_name} 的关系走向为 {result.final_status}。",
                event_tags=["final_confession", result.final_status],
            )
        )
    return deltas


def summarize_scene_10_events(
    settlement_results: list[SceneFinalSettlementResult],
) -> list[SceneEvent]:
    events = []
    seen_pairs: set[tuple[str, str]] = set()
    for item in settlement_results:
        if item.partner_participant_id:
            pair_key = tuple(sorted([item.participant_id, item.partner_participant_id]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
        events.append(
            SceneEvent(
                title=f"最终结算：{item.participant_name}",
                description=item.relationship_story[:200],
                event_tags=item.event_tags,
                source_participant_id=item.participant_id,
                target_participant_ids=[item.partner_participant_id] if item.partner_participant_id else [],
            )
        )
    return events[:8]


def summarize_scene_10_results(
    settlement_results: list[SceneFinalSettlementResult],
) -> str:
    if not settlement_results:
        return "最终结算未产生有效结果。"

    paired = [r for r in settlement_results if r.final_status == "paired"]
    open_ending = [r for r in settlement_results if r.final_status == "open_ending"]
    out = [r for r in settlement_results if r.final_status == "out"]

    paired_names: set[tuple[str, str]] = set()
    for r in paired:
        if r.partner_name:
            key = tuple(sorted([r.participant_name, r.partner_name]))
            paired_names.add(key)

    lines = ["最终告白与关系结算完成。"]
    if paired_names:
        pair_texts = [f"{a} & {b}" for a, b in paired_names]
        lines.append(f"成功配对：{'、'.join(pair_texts)}。")
    if open_ending:
        names = list(set(r.participant_name for r in open_ending))
        lines.append(f"开放结局：{'、'.join(names[:4])}。")
    if out:
        names = list(set(r.participant_name for r in out))
        lines.append(f"未配对：{'、'.join(names[:4])}。")

    scores = [r.romance_score for r in settlement_results if r.romance_score > 0]
    if scores:
        avg = sum(scores) / len(scores)
        lines.append(f"平均恋爱可能性评分：{round(avg, 1)} 分。")

    return " ".join(lines)


def derive_scene_10_participant_memories(
    context: dict,
    settlement_results: list[SceneFinalSettlementResult],
) -> list[dict]:
    updates = []
    for result in settlement_results:
        partner_text = result.partner_name or "无"
        summary_text = (
            f"{result.participant_name} 的最终结算：状态 {result.final_status}，"
            f"对象 {partner_text}，恋爱评分 {result.romance_score}。"
        )
        updates.append({
            "participant_id": result.participant_id,
            "memory_type": "scene_takeaway",
            "target_participant_ids": [result.partner_participant_id] if result.partner_participant_id else [],
            "summary": summary_text,
            "importance": clamp(70 + result.romance_score // 5, 50, 100),
            "event_tags": result.event_tags,
        })
    return updates
