from __future__ import annotations

from collections import defaultdict

from app.models import ParticipantProfile
from app.schemas.runtime import AgentTurnPayload, SceneCompetitionMapItem, SceneRelationshipDelta
from app.services.simulation.service import clamp


def build_scene_04_competition_seed_pairs(context: dict) -> list[dict]:
    pairs = []
    participants = context["participants"]
    for source in participants:
        for target in participants:
            if source.id == target.id:
                continue
            forward = context["relationship_map"].get((source.id, target.id))
            if forward is None:
                continue
            metrics = forward.metrics or {}
            score = (
                metrics.get("attraction", 0)
                + metrics.get("curiosity", 0)
                + metrics.get("expectation", 0)
                - metrics.get("anxiety", 0) * 0.4
            )
            pairs.append(
                {
                    "source_participant_id": source.id,
                    "target_participant_id": target.id,
                    "score": int(round(score)),
                }
            )
    pairs.sort(key=lambda item: item["score"], reverse=True)
    return pairs[:6]


def build_scene_04_focus_target(context: dict, speaker_id: str) -> str | None:
    best_target = None
    best_score = -10**9
    for participant in context["participants"]:
        if participant.id == speaker_id:
            continue
        relation = context["relationship_map"].get((speaker_id, participant.id))
        metrics = relation.metrics if relation else {}
        score = (
            metrics.get("attraction", 0) * 1.1
            + metrics.get("curiosity", 0)
            + metrics.get("trust", 0)
            - metrics.get("anxiety", 0) * 0.4
        )
        if score > best_score:
            best_score = score
            best_target = participant.id
    return best_target


def apply_scene_04_strategy_bias(
    context: dict,
    participant: ParticipantProfile,
    counts: dict[str, int],
    last_turn: AgentTurnPayload | None,
) -> float:
    strategy_cards = context.get("strategy_cards", [])
    personality = participant.editable_personality or {}
    bonus = 0.0
    if "hold_center" in strategy_cards:
        bonus += (int(personality.get("self_esteem_stability", 50)) - 50) / 10
        bonus += (int(personality.get("initiative", 50)) - 50) / 16
    if "focus_one_person" in strategy_cards:
        focus_target = build_scene_04_focus_target(context, participant.id)
        if last_turn and focus_target and focus_target in last_turn.target_participant_ids:
            bonus += 4.0
        bonus += max(0.0, 2.0 - counts.get(participant.id, 0) * 0.3)
    if "avoid_competition" in strategy_cards:
        bonus -= (int(personality.get("initiative", 50)) - 50) / 20
        bonus += (int(personality.get("self_esteem_stability", 50)) - 50) / 16
    return bonus


def apply_scene_04_turn_strategy_bias(
    context: dict,
    turn: AgentTurnPayload,
    changes: dict[str, int],
) -> dict[str, int]:
    adjusted = dict(changes)
    strategy_cards = context.get("strategy_cards", [])
    if "hold_center" in strategy_cards:
        adjusted["trust"] = adjusted.get("trust", 0) + 2
        adjusted["anxiety"] = adjusted.get("anxiety", 0) - 1
    if "focus_one_person" in strategy_cards and len(turn.target_participant_ids) == 1:
        adjusted["competition_sense"] = adjusted.get("competition_sense", 0) + 2
        adjusted["anxiety"] = adjusted.get("anxiety", 0) + 1
    if "avoid_competition" in strategy_cards:
        adjusted["competition_sense"] = adjusted.get("competition_sense", 0) - 1
        adjusted["conflict"] = adjusted.get("conflict", 0) - 1
    return adjusted


def derive_scene_04_competition_map(
    context: dict,
    transcript: list[AgentTurnPayload],
    relationship_deltas: list[SceneRelationshipDelta],
) -> list[SceneCompetitionMapItem]:
    target_sources: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for turn in transcript:
        for target_id in turn.target_participant_ids:
            target_sources[target_id][turn.speaker_participant_id] += 1

    delta_lookup = {
        (item.source_participant_id, item.target_participant_id): item
        for item in relationship_deltas
    }
    results = []
    for focus_id, source_counts in target_sources.items():
        sources = sorted(source_counts.items(), key=lambda item: item[1], reverse=True)
        if len(sources) < 2:
            continue
        primary_source, primary_count = sources[0]
        secondary_source, secondary_count = sources[1]
        primary_delta = delta_lookup.get((primary_source, focus_id))
        secondary_delta = delta_lookup.get((secondary_source, focus_id))
        anxiety_pressure = 0
        if primary_delta:
            anxiety_pressure += max(0, primary_delta.changes.get("anxiety", 0))
        if secondary_delta:
            anxiety_pressure += max(0, secondary_delta.changes.get("anxiety", 0))
        score = clamp(35 + (primary_count + secondary_count) * 10 + anxiety_pressure * 2, 0, 100)

        primary_name = context["participant_lookup"].get(primary_source)
        secondary_name = context["participant_lookup"].get(secondary_source)
        focus_name = context["participant_lookup"].get(focus_id)
        source_text = primary_name.name if primary_name else primary_source
        target_text = secondary_name.name if secondary_name else secondary_source
        focus_text = focus_name.name if focus_name else focus_id

        results.append(
            SceneCompetitionMapItem(
                source_participant_id=primary_source,
                target_participant_id=secondary_source,
                focus_participant_id=focus_id,
                competition_sense=score,
                reason=(
                    f"{source_text} 与 {target_text} 在晚餐中都持续向 {focus_text} 投射注意力，"
                    "公开场合下形成了明显竞争。"
                ),
                event_tags=["competition_signal", "group_dinner", "scene_04_level_02"],
            )
        )
    results.sort(key=lambda item: item.competition_sense, reverse=True)
    return results[:6]
