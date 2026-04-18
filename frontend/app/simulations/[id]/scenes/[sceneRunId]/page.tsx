"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { getSceneReplay, SceneReplay } from "../../../../../lib/api";
import {
  formatMetricLabel,
  formatReasonText,
  formatSceneTitle,
  formatStatusLabel,
} from "../../../../../lib/presentation";

export default function SceneReplayPage() {
  const params = useParams<{ id: string; sceneRunId: string }>();
  const simulationId = params.id;
  const sceneRunId = params.sceneRunId;
  const [data, setData] = useState<SceneReplay | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let stopped = false;

    async function load() {
      try {
        const nextData = await getSceneReplay(simulationId, sceneRunId);
        if (!stopped) {
          setData(nextData);
          setError("");
        }
      } catch (loadError) {
        if (!stopped) {
          setError(loadError instanceof Error ? loadError.message : "加载 scene 回放失败");
        }
      }
    }

    load();
    const timer = window.setInterval(load, 3000);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [sceneRunId, simulationId]);

  const participantNameMap = useMemo(
    () =>
      Object.fromEntries(
        (data?.scene_plan?.participants ?? []).map((participant) => [participant.participant_id, participant.name]),
      ),
    [data],
  );

  return (
    <main className="app-shell">
      <section className="app-header">
        <div>
          <span className="eyebrow">Scene Replay</span>
          <h1>{formatSceneTitle(data?.scene_code ?? "scene_replay")}</h1>
          <p>按轮次展开 orchestrator 计划、真实 transcript、事件裁决和 pairwise graph 变化。</p>
        </div>
        <div className="header-actions">
          <Link className="ghost-link" href={`/simulations/${simulationId}`}>
            返回总览
          </Link>
          <Link className="ghost-link" href={`/simulations/${simulationId}/relationships`}>
            关系图谱
          </Link>
        </div>
      </section>

      {error ? <p className="inline-error">{error}</p> : null}
      {!data ? (
        <section className="content-card">
          <p>正在加载 scene replay...</p>
        </section>
      ) : (
        <>
          <section className="overview-grid">
            <article className="content-card overview-hero-card">
              <span className={`status-pill status-${data.status}`}>{formatStatusLabel(data.status)}</span>
              <h2>{data.summary ?? data.scene_code}</h2>
              <p>{data.next_tension ?? "等待下一场 tension。"}</p>
            </article>
            <article className="content-card compact-stat-card">
              <h3>轮次范围</h3>
              <ul className="bullet-metrics">
                <li>当前 turn 数：{data.messages.length || data.rounds.reduce((sum, r) => sum + r.turns.length, 0)}</li>
                <li>计划最少：{data.scene_plan?.min_turns ?? "-"}</li>
                <li>计划最多：{data.scene_plan?.max_turns ?? "-"}</li>
              </ul>
            </article>
          </section>

          {data.pair_date_results.length ? (
            <section className="content-card">
              <div className="section-heading">
                <div>
                  <span className="eyebrow subtle">Random Date Pairs</span>
                  <h2>Scene 03 配对结果</h2>
                </div>
              </div>
              <div className="timeline-list">
                {data.pair_date_results.map((pair) => (
                  <article key={`pair-${pair.pair_index}`} className="timeline-card static">
                    <strong>
                      Pair {pair.pair_index} · {pair.participant_names.join(" x ")}
                    </strong>
                    <p>{pair.summary}</p>
                    <div className="metric-chip-row">
                      <span className="metric-chip">spark: {pair.spark_level}</span>
                      <span className="metric-chip">level: {pair.level_semantic}</span>
                      <span className="metric-chip">
                        {pair.affects_future_candidate ? "进入后续候选" : "暂不进入候选"}
                      </span>
                    </div>
                    <ul className="reason-list">
                      {pair.key_events.map((event, index) => (
                        <li key={`${pair.pair_index}-event-${index}`}>{event}</li>
                      ))}
                    </ul>
                  </article>
                ))}
                {data.group_state_after_scene.matching_plan?.waiting_participant_id ? (
                  <article className="timeline-card static">
                    <strong>轮空观察位</strong>
                    <p>
                      {participantNameMap[data.group_state_after_scene.matching_plan.waiting_participant_id] ??
                        data.group_state_after_scene.matching_plan.waiting_participant_id}
                      本轮轮空，情绪变化主要来自旁观结果。
                    </p>
                  </article>
                ) : null}
              </div>
            </section>
          ) : null}

          {data.competition_map.length ? (
            <section className="content-card">
              <div className="section-heading">
                <div>
                  <span className="eyebrow subtle">Competition Map</span>
                  <h2>Scene 04 竞争图谱</h2>
                </div>
              </div>
              <div className="timeline-list">
                {data.competition_map.map((item) => (
                  <article
                    key={`${item.source_participant_id}-${item.target_participant_id}-${item.focus_participant_id ?? "none"}`}
                    className="timeline-card static"
                  >
                    <strong>
                      {participantNameMap[item.source_participant_id] ?? item.source_participant_id}
                      {" vs "}
                      {participantNameMap[item.target_participant_id] ?? item.target_participant_id}
                    </strong>
                    <p>{item.reason}</p>
                    <div className="metric-chip-row">
                      <span className="metric-chip">competition_sense: {item.competition_sense}</span>
                      {item.focus_participant_id ? (
                        <span className="metric-chip">
                          focus: {participantNameMap[item.focus_participant_id] ?? item.focus_participant_id}
                        </span>
                      ) : null}
                    </div>
                    <div className="tag-row">
                      {item.event_tags.map((tag) => (
                        <span key={tag} className="soft-tag muted">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          {data.selection_results.length ? (
            <section className="content-card">
              <div className="section-heading">
                <div>
                  <span className="eyebrow subtle">Selection Results</span>
                  <h2>Scene 05 选择结果</h2>
                </div>
              </div>
              <div className="timeline-list">
                {data.selection_results.map((item) => (
                  <article
                    key={`${item.selector_participant_id}-${item.selected_target_participant_id}`}
                    className="timeline-card static"
                  >
                    <strong>
                      {item.selector_name}{" -> "}{item.selected_target_name}
                    </strong>
                    <p>{item.conversation_summary}</p>
                    <div className="metric-chip-row">
                      <span className="metric-chip">outcome: {item.outcome_type}</span>
                      <span className="metric-chip">level: {item.level_semantic}</span>
                    </div>
                    <ul className="reason-list">
                      {item.key_events.map((event, index) => (
                        <li key={`${item.selector_participant_id}-event-${index}`}>{event}</li>
                      ))}
                    </ul>
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          {data.signal_results.length ? (
            <section className="content-card">
              <div className="section-heading">
                <div>
                  <span className="eyebrow subtle">Private Signals</span>
                  <h2>Scene 06 私密信号结果</h2>
                </div>
              </div>
              <div className="timeline-list">
                {data.signal_results.map((item) => (
                  <article
                    key={`${item.sender_participant_id}-${item.recipient_participant_id}-${item.outcome_type}`}
                    className="timeline-card static"
                  >
                    <strong>
                      {item.sender_name}{" -> "}{item.recipient_name}
                    </strong>
                    <p>{item.signal_summary}</p>
                    <p className="card-footnote">接收解读：{item.recipient_interpretation}</p>
                    <div className="metric-chip-row">
                      <span className="metric-chip">clarity: {item.signal_clarity}</span>
                      <span className="metric-chip">outcome: {item.outcome_type}</span>
                      <span className="metric-chip">level: {item.level_semantic}</span>
                    </div>
                    <ul className="reason-list">
                      {item.key_events.map((event, index) => (
                        <li key={`${item.sender_participant_id}-signal-event-${index}`}>{event}</li>
                      ))}
                    </ul>
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          {data.missed_expectations.length ? (
            <section className="content-card">
              <div className="section-heading">
                <div>
                  <span className="eyebrow subtle">Expectation Miss</span>
                  <h2>Scene 06 期待落空结果</h2>
                </div>
              </div>
              <div className="timeline-list">
                {data.missed_expectations.map((item) => (
                  <article
                    key={`${item.participant_id}-${item.expected_from_participant_id}`}
                    className="timeline-card static"
                  >
                    <strong>
                      {item.participant_name} 未收到 {item.expected_from_participant_name} 的私密信号
                    </strong>
                    <p>{item.reason}</p>
                    <div className="metric-chip-row">
                      <span className="metric-chip">expectation_gap: +{item.expectation_gap_delta}</span>
                      <span className="metric-chip">disappointment: +{item.disappointment_delta}</span>
                      <span className="metric-chip">trust: {item.trust_delta}</span>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          {data.invitation_results.length ? (
            <section className="content-card">
              <div className="section-heading">
                <div>
                  <span className="eyebrow subtle">Invitation Results</span>
                  <h2>Scene 07 邀约结果</h2>
                </div>
              </div>
              <div className="timeline-list">
                {data.invitation_results.map((item) => (
                  <article
                    key={`${item.inviter_participant_id}-${item.target_participant_id}-${item.outcome_type}`}
                    className="timeline-card static"
                  >
                    <strong>
                      {item.inviter_name}{" -> "}{item.target_name}
                    </strong>
                    <p>{item.result_summary}</p>
                    <div className="metric-chip-row">
                      <span className="metric-chip">outcome: {item.outcome_type}</span>
                      <span className="metric-chip">competition: {item.has_competition ? "yes" : "no"}</span>
                      {item.fallback_used ? <span className="metric-chip">fallback used</span> : null}
                      {item.withdrew_after_rejection ? <span className="metric-chip">withdrew</span> : null}
                      {item.marginalization_risk ? <span className="metric-chip">marginalization risk</span> : null}
                    </div>
                    <ul className="reason-list">
                      {item.key_events.map((event, index) => (
                        <li key={`${item.inviter_participant_id}-invite-event-${index}`}>{event}</li>
                      ))}
                    </ul>
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          {data.competition_outcomes.length ? (
            <section className="content-card">
              <div className="section-heading">
                <div>
                  <span className="eyebrow subtle">Competition Outcomes</span>
                  <h2>Scene 07 竞争结果</h2>
                </div>
              </div>
              <div className="timeline-list">
                {data.competition_outcomes.map((item) => (
                  <article
                    key={`${item.target_participant_id}-${item.winner_participant_id ?? "none"}`}
                    className="timeline-card static"
                  >
                    <strong>{item.target_name}</strong>
                    <p>{item.summary}</p>
                    <div className="metric-chip-row">
                      {item.winner_name ? <span className="metric-chip">winner: {item.winner_name}</span> : null}
                      <span className="metric-chip">losers: {item.loser_participant_ids.length}</span>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          {data.conflict_test_results?.length ? (
            <section className="content-card">
              <div className="section-heading">
                <div>
                  <span className="eyebrow subtle">Conflict Test</span>
                  <h2>Scene 08 冲突压力测试结果</h2>
                </div>
              </div>
              <div className="timeline-list">
                {data.conflict_test_results.map((item) => (
                  <article
                    key={`conflict-${item.pair_index}-${item.participant_a_id}-${item.participant_b_id}`}
                    className="timeline-card static"
                  >
                    <strong>
                      Pair {item.pair_index} · {item.participant_a_name} vs {item.participant_b_name}
                    </strong>
                    <p>{item.summary}</p>
                    <div className="metric-chip-row">
                      <span className="metric-chip">话题: {item.conflict_topic}</span>
                      <span className="metric-chip">强度: {item.conflict_intensity}</span>
                      <span className="metric-chip">outcome: {item.outcome_type}</span>
                      <span className={`metric-chip ${item.survived ? "" : "metric-chip-danger"}`}>
                        {item.survived ? "关系存活 ✓" : "关系崩塌 ✗"}
                      </span>
                    </div>
                    <ul className="reason-list">
                      {item.key_events.map((event, index) => (
                        <li key={`conflict-${item.pair_index}-event-${index}`}>{event}</li>
                      ))}
                    </ul>
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          {data.decision_results?.length ? (
            <section className="content-card">
              <div className="section-heading">
                <div>
                  <span className="eyebrow subtle">Decision Night</span>
                  <h2>Scene 09 关键选择夜结果</h2>
                </div>
              </div>
              <div className="timeline-list">
                {data.decision_results.map((item) => (
                  <article
                    key={`decision-${item.participant_id}`}
                    className="timeline-card static"
                  >
                    <strong>
                      {item.participant_name}{" → "}{item.final_target_name ?? "未选择"}
                    </strong>
                    <p>{item.decision_reason}</p>
                    <p className="card-footnote">代价评估：{item.cost_assessment}</p>
                    <div className="metric-chip-row">
                      <span className="metric-chip">承诺等级: {item.commitment_level}</span>
                      <span className="metric-chip">outcome: {item.event_tags.join(", ") || "—"}</span>
                      {item.wavering_targets.length ? (
                        <span className="metric-chip">摇摆对象: {item.wavering_targets.join(", ")}</span>
                      ) : null}
                    </div>
                    <ul className="reason-list">
                      {item.key_events.map((event, index) => (
                        <li key={`decision-${item.participant_id}-event-${index}`}>{event}</li>
                      ))}
                    </ul>
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          {data.final_settlement_results?.length ? (
            <section className="content-card">
              <div className="section-heading">
                <div>
                  <span className="eyebrow subtle">Final Settlement</span>
                  <h2>Scene 10 最终结算结果</h2>
                </div>
              </div>
              <div className="timeline-list">
                {data.final_settlement_results.map((item) => (
                  <article
                    key={`settlement-${item.participant_id}`}
                    className="timeline-card static"
                  >
                    <strong>
                      {item.participant_name}
                      {item.partner_name ? ` ❤ ${item.partner_name}` : " — 未配对"}
                    </strong>
                    <p>{item.relationship_story}</p>
                    <div className="metric-chip-row">
                      <span className="metric-chip">状态: {item.final_status}</span>
                      <span className="metric-chip">恋爱评分: {item.romance_score}</span>
                      <span className="metric-chip">
                        {item.level_requirement_met ? "达标 ✓" : "未达标 ✗"}
                      </span>
                    </div>
                    {item.key_turning_points.length ? (
                      <>
                        <p className="card-footnote" style={{ marginTop: "0.5rem" }}>关键转折点：</p>
                        <ul className="reason-list">
                          {item.key_turning_points.map((point, index) => (
                            <li key={`settlement-${item.participant_id}-tp-${index}`}>{point}</li>
                          ))}
                        </ul>
                      </>
                    ) : null}
                    {item.success_reasons.length ? (
                      <>
                        <p className="card-footnote" style={{ marginTop: "0.5rem" }}>成功原因：</p>
                        <ul className="reason-list">
                          {item.success_reasons.map((reason, index) => (
                            <li key={`settlement-${item.participant_id}-sr-${index}`}>{reason}</li>
                          ))}
                        </ul>
                      </>
                    ) : null}
                    {item.failure_reasons.length ? (
                      <>
                        <p className="card-footnote" style={{ marginTop: "0.5rem" }}>失败原因：</p>
                        <ul className="reason-list">
                          {item.failure_reasons.map((reason, index) => (
                            <li key={`settlement-${item.participant_id}-fr-${index}`}>{reason}</li>
                          ))}
                        </ul>
                      </>
                    ) : null}
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          {data.scene_plan ? (
            <section className="content-card">
              <div className="section-heading">
                <div>
                  <span className="eyebrow subtle">Orchestrator</span>
                  <h2>场景计划</h2>
                </div>
              </div>
              <div className="plan-grid">
                <article className="plan-block">
                  <strong>Scene Goal</strong>
                  <p>{data.scene_plan.scene_goal}</p>
                </article>
                <article className="plan-block">
                  <strong>Scene Frame</strong>
                  <p>{data.scene_plan.scene_frame}</p>
                </article>
                <article className="plan-block">
                  <strong>Phase Outline</strong>
                  <ul className="reason-list">
                    {data.scene_plan.phase_outline.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </article>
                <article className="plan-block">
                  <strong>Participant Directives</strong>
                  <ul className="reason-list">
                    {data.scene_plan.participant_directives.map((directive) => (
                      <li key={`${directive.participant_id}-${directive.directive}`}>
                        {participantNameMap[directive.participant_id] ?? directive.participant_id}: {directive.directive}
                      </li>
                    ))}
                  </ul>
                </article>
              </div>
            </section>
          ) : null}

          <section className="content-card">
            <div className="section-heading">
              <div>
                <span className="eyebrow subtle">Rounds</span>
                <h2>按 round 回放</h2>
              </div>
            </div>
            <div className="transcript-list">
              {data.rounds.map((round) => (
                <article key={round.round_index} className="content-card inset-card">
                  <div className="timeline-card-top">
                    <strong>Round {round.round_index}</strong>
                    {round.phase_label ? <span className="soft-tag">{round.phase_label}</span> : null}
                  </div>
                  <div className="transcript-list">
                    {round.turns.map((message) => (
                      <article
                        key={`${message.turn_index}-${message.speaker_participant_id}`}
                        className="message-card"
                      >
                        <div className="timeline-card-top">
                          <strong>
                            Turn {message.turn_index} · {message.speaker_name}
                          </strong>
                          <div className="tag-row">
                            {message.intent_tags.map((tag) => (
                              <span key={tag} className="soft-tag muted">
                                {tag}
                              </span>
                            ))}
                          </div>
                        </div>
                        <p className="utterance-block">“{message.utterance}”</p>
                        <p>{message.behavior_summary}</p>
                        <div className="metric-chip-row">
                          {message.target_participant_ids.map((targetId) => (
                            <span key={targetId} className="metric-chip">
                              指向 {participantNameMap[targetId] ?? targetId}
                            </span>
                          ))}
                          {message.topic_tags.map((topic) => (
                            <span key={topic} className="metric-chip">
                              {topic}
                            </span>
                          ))}
                        </div>
                        {message.self_observation ? (
                          <p className="card-footnote">Self observation: {message.self_observation}</p>
                        ) : null}
                      </article>
                    ))}
                  </div>
                </article>
              ))}
              {!data.rounds.length ? (
                <article className="content-card inset-card">
                  <p>本场以配对结果为主，没有多轮逐 turn transcript。</p>
                </article>
              ) : null}
            </div>
          </section>

          <section className="two-panel-layout">
            <article className="content-card">
              <div className="section-heading">
                <div>
                  <span className="eyebrow subtle">Events</span>
                  <h2>关键事件</h2>
                </div>
              </div>
              <div className="timeline-list">
                {data.major_events.map((event) => (
                  <article key={`${event.title}-${event.linked_turn_indices.join("-")}`} className="timeline-card static">
                    <strong>{event.title}</strong>
                    <p>{event.description ?? "本轮互动已被裁决为关键事件。"}</p>
                    <div className="tag-row">
                      {event.event_tags.map((tag) => (
                        <span key={tag} className="soft-tag">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </article>
                ))}
              </div>
            </article>

            <article className="content-card">
              <div className="section-heading">
                <div>
                  <span className="eyebrow subtle">Speaker Flow</span>
                  <h2>多人切换与群体状态</h2>
                </div>
              </div>
              <div className="timeline-list">
                {data.speaker_switch_summary.map((item) => (
                  <article key={item.participant_id} className="timeline-card static">
                    <strong>{item.name}</strong>
                    <p>本场发言 {item.turn_count} 次，被点名或承接 {item.addressed_count} 次。</p>
                  </article>
                ))}
                <article className="timeline-card static">
                  <strong>Dominant Topics</strong>
                  <div className="tag-row">
                    {(data.group_state_after_scene.dominant_topics ?? []).map((topic) => (
                      <span key={topic} className="soft-tag">
                        {topic}
                      </span>
                    ))}
                  </div>
                </article>
                <article className="timeline-card static">
                  <strong>Tension Pairs</strong>
                  <ul className="reason-list">
                    {(data.group_state_after_scene.tension_pairs ?? []).map((pair) => (
                      <li key={pair.names.join("-")}>
                        {pair.names.join(" / ")} · pressure {pair.pressure}
                      </li>
                    ))}
                  </ul>
                </article>
              </div>
            </article>
          </section>

          <section className="content-card">
            <div className="section-heading">
              <div>
                <span className="eyebrow subtle">Graph Deltas</span>
                <h2>关系边变化</h2>
              </div>
            </div>
            <div className="timeline-list">
              {data.relationship_deltas.map((delta) => (
                <article
                  key={`${delta.source_participant_id}-${delta.target_participant_id}`}
                  className="timeline-card static"
                >
                  <strong>
                    {participantNameMap[delta.source_participant_id] ?? delta.source_participant_id}
                    {" → "}
                    {participantNameMap[delta.target_participant_id] ?? delta.target_participant_id}
                  </strong>
                  <div className="metric-chip-row">
                    {Object.entries(delta.changes).map(([key, value]) => (
                      <span key={key} className="metric-chip">
                        {formatMetricLabel(key)}: {value > 0 ? "+" : ""}
                        {value}
                      </span>
                    ))}
                  </div>
                  <p>{formatReasonText(delta.reason)}</p>
                </article>
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
