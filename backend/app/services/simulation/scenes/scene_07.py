from __future__ import annotations

import hashlib
import random
from collections import defaultdict

from app.models import SceneRun, SimulationRun
from app.schemas.runtime import (
    SceneCompetitionOutcome,
    SceneEvent,
    SceneInvitationResult,
    SceneOrchestratorPlan,
    SceneRefereeResult,
    SceneRelationshipDelta,
    SceneRuntimeExecution,
)
from app.services.simulation.scene_config import SCENE_CONFIG
from app.services.simulation.scene_registry import SCENE_07_CODE
from app.services.simulation.scenes.synthetic_rounds import build_scene_07_synthetic_rounds
from app.services.simulation.service import clamp


def execute_scene_07_runtime(
    simulation: SimulationRun,
    scene_run: SceneRun,
    context: dict,
    input_summary: dict,
    plan: SceneOrchestratorPlan,
) -> SceneRuntimeExecution:
    rng = build_scene_07_rng(simulation.id, scene_run.id)
    invitation_plan = build_scene_07_invitation_plan(context, rng)
    invitation_results, competition_outcomes = resolve_scene_07_invitation_competition(context, invitation_plan)
    relationship_deltas = derive_scene_07_relationship_deltas(invitation_results)
    major_events = summarize_scene_07_events(invitation_results, competition_outcomes)
    scene_summary = summarize_scene_07_results(invitation_results, competition_outcomes)
    next_tension = build_scene_07_next_tension(context, invitation_results, relationship_deltas)
    memory_updates = derive_scene_07_participant_memories(context, relationship_deltas)

    referee_result = SceneRefereeResult(
        scene_id=SCENE_07_CODE,
        scene_summary=scene_summary,
        major_events=major_events,
        relationship_deltas=relationship_deltas,
        pair_date_results=[],
        competition_map=[],
        selection_results=[],
        signal_results=[],
        missed_expectations=[],
        invitation_results=invitation_results,
        competition_outcomes=competition_outcomes,
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
        "rounds": build_scene_07_synthetic_rounds(plan, invitation_results, competition_outcomes),
        "group_state_after_scene": {
            "dominant_topics": ["invitation", "competition", "fallback"],
            "attention_distribution": [],
            "tension_pairs": [],
            "isolated_participants": [],
            "invitation_plan": invitation_plan,
            "scene_level": SCENE_CONFIG[SCENE_07_CODE]["scene_level"],
        },
        "next_tension": referee_result.next_tension,
        "replay_url": f"/simulations/{simulation.id}/scenes/{scene_run.id}",
    }
    return SceneRuntimeExecution(
        input_summary=input_summary,
        orchestrator_plan=plan,
        orchestrator_raw={
            **plan.model_dump(),
            "invitation_plan": invitation_plan,
        },
        messages=[],
        referee_result=referee_result,
        referee_raw={
            **referee_result.model_dump(),
            "invitation_plan": invitation_plan,
        },
        replay_payload=replay_payload,
    )


def build_scene_07_rng(simulation_id: str, scene_run_id: str) -> random.Random:
    seed_text = f"{simulation_id}:{scene_run_id}:{SCENE_07_CODE}"
    seed = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:16], 16)
    return random.Random(seed)


def build_scene_07_candidate_scores(context: dict, inviter_id: str) -> list[dict]:
    candidates = []
    for participant in context["participants"]:
        if participant.id == inviter_id:
            continue
        forward = context["relationship_map"].get((inviter_id, participant.id))
        backward = context["relationship_map"].get((participant.id, inviter_id))
        forward_metrics = forward.metrics if forward else {}
        backward_metrics = backward.metrics if backward else {}
        score = (
            forward_metrics.get("attraction", 0) * 1.2
            + forward_metrics.get("trust", 0)
            + forward_metrics.get("expectation", 0) * 0.9
            + backward_metrics.get("trust", 0) * 0.4
            - forward_metrics.get("anxiety", 0) * 0.25
        )
        candidates.append(
            {
                "inviter_participant_id": inviter_id,
                "target_participant_id": participant.id,
                "score": score,
            }
        )
    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates


