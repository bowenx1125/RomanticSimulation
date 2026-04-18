from __future__ import annotations

from app.schemas.runtime import AgentTurnPayload, SceneOrchestratorPlan


def build_synthetic_round(
    round_index: int,
    phase_label: str | None,
    turns: list[AgentTurnPayload],
) -> dict:
    return {
        "round_index": round_index,
        "phase_label": phase_label,
        "turns": [t.model_dump() for t in turns],
    }


def _phase_label(plan: SceneOrchestratorPlan | None, round_index: int) -> str | None:
    if plan and round_index - 1 < len(plan.phase_outline):
        return plan.phase_outline[round_index - 1]
    return None


def build_scene_05_synthetic_rounds(
    plan: SceneOrchestratorPlan | None,
    selection_results: list,
) -> list[dict]:
    rounds: list[dict] = []
    turn_idx = 0

    r1_turns = []
    for item in selection_results:
        turn_idx += 1
        r1_turns.append(AgentTurnPayload(
            speaker_participant_id=item.selector_participant_id,
            speaker_name=item.selector_name,
            turn_index=turn_idx,
            round_index=1,
            utterance=f"选择了 {item.selected_target_name} 作为交流对象。",
            behavior_summary=f"主动选择 {item.selected_target_name}，准备进入定向交流。",
            intent_tags=["choose_target"],
            target_participant_ids=[item.selected_target_participant_id],
            topic_tags=["selection", "choice"],
        ))
    rounds.append(build_synthetic_round(1, _phase_label(plan, 1), r1_turns))

    r2_turns = []
    for item in selection_results:
        turn_idx += 1
        r2_turns.append(AgentTurnPayload(
            speaker_participant_id=item.selector_participant_id,
            speaker_name=item.selector_name,
            turn_index=turn_idx,
            round_index=2,
            utterance=item.conversation_summary,
            behavior_summary=f"与 {item.selected_target_name} 进行定向交流。",
            intent_tags=["directed_conversation"],
            target_participant_ids=[item.selected_target_participant_id],
            topic_tags=["conversation", item.outcome_type],
        ))
    rounds.append(build_synthetic_round(2, _phase_label(plan, 2), r2_turns))

    r3_turns = []
    for item in selection_results:
        turn_idx += 1
        r3_turns.append(AgentTurnPayload(
            speaker_participant_id=item.selector_participant_id,
            speaker_name=item.selector_name,
            turn_index=turn_idx,
            round_index=3,
            utterance=f"结果：{item.outcome_type}（{item.level_semantic}）",
            behavior_summary="；".join(item.key_events[:2]) if item.key_events else "交流完成。",
            intent_tags=["outcome_reveal", item.outcome_type],
            target_participant_ids=[item.selected_target_participant_id],
            topic_tags=["outcome"],
        ))
    rounds.append(build_synthetic_round(3, _phase_label(plan, 3), r3_turns))

    mismatched = [r for r in selection_results if r.outcome_type in ("mismatch", "one_sided")]
    if mismatched:
        r4_turns = []
        for item in mismatched:
            turn_idx += 1
            r4_turns.append(AgentTurnPayload(
                speaker_participant_id=item.selector_participant_id,
                speaker_name=item.selector_name,
                turn_index=turn_idx,
                round_index=4,
                utterance=f"对 {item.selected_target_name} 的选择未获对等回应，关系出现错位。",
                behavior_summary="错位产生的情绪残留正在发酵。",
                intent_tags=["mismatch_residue"],
                target_participant_ids=[item.selected_target_participant_id],
                topic_tags=["mismatch", "residue"],
            ))
        rounds.append(build_synthetic_round(4, _phase_label(plan, 4), r4_turns))
    else:
        turn_idx += 1
        rounds.append(build_synthetic_round(4, _phase_label(plan, 4), [AgentTurnPayload(
            speaker_participant_id=selection_results[0].selector_participant_id if selection_results else "system",
            speaker_name=selection_results[0].selector_name if selection_results else "系统",
            turn_index=turn_idx,
            round_index=4,
            utterance="本轮未出现明显错位，关系推进方向基本一致。",
            behavior_summary="选择结果整体匹配度较高。",
            intent_tags=["no_mismatch"],
            target_participant_ids=[],
            topic_tags=["recap"],
        )]))

    turn_idx += 1
    recap_text = f"共 {len(selection_results)} 人完成选择。"
    rounds.append(build_synthetic_round(5, _phase_label(plan, 5), [AgentTurnPayload(
        speaker_participant_id=selection_results[0].selector_participant_id if selection_results else "system",
        speaker_name=selection_results[0].selector_name if selection_results else "系统",
        turn_index=turn_idx,
        round_index=5,
        utterance=recap_text,
        behavior_summary="选择阶段结束，关系方向基本明确。",
        intent_tags=["recap"],
        target_participant_ids=[],
        topic_tags=["relationship_recap"],
    )]))

    return rounds


