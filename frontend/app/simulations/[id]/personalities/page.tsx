"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import {
  getSimulationPersonalities,
  SimulationPersonalities,
} from "../../../../lib/api";
import {
  formatCastRole,
  formatPersonalityFieldLabel,
  formatPersonalityValue,
} from "../../../../lib/presentation";

export default function PersonalitiesPage() {
  const params = useParams<{ id: string }>();
  const simulationId = params.id;
  const [data, setData] = useState<SimulationPersonalities | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let stopped = false;

    async function load() {
      try {
        const nextData = await getSimulationPersonalities(simulationId);
        if (!stopped) {
          setData(nextData);
          setError("");
        }
      } catch (loadError) {
        if (!stopped) {
          setError(loadError instanceof Error ? loadError.message : "加载人格面板失败");
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

  return (
    <main className="app-shell">
      <section className="app-header">
        <div>
          <span className="eyebrow">Personalities</span>
          <h1>Simulation Personality Snapshot</h1>
          <p>这里展示的是这局 simulation 真正吃进去的人格快照，以及哪些字段相对默认导入被改过。</p>
        </div>
        <div className="header-actions">
          <Link className="ghost-link" href={`/simulations/${simulationId}`}>
            返回总览
          </Link>
          <Link className="ghost-link" href={`/simulations/${simulationId}/relationships`}>
            查看关系图谱
          </Link>
        </div>
      </section>

      {error ? <p className="inline-error">{error}</p> : null}
      {!data ? (
        <section className="content-card">
          <p>正在加载 personalities...</p>
        </section>
      ) : (
        <section className="relationship-page-grid">
          {data.personalities.map((item) => (
            <article key={item.participant_id} className="relationship-detail-card">
              <div className="timeline-card-top">
                <div>
                  <span className="eyebrow subtle">{formatCastRole(item.cast_role)}</span>
                  <h2>{item.name}</h2>
                </div>
                {item.preset_slug ? <span className="soft-tag">{item.preset_slug}</span> : null}
              </div>

              <div className="metric-chip-row">
                {item.changed_fields.length ? item.changed_fields.map((field) => (
                  <span key={field} className="metric-chip">
                    改动: {formatPersonalityFieldLabel(field)}
                  </span>
                )) : (
                  <span className="card-footnote">这位角色沿用了项目默认人格。</span>
                )}
              </div>

              <div className="personality-list">
                {Object.entries(item.editable_personality).map(([key, value]) => (
                  <div key={key} className="personality-row">
                    <strong>{formatPersonalityFieldLabel(key)}</strong>
                    <span>{formatPersonalityValue(key, value)}</span>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