def build_scene_07_inviter_priority(context: dict, rng: random.Random) -> list[str]:
    strategy_cards = set(context.get("strategy_cards", []))
    ranked = []
    for participant in context["participants"]:
        personality = participant.editable_personality or {}
        top_candidates = build_scene_07_candidate_scores(context, participant.id)
        top_score = top_candidates[0]["score"] if top_candidates else 0
        priority_score = (
            personality.get("initiative", 50) * 1.0
            + personality.get("emotional_openness", 50) * 0.35
            + top_score * 0.5
            + rng.random() * 0.6
        )
        if "act_first" in strategy_cards:
            priority_score += 12
        ranked.append((priority_score, participant.id))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in ranked]


def build_scene_07_invitation_seed(context: dict) -> dict:
    return {
        participant.id: [
            item["target_participant_id"]
            for item in build_scene_07_candidate_scores(context, participant.id)[:2]
        ]
        for participant in context["participants"]
    }


def build_scene_07_invitation_plan(context: dict, rng: random.Random) -> dict:
    strategy_cards = set(context.get("strategy_cards", []))
    invitation_order = build_scene_07_inviter_priority(context, rng)
    planned = []
    for inviter_id in invitation_order:
        inviter = context["participant_lookup"][inviter_id]
        ranked = build_scene_07_candidate_scores(context, inviter_id)
        if not ranked:
            continue

        if "compete_for_top_choice" in strategy_cards:
            first_pick = ranked[0]
        else:
            top_slice = ranked[: min(2, len(ranked))]
            jittered = sorted(
                (
                    {
                        **item,
                        "score": item["score"] + rng.random() * 0.75,
                    }
                    for item in top_slice
                ),
                key=lambda item: item["score"],
                reverse=True,
            )
            first_pick = jittered[0]

        fallback_target_id = ranked[1]["target_participant_id"] if len(ranked) > 1 else None
        first_target_name = context["participant_lookup"][first_pick["target_participant_id"]].name
        reason = f"{inviter.name} 本轮优先邀约 {first_target_name}。"
        planned.append(
            {
                "inviter_participant_id": inviter_id,
                "first_target_participant_id": first_pick["target_participant_id"],
                "fallback_target_participant_id": fallback_target_id,
                "reason": reason,
            }
        )

    return {
        "scene_id": SCENE_07_CODE,
        "scene_level": SCENE_CONFIG[SCENE_07_CODE]["scene_level"],
        "strategy_cards": sorted(strategy_cards),
        "invitation_order": invitation_order,
        "planned_invitations": planned,
    }


def choose_scene_07_target_winner(
    context: dict,
    target_participant_id: str,
    inviter_ids: list[str],
    rank_lookup: dict[str, int],
) -> str:
    best_inviter = inviter_ids[0]
    best_score = -10**9
    for inviter_id in inviter_ids:
        relation = context["relationship_map"].get((target_participant_id, inviter_id))
        metrics = relation.metrics if relation else {}
        inviter = context["participant_lookup"][inviter_id]
        personality = inviter.editable_personality or {}
        score = (
            metrics.get("trust", 0) * 1.2
            + metrics.get("attraction", 0)
            + metrics.get("expectation", 0) * 0.7
            + personality.get("initiative", 50) * 0.2
            + max(0, 8 - rank_lookup.get(inviter_id, 8)) * 0.3
        )
        if score > best_score:
            best_score = score
            best_inviter = inviter_id
    return best_inviter