def build_scene_06_synthetic_rounds(
    plan: SceneOrchestratorPlan | None,
    signal_results: list,
    missed_expectations: list,
) -> list[dict]:
    rounds: list[dict] = []
    turn_idx = 0

    r1_turns = []
    for item in signal_results:
        turn_idx += 1
        r1_turns.append(AgentTurnPayload(
            speaker_participant_id=item.sender_participant_id,
            speaker_name=item.sender_name,
            turn_index=turn_idx,
            round_index=1,
            utterance=f"向 {item.recipient_name} 发送私密信号。",
            behavior_summary=item.signal_summary,
            intent_tags=["signal_send"],
            target_participant_ids=[item.recipient_participant_id],
            topic_tags=["private_signal", f"clarity_{item.signal_clarity}"],
        ))
    rounds.append(build_synthetic_round(1, _phase_label(plan, 1), r1_turns))

    r2_turns = []
    for item in signal_results:
        turn_idx += 1
        r2_turns.append(AgentTurnPayload(
            speaker_participant_id=item.recipient_participant_id,
            speaker_name=item.recipient_name,
            turn_index=turn_idx,
            round_index=2,
            utterance=f"收到 {item.sender_name} 的信号，初步反应中。",
            behavior_summary=f"信号清晰度：{item.signal_clarity}",
            intent_tags=["signal_receive", "first_reaction"],
            target_participant_ids=[item.sender_participant_id],
            topic_tags=["delivery", "reaction"],
        ))
    rounds.append(build_synthetic_round(2, _phase_label(plan, 2), r2_turns))

    r3_turns = []
    for item in signal_results:
        turn_idx += 1
        r3_turns.append(AgentTurnPayload(
            speaker_participant_id=item.recipient_participant_id,
            speaker_name=item.recipient_name,
            turn_index=turn_idx,
            round_index=3,
            utterance=item.recipient_interpretation,
            behavior_summary=f"结果：{item.outcome_type}",
            intent_tags=["interpretation", item.outcome_type],
            target_participant_ids=[item.sender_participant_id],
            topic_tags=["reveal", item.outcome_type],
        ))
    rounds.append(build_synthetic_round(3, _phase_label(plan, 3), r3_turns))

    r4_turns = []
    if missed_expectations:
        for item in missed_expectations:
            turn_idx += 1
            r4_turns.append(AgentTurnPayload(
                speaker_participant_id=item.participant_id,
                speaker_name=item.participant_name,
                turn_index=turn_idx,
                round_index=4,
                utterance=f"期待 {item.expected_from_participant_name} 的信号未到，产生落差。",
                behavior_summary=item.reason,
                intent_tags=["expectation_miss"],
                target_participant_ids=[item.expected_from_participant_id],
                topic_tags=["disappointment", "expectation_gap"],
            ))
    else:
        turn_idx += 1
        r4_turns.append(AgentTurnPayload(
            speaker_participant_id=signal_results[0].sender_participant_id if signal_results else "system",
            speaker_name=signal_results[0].sender_name if signal_results else "系统",
            turn_index=turn_idx,
            round_index=4,
            utterance="本轮未出现显著的期待落空情况。",
            behavior_summary="信号传递基本符合预期。",
            intent_tags=["no_miss"],
            target_participant_ids=[],
            topic_tags=["stable"],
        ))
    rounds.append(build_synthetic_round(4, _phase_label(plan, 4), r4_turns))

    turn_idx += 1
    rounds.append(build_synthetic_round(5, _phase_label(plan, 5), [AgentTurnPayload(
        speaker_participant_id=signal_results[0].sender_participant_id if signal_results else "system",
        speaker_name=signal_results[0].sender_name if signal_results else "系统",
        turn_index=turn_idx,
        round_index=5,
        utterance=f"私密信号阶段结束，共 {len(signal_results)} 条信号，{len(missed_expectations)} 个期待落空。",
        behavior_summary="情绪余波将影响下一场邀约。",
        intent_tags=["recap"],
        target_participant_ids=[],
        topic_tags=["emotional_aftermath"],
    )]))

    return rounds


