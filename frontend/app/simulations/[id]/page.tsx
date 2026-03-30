"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { getSimulationOverview, SimulationOverview } from "../../../lib/api";
import {
  formatCastRole,
  formatMetricLabel,
  formatStatusLabel,
  formatStrategyCard,
} from "../../../lib/presentation";

function formatTime(value?: string) {
  if (!value) {
    return "尚未完成";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    month: "short",
    day: "numeric",
  }).format(new Date(value));
}

function summarizeAuditPayload(logType: string, payload: unknown) {
  if (payload == null || typeof payload !== "object") {
    return "本阶段已记录结构化结果。";
  }

  const record = payload as Record<string, unknown>;
  if (logType === "scene_input_summary") {
    const participants = Array.isArray(record.participants)
      ? record.participants
          .map((item) =>
            typeof item === "object" && item ? String((item as { name?: string }).name ?? "") : "",
          )
          .filter(Boolean)
      : [];
    return `系统为 ${participants.join("、")} 准备了本场共享上下文。`;
  }
  if (logType === "scene_orchestrator_plan") {
    return "Scene orchestrator 已锁定轮次、停机条件和调度方向。";
  }
  if (logType === "participant_agent_outputs") {
    const messages = Array.isArray(record.messages) ? record.messages.length : 0;
    return `多人 turn loop 已完成，共产出 ${messages} 轮可回放发言。`;
  }
  if (logType === "scene_referee_result") {
    return typeof record.scene_summary === "string"
      ? record.scene_summary
      : "Referee 已完成 pairwise graph 更新。";
  }
  if (logType === "applied_state_changes") {
    const deltas = Array.isArray(record.relationship_deltas) ? record.relationship_deltas.length : 0;
    return `Graph state engine 已写入 ${deltas} 条边变化。`;
  }
  return "该阶段已写入审计日志。";
}