def resolve_scene_07_invitation_competition(
    context: dict,
    invitation_plan: dict,
) -> tuple[list[SceneInvitationResult], list[SceneCompetitionOutcome]]:
    strategy_cards = set(invitation_plan.get("strategy_cards", []))
    invitation_order = invitation_plan.get("invitation_order", [])
    rank_lookup = {inviter_id: index for index, inviter_id in enumerate(invitation_order)}
    plan_lookup = {
        item["inviter_participant_id"]: item
        for item in invitation_plan.get("planned_invitations", [])
    }

    target_to_inviters: dict[str, list[str]] = defaultdict(list)
    for inviter_id, item in plan_lookup.items():
        target_id = item.get("first_target_participant_id")
        if target_id:
            target_to_inviters[target_id].append(inviter_id)

    accepted_target_by_inviter: dict[str, str] = {}
    accepted_inviter_by_target: dict[str, str] = {}
    failures: dict[str, int] = defaultdict(int)
    invitation_results: dict[str, dict] = {}
    competition_outcomes: list[SceneCompetitionOutcome] = []

    for target_id, inviters in target_to_inviters.items():
        target_name = context["participant_lookup"][target_id].name
        if len(inviters) == 1:
            inviter_id = inviters[0]
            inviter_name = context["participant_lookup"][inviter_id].name
            accepted_target_by_inviter[inviter_id] = target_id
            accepted_inviter_by_target[target_id] = inviter_id
            invitation_results[inviter_id] = {
                "inviter_participant_id": inviter_id,
                "inviter_name": inviter_name,
                "target_participant_id": target_id,
                "target_name": target_name,
                "has_competition": False,
                "competing_inviter_ids": [],
                "outcome_type": "direct_accept",
                "result_summary": f"{inviter_name} 主动邀约 {target_name} 并获得直接接受。",
                "fallback_used": False,
                "withdrew_after_rejection": False,
                "marginalization_risk": False,
                "key_events": ["邀约被直接接受，关系进入明确推进阶段。"],
                "relationship_deltas": [
                    SceneRelationshipDelta(
                        source_participant_id=inviter_id,
                        target_participant_id=target_id,
                        changes={"trust": 6, "anxiety": -2, "self_esteem": 4, "conflict": -1},
                        reason="主动邀约被接受，推进意愿得到正向反馈。",
                        event_tags=["direct_accept", "scene_07_level_02"],
                    ),
                    SceneRelationshipDelta(
                        source_participant_id=target_id,
                        target_participant_id=inviter_id,
                        changes={"trust": 5, "expectation": 3, "anxiety": -1},
                        reason="接受邀约后关系确定性提升。",
                        event_tags=["direct_accept", "scene_07_level_02"],
                    ),
                ],
                "event_tags": ["direct_accept", "scene_07_level_02"],
            }
            continue

        winner_id = choose_scene_07_target_winner(context, target_id, inviters, rank_lookup)
        winner_name = context["participant_lookup"][winner_id].name
        losers = [inviter_id for inviter_id in inviters if inviter_id != winner_id]
        accepted_target_by_inviter[winner_id] = target_id
        accepted_inviter_by_target[target_id] = winner_id

        competition_outcomes.append(
            SceneCompetitionOutcome(
                target_participant_id=target_id,
                target_name=target_name,
                inviter_participant_ids=inviters,
                winner_participant_id=winner_id,
                winner_name=winner_name,
                loser_participant_ids=losers,
                summary=f"{target_name} 在竞争邀约中选择了 {winner_name}。",
                event_tags=["date_competition", "scene_07_level_02"],
                level_semantic=SCENE_CONFIG[SCENE_07_CODE]["scene_level"],
            )
        )

        invitation_results[winner_id] = {
            "inviter_participant_id": winner_id,
            "inviter_name": winner_name,
            "target_participant_id": target_id,
            "target_name": target_name,
            "has_competition": True,
            "competing_inviter_ids": losers,
            "outcome_type": "accepted_after_competition",
            "result_summary": f"{winner_name} 在竞争邀约中胜出并与 {target_name} 建立约会线。",
            "fallback_used": False,
            "withdrew_after_rejection": False,
            "marginalization_risk": False,
            "key_events": ["竞争邀约胜出，关系主线可见度提升。"],
            "relationship_deltas": [
                SceneRelationshipDelta(
                    source_participant_id=winner_id,
                    target_participant_id=target_id,
                    changes={"trust": 7, "anxiety": -2, "self_esteem": 5, "conflict": 1},
                    reason="在竞争邀约中被选择，主动性获得正反馈。",
                    event_tags=["date_competition_win", "scene_07_level_02"],
                ),
                SceneRelationshipDelta(
                    source_participant_id=target_id,
                    target_participant_id=winner_id,
                    changes={"trust": 6, "expectation": 4},
                    reason="竞争后仍选择该对象，关系判断更集中。",
                    event_tags=["date_competition_win", "scene_07_level_02"],
                ),
            ],
            "event_tags": ["date_competition_win", "scene_07_level_02"],
        }

        for loser_id in losers:
            loser_name = context["participant_lookup"][loser_id].name
            failures[loser_id] += 1
            invitation_results[loser_id] = {
                "inviter_participant_id": loser_id,
                "inviter_name": loser_name,
                "target_participant_id": target_id,
                "target_name": target_name,
                "has_competition": True,
                "competing_inviter_ids": [winner_id],
                "outcome_type": "rejected_due_to_competition",
                "result_summary": f"{loser_name} 在对 {target_name} 的竞争邀约中失利。",
                "fallback_used": False,
                "withdrew_after_rejection": False,
                "marginalization_risk": False,
                "key_events": ["竞争邀约失败，进入 fallback 或退出评估。"],
                "relationship_deltas": [
                    SceneRelationshipDelta(
                        source_participant_id=loser_id,
                        target_participant_id=target_id,
                        changes={"conflict": 4, "anxiety": 7, "self_esteem": -7, "trust": -2},
                        reason="竞争邀约失败，受挫感和不确定性显著上升。",
                        event_tags=["date_competition_loss", "scene_07_level_02"],
                    )
                ],
                "event_tags": ["date_competition_loss", "scene_07_level_02"],
            }

    for inviter_id in invitation_order:
        if inviter_id in accepted_target_by_inviter:
            continue

        base_result = invitation_results.get(inviter_id)
        if base_result is None:
            plan_item = plan_lookup.get(inviter_id)
            if not plan_item:
                continue
            target_id = plan_item["first_target_participant_id"]
            target_name = context["participant_lookup"][target_id].name
            inviter_name = context["participant_lookup"][inviter_id].name
            base_result = {
                "inviter_participant_id": inviter_id,
                "inviter_name": inviter_name,
                "target_participant_id": target_id,
                "target_name": target_name,
                "has_competition": False,
                "competing_inviter_ids": [],
                "outcome_type": "rejected",
                "result_summary": f"{inviter_name} 的邀约未形成有效接受。",
                "fallback_used": False,
                "withdrew_after_rejection": False,
                "marginalization_risk": False,
                "key_events": ["首邀未形成有效推进。"],
                "relationship_deltas": [],
                "event_tags": ["rejected", "scene_07_level_02"],
            }
            invitation_results[inviter_id] = base_result
            failures[inviter_id] += 1

        plan_item = plan_lookup.get(inviter_id, {})
        fallback_target_id = plan_item.get("fallback_target_participant_id")
        can_fallback = (
            "fallback_strategy" in strategy_cards
            and "withdraw_if_rejected" not in strategy_cards
            and fallback_target_id is not None
        )

        if can_fallback and fallback_target_id not in accepted_inviter_by_target:
            fallback_target_name = context["participant_lookup"][fallback_target_id].name
            accepted_target_by_inviter[inviter_id] = fallback_target_id
            accepted_inviter_by_target[fallback_target_id] = inviter_id
            base_result["target_participant_id"] = fallback_target_id
            base_result["target_name"] = fallback_target_name
            base_result["outcome_type"] = "accepted_via_fallback"
            base_result["result_summary"] = (
                f"{base_result['inviter_name']} 在首邀失利后转向 {fallback_target_name}，并获得接受。"
            )
            base_result["fallback_used"] = True
            base_result["key_events"].append("fallback 邀约成功，但关系纯度低于首选成功。")
            base_result["relationship_deltas"].append(
                SceneRelationshipDelta(
                    source_participant_id=inviter_id,
                    target_participant_id=fallback_target_id,
                    changes={"trust": 4, "anxiety": -1, "self_esteem": 2, "conflict": 1},
                    reason="次优邀约成功带来缓冲推进，但稳定性不及首选成功。",
                    event_tags=["fallback_accept", "scene_07_level_02"],
                )
            )
            base_result["relationship_deltas"].append(
                SceneRelationshipDelta(
                    source_participant_id=fallback_target_id,
                    target_participant_id=inviter_id,
                    changes={"trust": 3, "expectation": 2},
                    reason="接受次优邀约，关系可继续观察但确定性一般。",
                    event_tags=["fallback_accept", "scene_07_level_02"],
                )
            )
            base_result["event_tags"] = sorted(set(base_result["event_tags"] + ["fallback_accept"]))
        else:
            if can_fallback and fallback_target_id is not None:
                failures[inviter_id] += 1
            base_result["outcome_type"] = "withdraw_after_rejection"
            base_result["withdrew_after_rejection"] = True
            base_result["result_summary"] = f"{base_result['inviter_name']} 在受挫后选择退出本轮邀约竞争。"
            base_result["key_events"].append("被拒后未继续发起新邀约。")
            base_result["relationship_deltas"].append(
                SceneRelationshipDelta(
                    source_participant_id=inviter_id,
                    target_participant_id=base_result["target_participant_id"],
                    changes={"anxiety": 4, "self_esteem": -4, "conflict": 1},
                    reason="拒绝后主动退出，减少二次冲突但受挫感保留。",
                    event_tags=["withdraw_after_rejection", "scene_07_level_02"],
                )
            )
            base_result["event_tags"] = sorted(set(base_result["event_tags"] + ["withdraw_after_rejection"]))

        base_result["marginalization_risk"] = failures[inviter_id] >= 2
        if base_result["marginalization_risk"]:
            base_result["event_tags"] = sorted(set(base_result["event_tags"] + ["marginalization_risk"]))
            base_result["key_events"].append("连续受挫导致主线关注度下降风险上升。")

    ordered_results = []
    for inviter_id in invitation_order:
        data = invitation_results.get(inviter_id)
        if not data:
            continue
        ordered_results.append(
            SceneInvitationResult(
                inviter_participant_id=data["inviter_participant_id"],
                inviter_name=data["inviter_name"],
                target_participant_id=data["target_participant_id"],
                target_name=data["target_name"],
                has_competition=data["has_competition"],
                competing_inviter_ids=data["competing_inviter_ids"],
                outcome_type=data["outcome_type"],
                result_summary=data["result_summary"],
                fallback_used=data["fallback_used"],
                withdrew_after_rejection=data["withdrew_after_rejection"],
                marginalization_risk=data["marginalization_risk"],
                key_events=data["key_events"],
                relationship_deltas=data["relationship_deltas"],
                event_tags=data["event_tags"],
                level_semantic=SCENE_CONFIG[SCENE_07_CODE]["scene_level"],
            )
        )
    return ordered_results, competition_outcomes