def build_scene_07_synthetic_rounds(
    plan: SceneOrchestratorPlan | None,
    invitation_results: list,
    competition_outcomes: list,
) -> list[dict]:
    rounds: list[dict] = []
    turn_idx = 0

    r1_turns = []
    for item in invitation_results:
        turn_idx += 1
        r1_turns.append(AgentTurnPayload(
            speaker_participant_id=item.inviter_participant_id,
            speaker_name=item.inviter_name,
            turn_index=turn_idx,
            round_index=1,
            utterance=f"向 {item.target_name} 发出邀约。",
            behavior_summary=item.result_summary,
            intent_tags=["invitation_launch"],
            target_participant_ids=[item.target_participant_id],
            topic_tags=["invitation"],
        ))
    rounds.append(build_synthetic_round(1, _phase_label(plan, 1), r1_turns))

    competing = [r for r in invitation_results if r.has_competition]
    r2_turns = []
    if competing:
        for item in competing:
            turn_idx += 1
            r2_turns.append(AgentTurnPayload(
                speaker_participant_id=item.inviter_participant_id,
                speaker_name=item.inviter_name,
                turn_index=turn_idx,
                round_index=2,
                utterance=f"对 {item.target_name} 的邀约遇到竞争。",
                behavior_summary=f"竞争对手：{len(item.competing_inviter_ids)} 人",
                intent_tags=["competition_reveal"],
                target_participant_ids=[item.target_participant_id],
                topic_tags=["competition"],
            ))
    else:
        turn_idx += 1
        r2_turns.append(AgentTurnPayload(
            speaker_participant_id=invitation_results[0].inviter_participant_id if invitation_results else "system",
            speaker_name=invitation_results[0].inviter_name if invitation_results else "系统",
            turn_index=turn_idx,
            round_index=2,
            utterance="本轮邀约未出现撞车竞争。",
            behavior_summary="邀约目标无冲突。",
            intent_tags=["no_competition"],
            target_participant_ids=[],
            topic_tags=["stable"],
        ))
    rounds.append(build_synthetic_round(2, _phase_label(plan, 2), r2_turns))

    r3_turns = []
    if competition_outcomes:
        for item in competition_outcomes:
            turn_idx += 1
            winner_text = item.winner_name or "无明确胜者"
            r3_turns.append(AgentTurnPayload(
                speaker_participant_id=item.target_participant_id,
                speaker_name=item.target_name,
                turn_index=turn_idx,
                round_index=3,
                utterance=item.summary,
                behavior_summary=f"胜者：{winner_text}",
                intent_tags=["competition_resolution"],
                target_participant_ids=item.inviter_participant_ids,
                topic_tags=["resolution"],
            ))
    else:
        turn_idx += 1
        r3_turns.append(AgentTurnPayload(
            speaker_participant_id=invitation_results[0].inviter_participant_id if invitation_results else "system",
            speaker_name=invitation_results[0].inviter_name if invitation_results else "系统",
            turn_index=turn_idx,
            round_index=3,
            utterance="无竞争需要解决，邀约直接进入结果。",
            behavior_summary="竞争解决阶段跳过。",
            intent_tags=["skip"],
            target_participant_ids=[],
            topic_tags=["no_competition"],
        ))
    rounds.append(build_synthetic_round(3, _phase_label(plan, 3), r3_turns))

    fallback_items = [r for r in invitation_results if r.fallback_used or r.withdrew_after_rejection]
    r4_turns = []
    if fallback_items:
        for item in fallback_items:
            turn_idx += 1
            action = "转向备选" if item.fallback_used else "选择退出"
            r4_turns.append(AgentTurnPayload(
                speaker_participant_id=item.inviter_participant_id,
                speaker_name=item.inviter_name,
                turn_index=turn_idx,
                round_index=4,
                utterance=f"邀约被拒后{action}。",
                behavior_summary=item.result_summary,
                intent_tags=["fallback" if item.fallback_used else "withdrawal"],
                target_participant_ids=[item.target_participant_id],
                topic_tags=["fallback", "rejection"],
            ))
    else:
        turn_idx += 1
        r4_turns.append(AgentTurnPayload(
            speaker_participant_id=invitation_results[0].inviter_participant_id if invitation_results else "system",
            speaker_name=invitation_results[0].inviter_name if invitation_results else "系统",
            turn_index=turn_idx,
            round_index=4,
            utterance="本轮未出现被拒后的 fallback 或退出。",
            behavior_summary="邀约结果整体稳定。",
            intent_tags=["stable"],
            target_participant_ids=[],
            topic_tags=["stable"],
        ))
    rounds.append(build_synthetic_round(4, _phase_label(plan, 4), r4_turns))

    turn_idx += 1
    accepted = sum(1 for r in invitation_results if r.outcome_type == "accepted")
    rounds.append(build_synthetic_round(5, _phase_label(plan, 5), [AgentTurnPayload(
        speaker_participant_id=invitation_results[0].inviter_participant_id if invitation_results else "system",
        speaker_name=invitation_results[0].inviter_name if invitation_results else "系统",
        turn_index=turn_idx,
        round_index=5,
        utterance=f"邀约阶段结束，{accepted}/{len(invitation_results)} 个邀约被接受。",
        behavior_summary="邀约竞争结果将影响后续冲突测试。",
        intent_tags=["recap"],
        target_participant_ids=[],
        topic_tags=["outcome_recap"],
    )]))

    return rounds