export default function SimulationOverviewPage() {
  const params = useParams<{ id: string }>();
  const simulationId = params.id;
  const [data, setData] = useState<SimulationOverview | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let stopped = false;

    async function load() {
      try {
        const nextData = await getSimulationOverview(simulationId);
        if (!stopped) {
          setData(nextData);
          setError("");
        }
      } catch (loadError) {
        if (!stopped) {
          setError(loadError instanceof Error ? loadError.message : "加载模拟失败");
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

  const topEdges = useMemo(() => data?.relationship_cards.slice(0, 6) ?? [], [data]);
  const latestScene = data ? data.scene_timeline_preview[data.scene_timeline_preview.length - 1] : null;

  return (
    <main className="app-shell">
      <section className="app-header">
        <div>
          <span className="eyebrow">Simulation Overview</span>
          <h1>多人关系场总览</h1>
          <p>
            这里看的是一局连续 runtime 的全貌：谁正在形成明确连接，谁在旁观，谁开始因为多人场而误读别人。
          </p>
        </div>
        <div className="header-actions">
          <Link className="ghost-link" href="/">
            新建实验
          </Link>
          {data ? (
            <Link className="ghost-link" href={`/projects/${data.project_id}/participants`}>
              参与者配置
            </Link>
          ) : null}
          <Link className="ghost-link" href={`/simulations/${simulationId}/relationships`}>
            关系图谱
          </Link>
          <Link className="ghost-link" href={`/simulations/${simulationId}/personalities`}>
            人格面板
          </Link>
        </div>
      </section>

      {error ? <p className="inline-error">{error}</p> : null}

      {!data ? (
        <section className="content-card">
          <p>正在加载 simulation overview...</p>
        </section>
      ) : (
        <>
          <section className="overview-grid">
            <article className="content-card overview-hero-card">
              <span className={`status-pill status-${data.status}`}>{formatStatusLabel(data.status)}</span>
              <h2>{data.latest_scene_summary ?? "正在准备第一场 scene"}</h2>
              <p>{data.active_tension ?? "等待当前场景张力生成..."}</p>
              <div className="meta-strip">
                <span>simulation_id: {data.id}</span>
                <span>scene: {data.current_scene_code ?? "pending"}</span>
                <span>started: {formatTime(data.started_at)}</span>
              </div>
              {latestScene ? (
                <Link className="primary-link" href={`/simulations/${simulationId}/scenes/${latestScene.scene_run_id}`}>
                  打开当前 scene 回放
                </Link>
              ) : null}
            </article>

            <article className="content-card compact-stat-card">
              <h3>群体张力</h3>
              <p>{data.group_tension_summary ?? data.latest_audit_snippet ?? "等待群体张力聚合。"}</p>
              <div className="metric-chip-row">
                {data.isolated_participants.map((participant) => (
                  <span key={participant.participant_id} className="metric-chip">
                    观察位: {participant.name}
                  </span>
                ))}
              </div>
            </article>

            <article className="content-card compact-stat-card">
              <h3>策略偏置</h3>
              <div className="tag-row">
                {data.strategy_cards.map((strategy) => (
                  <span key={strategy} className="soft-tag">
                    {formatStrategyCard(strategy)}
                  </span>
                ))}
              </div>
              <p className="card-footnote">{data.latest_audit_snippet ?? "等待下一段 tension。"}</p>
            </article>

            <article className="content-card compact-stat-card">
              <h3>运行状态</h3>
              <ul className="bullet-metrics">
                <li>当前状态：{formatStatusLabel(data.status)}</li>
                <li>当前场景：{data.current_scene_code}</li>
                <li>完成时间：{formatTime(data.finished_at)}</li>
              </ul>
            </article>
          </section>

          <section className="two-panel-layout">
            <article className="content-card">
              <div className="section-heading">
                <div>
                  <span className="eyebrow subtle">Participants</span>
                  <h2>本局参与者</h2>
                </div>
              </div>
              <div className="participant-list">
                {data.participants.map((participant) => (
                  <article key={participant.participant_id} className="participant-mini-card">
                    <div className="timeline-card-top">
                      <strong>{participant.name}</strong>
                      <span className="soft-tag">{formatCastRole(participant.cast_role)}</span>
                    </div>
                    <p>{participant.personality_summary ?? "暂无额外描述"}</p>
                    <div className="metric-chip-row">
                      <span className="metric-chip">
                        主动性 {participant.editable_personality.initiative}
                      </span>
                      <span className="metric-chip">
                        开放度 {participant.editable_personality.emotional_openness}
                      </span>
                    </div>
                  </article>
                ))}
              </div>
            </article>

            <article className="content-card">
              <div className="section-heading">
                <div>
                  <span className="eyebrow subtle">Hot Pairs</span>
                  <h2>当前最热关系线</h2>
                </div>
                <Link className="text-link" href={`/simulations/${simulationId}/relationships`}>
                  打开完整图谱
                </Link>
              </div>
              <div className="timeline-list">
                {data.hot_pairs.length ? data.hot_pairs.map((pair) => (
                  <article
                    key={`${pair.participant_a_id}-${pair.participant_b_id}`}
                    className="timeline-card static"
                  >
                    <div className="timeline-card-top">
                      <strong>
                        {pair.participant_a_name} ↔ {pair.participant_b_name}
                      </strong>
                      <span className="soft-tag">score {pair.combined_score}</span>
                    </div>
                    <p>{pair.summary}</p>
                  </article>
                )) : topEdges.map((edge) => (
                  <article
                    key={`${edge.source_participant_id}-${edge.target_participant_id}`}
                    className="timeline-card static"
                  >
                    <div className="timeline-card-top">
                      <strong>
                        {edge.source_name} → {edge.target_name}
                      </strong>
                      <span className={`trend-pill trend-${edge.trend}`}>
                        {formatStatusLabel(edge.trend)}
                      </span>
                    </div>
                    <div className="metric-chip-row">
                      {Object.entries(edge.surface_metrics).map(([metric, value]) => (
                        <span key={metric} className="metric-chip">
                          {formatMetricLabel(metric)}: {value}
                        </span>
                      ))}
                    </div>
                  </article>
                ))}
              </div>
            </article>
          </section>

          <section className="two-panel-layout">
            <article className="content-card">
              <div className="section-heading">
                <div>
                  <span className="eyebrow subtle">Timeline</span>
                  <h2>Scene 时间线</h2>
                </div>
              </div>
              <div className="timeline-list">
                {data.scene_timeline_preview.map((scene) => (
                  <Link key={scene.scene_run_id} className="timeline-card" href={`/simulations/${simulationId}/scenes/${scene.scene_run_id}`}>
                    <div className="timeline-card-top">
                      <strong>{scene.scene_code}</strong>
                      <span className={`status-pill status-${scene.status}`}>
                        {formatStatusLabel(scene.status)}
                      </span>
                    </div>
                    <p>{scene.summary ?? "等待场景完成结构化摘要。"}</p>
                    <small>{scene.tension ?? "等待下一段 tension。"}</small>
                  </Link>
                ))}
              </div>
            </article>

            <article className="content-card">
              <div className="section-heading">
                <div>
                  <span className="eyebrow subtle">Audit</span>
                  <h2>最近结构化日志</h2>
                </div>
              </div>
              <div className="audit-grid">
                {data.recent_audit_logs.map((log) => (
                  <article key={`${log.log_type}-${log.created_at}`} className="audit-card">
                    <strong>{log.log_type}</strong>
                    <span>{formatTime(log.created_at)}</span>
                    <p>{summarizeAuditPayload(log.log_type, log.payload)}</p>
                  </article>
                ))}
              </div>
            </article>
          </section>
        </>
      )}
    </main>
  );
}