def derive_scene_07_relationship_deltas(
    invitation_results: list[SceneInvitationResult],
) -> list[SceneRelationshipDelta]:
    delta_map: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    reason_map: dict[tuple[str, str], list[str]] = defaultdict(list)
    tag_map: dict[tuple[str, str], set[str]] = defaultdict(set)

    for result in invitation_results:
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


def summarize_scene_07_events(
    invitation_results: list[SceneInvitationResult],
    competition_outcomes: list[SceneCompetitionOutcome],
) -> list[SceneEvent]:
    events = []
    for index, item in enumerate(invitation_results, start=1):
        events.append(
            SceneEvent(
                title=f"邀约 {index}: {item.inviter_name} -> {item.target_name}",
                description=item.result_summary,
                event_tags=item.event_tags,
                source_participant_id=item.inviter_participant_id,
                target_participant_ids=[item.target_participant_id],
                linked_turn_indices=[index],
            )
        )
    base_index = len(invitation_results)
    for offset, outcome in enumerate(competition_outcomes, start=1):
        events.append(
            SceneEvent(
                title=f"竞争结果: {outcome.target_name}",
                description=outcome.summary,
                event_tags=outcome.event_tags,
                source_participant_id=outcome.winner_participant_id,
                target_participant_ids=[outcome.target_participant_id],
                linked_turn_indices=[base_index + offset],
            )
        )
    return events[:8]