def build_scene_08_synthetic_rounds(
    plan: SceneOrchestratorPlan | None,
    conflict_test_results: list,
) -> list[dict]:
    rounds: list[dict] = []
    turn_idx = 0

    r1_turns = []
    for item in conflict_test_results:
        turn_idx += 1
        r1_turns.append(AgentTurnPayload(
            speaker_participant_id=item.participant_a_id,
            speaker_name=item.participant_a_name,
            turn_index=turn_idx,
            round_index=1,
            utterance=f"冲突话题揭晓：「{item.conflict_topic}」",
            behavior_summary=item.key_events[0] if item.key_events else "冲突话题公布。",
            intent_tags=["conflict_reveal", f"intensity_{item.conflict_intensity}"],
            target_participant_ids=[item.participant_b_id],
            topic_tags=["conflict_test", item.conflict_topic],
        ))
    rounds.append(build_synthetic_round(1, _phase_label(plan, 1), r1_turns))

    r2_turns = []
    for item in conflict_test_results:
        turn_idx += 1
        r2_turns.append(AgentTurnPayload(
            speaker_participant_id=item.participant_b_id,
            speaker_name=item.participant_b_name,
            turn_index=turn_idx,
            round_index=2,
            utterance=f"对「{item.conflict_topic}」表明立场，双方开始交锋。",
            behavior_summary=f"冲突强度：{item.conflict_intensity}",
            intent_tags=["position_statement", "pushback"],
            target_participant_ids=[item.participant_a_id],
            topic_tags=["value_clash", item.conflict_intensity],
        ))
    rounds.append(build_synthetic_round(2, _phase_label(plan, 2), r2_turns))

    r3_turns = []
    for item in conflict_test_results:
        turn_idx += 1
        r3_turns.append(AgentTurnPayload(
            speaker_participant_id=item.participant_a_id,
            speaker_name=item.participant_a_name,
            turn_index=turn_idx,
            round_index=3,
            utterance=f"冲突升级，核心价值观分歧暴露。强度：{item.conflict_intensity}。",
            behavior_summary=item.key_events[1] if len(item.key_events) > 1 else "冲突持续升级。",
            intent_tags=["escalation", "core_value_clash"],
            target_participant_ids=[item.participant_b_id],
            topic_tags=["escalation"],
        ))
    rounds.append(build_synthetic_round(3, _phase_label(plan, 3), r3_turns))

    r4_turns = []
    for item in conflict_test_results:
        turn_idx += 1
        if item.survived:
            utterance = f"{item.participant_a_name} 与 {item.participant_b_name} 尝试修复，关系存活。"
            tags = ["repair_attempt", "survived"]
        else:
            utterance = f"{item.participant_a_name} 与 {item.participant_b_name} 无法修复，关系崩塌。"
            tags = ["collapse", "failed"]
        r4_turns.append(AgentTurnPayload(
            speaker_participant_id=item.participant_b_id,
            speaker_name=item.participant_b_name,
            turn_index=turn_idx,
            round_index=4,
            utterance=utterance,
            behavior_summary=item.key_events[-1] if item.key_events else item.summary,
            intent_tags=tags,
            target_participant_ids=[item.participant_a_id],
            topic_tags=[item.outcome_type],
        ))
    rounds.append(build_synthetic_round(4, _phase_label(plan, 4), r4_turns))

    r5_turns = []
    for item in conflict_test_results:
        turn_idx += 1
        r5_turns.append(AgentTurnPayload(
            speaker_participant_id=item.participant_a_id,
            speaker_name=item.participant_a_name,
            turn_index=turn_idx,
            round_index=5,
            utterance=item.summary,
            behavior_summary=f"结果：{item.outcome_type}",
            intent_tags=["aftermath", "trust_assessment"],
            target_participant_ids=[item.participant_b_id],
            topic_tags=["aftermath", item.outcome_type],
        ))
    rounds.append(build_synthetic_round(5, _phase_label(plan, 5), r5_turns))

    return rounds


