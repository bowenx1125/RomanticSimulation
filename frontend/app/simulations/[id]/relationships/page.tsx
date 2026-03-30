"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  getSimulationRelationshipGraph,
  SimulationRelationshipGraph,
} from "../../../../lib/api";
import { formatCastRole, formatMetricLabel, formatStatusLabel } from "../../../../lib/presentation";

export default function RelationshipsPage() {
  const params = useParams<{ id: string }>();
  const simulationId = params.id;
  const [data, setData] = useState<SimulationRelationshipGraph | null>(null);
  const [error, setError] = useState("");
  const [selectedSourceId, setSelectedSourceId] = useState<string>("all");

  useEffect(() => {
    let stopped = false;

    async function load() {
      try {
        const nextData = await getSimulationRelationshipGraph(simulationId);
        if (!stopped) {
          setData(nextData);
          setError("");
        }
      } catch (loadError) {
        if (!stopped) {
          setError(loadError instanceof Error ? loadError.message : "加载关系面板失败");
        }
      }
    }

    load();
    const timer = window.setInterval(load, 3000);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [simulationId]);

  const grouped = useMemo(() => {
    const map = new Map<string, SimulationRelationshipGraph["edges"]>();
    (data?.edges ?? []).forEach((relationship) => {
      if (selectedSourceId !== "all" && relationship.source_participant_id !== selectedSourceId) {
        return;
      }
      const current = map.get(relationship.source_participant_id) ?? [];
      current.push(relationship);
      map.set(relationship.source_participant_id, current);
    });
    return map;
  }, [data, selectedSourceId]);

  return (
    <main className="app-shell">
      <section className="app-header">
        <div>
          <span className="eyebrow">Relationships</span>
          <h1>Pairwise Relationship Graph</h1>
          <p>这里展示的是 A→B、B→A 分离的真实关系边，而不是把所有关系压成一个“对主角的温度条”。</p>
        </div>
        <div className="header-actions">
          <Link className="ghost-link" href={`/simulations/${simulationId}`}>
            返回总览
          </Link>
          <Link className="ghost-link" href={`/simulations/${simulationId}/personalities`}>
            人格面板
          </Link>
        </div>
      </section>

      {error ? <p className="inline-error">{error}</p> : null}
      {!data ? (
        <section className="content-card">
          <p>正在加载 relationships...</p>
        </section>
      ) : (
        <>
          <section className="participant-list-panel">
            {data.nodes.map((participant) => (
              <article key={participant.participant_id} className="participant-mini-card">
                <div className="timeline-card-top">
                  <strong>{participant.name}</strong>
                  <span className="soft-tag">{formatCastRole(participant.cast_role)}</span>
                </div>
                <p>总连接强度 {participant.total_score}，流出 {participant.outgoing_score} / 流入 {participant.incoming_score}</p>
              </article>
            ))}
          </section>

          <section className="overview-grid">
            <article className="content-card compact-stat-card">
              <h3>Group Tension</h3>
              <p>{data.group_tension_summary ?? "等待群体张力形成。"}</p>
            </article>
            <article className="content-card compact-stat-card">
              <h3>Hot Pairs</h3>
              <div className="timeline-list compact">
                {data.hot_pairs.map((pair) => (
                  <article
                    key={`${pair.participant_a_id}-${pair.participant_b_id}`}
                    className="timeline-card static compact-pair-card"
                  >
                    <div className="timeline-card-top">
                      <strong>
                        {pair.participant_a_name} ↔ {pair.participant_b_name}
                      </strong>
                      <span className="soft-tag">score {pair.combined_score}</span>
                    </div>
                    <p>{pair.summary}</p>
                  </article>
                ))}
              </div>
            </article>
            <article className="content-card compact-stat-card">
              <h3>筛选 Source</h3>
              <select
                className="field-input"
                value={selectedSourceId}
                onChange={(event) => setSelectedSourceId(event.target.value)}
              >
                <option value="all">all</option>
                {data.nodes.map((participant) => (
                  <option key={participant.participant_id} value={participant.participant_id}>
                    {participant.name}
                  </option>
                ))}
              </select>
            </article>
          </section>

          <section className="relationship-page-grid">
            {Array.from(grouped.entries()).map(([sourceId, edges]) => {
              const source = data.nodes.find((participant) => participant.participant_id === sourceId);
              return (
                <article key={sourceId} className="relationship-detail-card">
                  <div className="timeline-card-top">
                    <div>
                      <span className="eyebrow subtle">Source Participant</span>
                      <h2>{source?.name ?? sourceId}</h2>
                    </div>
                  </div>

                  <div className="relationship-edge-list">
                    {edges.map((relationship) => (
                      <div
                        key={`${relationship.source_participant_id}-${relationship.target_participant_id}`}
                        className="relationship-edge-card"
                      >
                        <div className="timeline-card-top">
                          <strong>{relationship.target_name}</strong>
                          <span className={`trend-pill trend-${relationship.trend}`}>
                            {formatStatusLabel(relationship.trend)}
                          </span>
                        </div>
                        <p className="relationship-status-line">
                          当前状态：<strong>{formatStatusLabel(relationship.status)}</strong>
                        </p>
                        {relationship.strongest_metric ? (
                          <p className="card-footnote">最强信号：{formatMetricLabel(relationship.strongest_metric)}</p>
                        ) : null}
                        <div className="metric-bar-list">
                          {data.strongest_signals
                            .find(
                              (signal) =>
                                signal.source_participant_id === relationship.source_participant_id &&
                                signal.target_participant_id === relationship.target_participant_id,
                            )
                            ?.surface_metrics
                            ? Object.entries(
                                data.strongest_signals.find(
                                  (signal) =>
                                    signal.source_participant_id === relationship.source_participant_id &&
                                    signal.target_participant_id === relationship.target_participant_id,
                                )!.surface_metrics,
                              ).map(([metric, value]) => (
                            <div key={metric} className="metric-bar-row">
                              <div className="metric-bar-header">
                                <span>{formatMetricLabel(metric)}</span>
                                <strong>{value}</strong>
                              </div>
                              <div className="metric-bar-track">
                                <div className="metric-bar-fill" style={{ width: `${Math.min(value, 100)}%` }} />
                              </div>
                            </div>
                              ))
                            : null}
                        </div>
                        <div className="reason-block">
                          <h3>Recent Reasons</h3>
                          <ul className="reason-list">
                            {relationship.last_event_tags.map((reason) => <li key={reason}>{reason}</li>)}
                          </ul>
                        </div>
                      </div>
                    ))}
                  </div>
                </article>
              );
            })}
          </section>

          <section className="content-card">
            <div className="section-heading">
              <div>
                <span className="eyebrow subtle">Isolated Participants</span>
                <h2>暂时边缘位</h2>
              </div>
            </div>
            <div className="metric-chip-row">
              {data.isolated_participants.map((participant) => (
                <span key={participant.participant_id} className="metric-chip">
                  {participant.name}
                </span>
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