def summarize_scene_07_results(
    invitation_results: list[SceneInvitationResult],
    competition_outcomes: list[SceneCompetitionOutcome],
) -> str:
    if not invitation_results:
        return "本场尚未形成有效邀约结果。"

    accepted_direct = sum(1 for item in invitation_results if item.outcome_type == "direct_accept")
    accepted_competition = sum(1 for item in invitation_results if item.outcome_type == "accepted_after_competition")
    accepted_fallback = sum(1 for item in invitation_results if item.outcome_type == "accepted_via_fallback")
    withdrew = sum(1 for item in invitation_results if item.withdrew_after_rejection)
    marginal = sum(1 for item in invitation_results if item.marginalization_risk)

    lines = ["主动邀约竞争完成，关系推进从信号阶段进入行动分化阶段。"]
    lines.append(
        f"直接接受 {accepted_direct} 条，竞争胜出 {accepted_competition} 条，fallback 成功 {accepted_fallback} 条，退出 {withdrew} 人。"
    )
    lines.append(f"本场出现 {len(competition_outcomes)} 组竞争邀约，边缘化风险角色 {marginal} 人。")
    strongest = max(
        invitation_results,
        key=lambda item: sum(abs(value) for delta in item.relationship_deltas for value in delta.changes.values()),
    )
    lines.append(f"最关键邀约线是 {strongest.inviter_name} -> {strongest.target_name}。")
    lines.append("这些结果将在 scene_08_conflict_test 中接受关系稳定性检验。")
    return " ".join(lines)