def build_scene_09_synthetic_rounds(
    plan: SceneOrchestratorPlan | None,
    decision_results: list,
) -> list[dict]:
    rounds: list[dict] = []
    turn_idx = 0

    r1_turns = []
    for item in decision_results:
        turn_idx += 1
        r1_turns.append(AgentTurnPayload(
            speaker_participant_id=item.participant_id,
            speaker_name=item.participant_name,
            turn_index=turn_idx,
            round_index=1,
            utterance=item.cost_assessment,
            behavior_summary="冲突后的关系代价评估。",
            intent_tags=["reflection", "cost_assessment"],
            target_participant_ids=[item.final_target_participant_id] if item.final_target_participant_id else [],
            topic_tags=["post_conflict", "reflection"],
        ))
    rounds.append(build_synthetic_round(1, _phase_label(plan, 1), r1_turns))

    r2_turns = []
    for item in decision_results:
        turn_idx += 1
        wavering_text = f"（备选：{'、'.join(item.wavering_targets)}）" if item.wavering_targets else ""
        target_text = item.final_target_name or "无"
        r2_turns.append(AgentTurnPayload(
            speaker_participant_id=item.participant_id,
            speaker_name=item.participant_name,
            turn_index=turn_idx,
            round_index=2,
            utterance=f"重新评估候选对象，当前首选：{target_text}{wavering_text}",
            behavior_summary="在多个对象间权衡利弊。",
            intent_tags=["re_evaluation"],
            target_participant_ids=[item.final_target_participant_id] if item.final_target_participant_id else [],
            topic_tags=["candidate", "evaluation"],
        ))
    rounds.append(build_synthetic_round(2, _phase_label(plan, 2), r2_turns))

    r3_turns = []
    for item in decision_results:
        turn_idx += 1
        r3_turns.append(AgentTurnPayload(
            speaker_participant_id=item.participant_id,
            speaker_name=item.participant_name,
            turn_index=turn_idx,
            round_index=3,
            utterance=item.decision_reason,
            behavior_summary=f"承诺等级：{item.commitment_level}",
            intent_tags=["final_lock", item.commitment_level],
            target_participant_ids=[item.final_target_participant_id] if item.final_target_participant_id else [],
            topic_tags=["decision", item.commitment_level],
        ))
    rounds.append(build_synthetic_round(3, _phase_label(plan, 3), r3_turns))

    r4_turns = []
    for item in decision_results:
        turn_idx += 1
        if item.commitment_level in ("committed", "leaning"):
            utterance = f"向 {item.final_target_name} 释放承诺信号。"
            tags = ["commitment_signal"]
        else:
            utterance = f"选择退出或继续观望。"
            tags = ["withdrawal"]
        r4_turns.append(AgentTurnPayload(
            speaker_participant_id=item.participant_id,
            speaker_name=item.participant_name,
            turn_index=turn_idx,
            round_index=4,
            utterance=utterance,
            behavior_summary="；".join(item.key_events[:2]) if item.key_events else "决策完成。",
            intent_tags=tags,
            target_participant_ids=[item.final_target_participant_id] if item.final_target_participant_id else [],
            topic_tags=[item.commitment_level],
        ))
    rounds.append(build_synthetic_round(4, _phase_label(plan, 4), r4_turns))

    turn_idx += 1
    committed_count = sum(1 for r in decision_results if r.commitment_level == "committed")
    rounds.append(build_synthetic_round(5, _phase_label(plan, 5), [AgentTurnPayload(
        speaker_participant_id=decision_results[0].participant_id if decision_results else "system",
        speaker_name=decision_results[0].participant_name if decision_results else "系统",
        turn_index=turn_idx,
        round_index=5,
        utterance=f"选择夜结束，{committed_count}/{len(decision_results)} 人做出坚定选择。",
        behavior_summary="选择夜结果将决定最终告白对象。",
        intent_tags=["recap"],
        target_participant_ids=[],
        topic_tags=["decision_recap"],
    )]))

    return rounds


