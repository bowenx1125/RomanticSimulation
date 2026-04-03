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
                <li>当前 turn 数：{data.messages.length}</li>
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