def build_scene_07_next_tension(
    context: dict,
    invitation_results: list[SceneInvitationResult],
    relationship_deltas: list[SceneRelationshipDelta],
) -> str:
    marginal = next((item for item in invitation_results if item.marginalization_risk), None)
    if marginal:
        return (
            f"scene_08_conflict_test 将优先检验主线关系，{marginal.inviter_name} 因连续受挫出现边缘化趋势，"
            "这会放大其在冲突场里的防御反应。"
        )

    accepted = next(
        (
            item
            for item in invitation_results
            if item.outcome_type in {"accepted_after_competition", "direct_accept", "accepted_via_fallback"}
        ),
        None,
    )
    if accepted:
        return (
            f"scene_08_conflict_test 中，{accepted.inviter_name} 与 {accepted.target_name} 的推进线将面对价值观冲突检验，"
            "竞争后的高期待会放大冲突成本。"
        )

    if relationship_deltas:
        peak = max(relationship_deltas, key=lambda item: item.changes.get("conflict", 0) + item.changes.get("anxiety", 0))
        source_name = context["participant_lookup"].get(peak.source_participant_id)
        target_name = context["participant_lookup"].get(peak.target_participant_id)
        source_text = source_name.name if source_name else peak.source_participant_id
        target_text = target_name.name if target_name else peak.target_participant_id
        return f"scene_08_conflict_test 将放大 {source_text} 与 {target_text} 的不稳定信号，检验关系是否能承受冲突。"

    return "scene_08_conflict_test 将检验邀约后关系是否具备稳定推进能力。"


def derive_scene_07_participant_memories(
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
                "summary": f"{participant.name} 在主动邀约竞争后对 {target_name} 的推进策略发生调整。",
                "importance": clamp(45 + sum(abs(value) for value in top.changes.values()), 35, 93),
                "event_tags": top.event_tags,
            }
        )
    return updates