def build_scene_10_synthetic_rounds(
    plan: SceneOrchestratorPlan | None,
    settlement_results: list,
) -> list[dict]:
    rounds: list[dict] = []
    turn_idx = 0

    paired = [r for r in settlement_results if r.final_status == "paired"]
    open_ending = [r for r in settlement_results if r.final_status == "open_ending"]
    out = [r for r in settlement_results if r.final_status == "out"]

    r1_turns = []
    for item in settlement_results:
        turn_idx += 1
        partner_text = item.partner_name or "无"
        r1_turns.append(AgentTurnPayload(
            speaker_participant_id=item.participant_id,
            speaker_name=item.participant_name,
            turn_index=turn_idx,
            round_index=1,
            utterance=f"最终告白对象：{partner_text}，恋爱评分：{item.romance_score}",
            behavior_summary=f"状态：{item.final_status}",
            intent_tags=["confession", item.final_status],
            target_participant_ids=[item.partner_participant_id] if item.partner_participant_id else [],
            topic_tags=["final_confession"],
        ))
    rounds.append(build_synthetic_round(1, _phase_label(plan, 1), r1_turns))

    r2_turns = []
    seen_pairs: set[tuple[str, str]] = set()
    for item in paired + open_ending:
        if item.partner_participant_id:
            pair_key = tuple(sorted([item.participant_id, item.partner_participant_id]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
        turn_idx += 1
        r2_turns.append(AgentTurnPayload(
            speaker_participant_id=item.participant_id,
            speaker_name=item.participant_name,
            turn_index=turn_idx,
            round_index=2,
            utterance=f"与 {item.partner_name or '无'} 的关系确认：{item.final_status}。",
            behavior_summary="门槛达标" if item.level_requirement_met else "未达配对门槛",
            intent_tags=["mutual_confirmation", item.final_status],
            target_participant_ids=[item.partner_participant_id] if item.partner_participant_id else [],
            topic_tags=["confirmation"],
        ))
    if not r2_turns:
        turn_idx += 1
        r2_turns.append(AgentTurnPayload(
            speaker_participant_id=settlement_results[0].participant_id if settlement_results else "system",
            speaker_name=settlement_results[0].participant_name if settlement_results else "系统",
            turn_index=turn_idx,
            round_index=2,
            utterance="无互选配对产生。",
            behavior_summary="所有关系未达配对标准。",
            intent_tags=["no_pair"],
            target_participant_ids=[],
            topic_tags=["no_match"],
        ))
    rounds.append(build_synthetic_round(2, _phase_label(plan, 2), r2_turns))

    r3_turns = []
    for item in settlement_results:
        turn_idx += 1
        reasons = item.success_reasons if item.success_reasons else item.failure_reasons
        reason_text = "；".join(reasons[:2]) if reasons else "无额外说明。"
        r3_turns.append(AgentTurnPayload(
            speaker_participant_id=item.participant_id,
            speaker_name=item.participant_name,
            turn_index=turn_idx,
            round_index=3,
            utterance=f"结算状态：{item.final_status}。原因：{reason_text}",
            behavior_summary=f"恋爱评分：{item.romance_score}",
            intent_tags=["settlement", item.final_status],
            target_participant_ids=[item.partner_participant_id] if item.partner_participant_id else [],
            topic_tags=["settlement"],
        ))
    rounds.append(build_synthetic_round(3, _phase_label(plan, 3), r3_turns))

    r4_turns = []
    for item in settlement_results:
        if not item.key_turning_points:
            continue
        turn_idx += 1
        r4_turns.append(AgentTurnPayload(
            speaker_participant_id=item.participant_id,
            speaker_name=item.participant_name,
            turn_index=turn_idx,
            round_index=4,
            utterance=item.relationship_story[:200],
            behavior_summary="；".join(item.key_turning_points[:2]),
            intent_tags=["story_output", "turning_points"],
            target_participant_ids=[item.partner_participant_id] if item.partner_participant_id else [],
            topic_tags=["story", "turning_points"],
        ))
    if not r4_turns:
        turn_idx += 1
        r4_turns.append(AgentTurnPayload(
            speaker_participant_id=settlement_results[0].participant_id if settlement_results else "system",
            speaker_name=settlement_results[0].participant_name if settlement_results else "系统",
            turn_index=turn_idx,
            round_index=4,
            utterance="关系故事输出完成。",
            behavior_summary="所有关系线的故事已生成。",
            intent_tags=["story_complete"],
            target_participant_ids=[],
            topic_tags=["story"],
        ))
    rounds.append(build_synthetic_round(4, _phase_label(plan, 4), r4_turns))

    turn_idx += 1
    paired_count = len(set(
        tuple(sorted([r.participant_id, r.partner_participant_id]))
        for r in paired if r.partner_participant_id
    ))
    rounds.append(build_synthetic_round(5, _phase_label(plan, 5), [AgentTurnPayload(
        speaker_participant_id=settlement_results[0].participant_id if settlement_results else "system",
        speaker_name=settlement_results[0].participant_name if settlement_results else "系统",
        turn_index=turn_idx,
        round_index=5,
        utterance=f"最终结算完成：{paired_count} 对配对，{len(open_ending)} 人开放结局，{len(out)} 人未配对。",
        behavior_summary="模拟结束，所有关系线已完成最终结算。",
        intent_tags=["final_recap"],
        target_participant_ids=[],
        topic_tags=["final_recap"],
    )]))

    return rounds
