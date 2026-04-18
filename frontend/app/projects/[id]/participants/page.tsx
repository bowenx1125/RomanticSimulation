"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  applyPersonalityPreset,
  createSimulation,
  getProjectParticipants,
  ParticipantEditablePersonality,
  ProjectParticipant,
  ProjectParticipantsResponse,
  updateParticipantPersonality,
} from "../../../../lib/api";
import {
  formatCastRole,
  formatEnumLabel,
  formatPersonalityFieldLabel,
} from "../../../../lib/presentation";

const strategyOptions = [
  {
    id: "warm_presence",
    title: "暖场在场感",
    description: "降低陌生感，让多人场更容易接住话头。",
  },
  {
    id: "playful_opening",
    title: "俏皮开场",
    description: "提高火花感和注意力，容易催出交叉互动。",
  },
  {
    id: "seek_common_ground",
    title: "主动找共同点",
    description: "更快建立舒适感和被理解感。",
  },
  {
    id: "ask_deeper_questions",
    title: "追问更深层",
    description: "更早暴露价值观，也更容易筛出真正聊得来的人。",
  },
];

function csvValue(items?: string[]) {
  return (items ?? []).join(", ");
}

function diffPersonality(
  current: ParticipantEditablePersonality,
  baseline: ParticipantEditablePersonality,
) {
  return Object.keys(current).filter((key) => {
    const currentValue = current[key as keyof ParticipantEditablePersonality];
    const baselineValue = baseline[key as keyof ParticipantEditablePersonality];
    return JSON.stringify(currentValue) !== JSON.stringify(baselineValue);
  });
}

export default function ProjectParticipantsPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const projectId = params.id;
  const [data, setData] = useState<ProjectParticipantsResponse | null>(null);
  const [participants, setParticipants] = useState<ProjectParticipant[]>([]);
  const [selectedParticipantIds, setSelectedParticipantIds] = useState<string[]>([]);
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([
    "warm_presence",
    "ask_deeper_questions",
  ]);
  const [savingParticipantId, setSavingParticipantId] = useState<string | null>(null);
  const [launching, setLaunching] = useState(false);
  const [status, setStatus] = useState("先校准每位 participant 的稳定人格，再决定谁进入本次 simulation。");
  const [error, setError] = useState("");

  useEffect(() => {
    let stopped = false;

    async function load() {
      try {
        const nextData = await getProjectParticipants(projectId);
        if (!stopped) {
          setData(nextData);
          setParticipants(nextData.participants);
          setSelectedParticipantIds(nextData.participants.map((participant) => participant.id));
          setError("");
        }
      } catch (loadError) {
        if (!stopped) {
          setError(loadError instanceof Error ? loadError.message : "加载 participant workspace 失败");
        }
      }
    }

    load();
    return () => {
      stopped = true;
    };
  }, [projectId]);

  const baselineMap = useMemo(
    () =>
      Object.fromEntries(
        (data?.participants ?? []).map((participant) => [participant.id, participant.editable_personality]),
      ),
    [data],
  );

  function updateParticipant(
    participantId: string,
    updater: (current: ProjectParticipant) => ProjectParticipant,
  ) {
    setParticipants((current) =>
      current.map((participant) => (participant.id === participantId ? updater(participant) : participant)),
    );
  }

  function toggleParticipant(participantId: string) {
    setSelectedParticipantIds((current) =>
      current.includes(participantId)
        ? current.filter((item) => item !== participantId)
        : [...current, participantId],
    );
  }

  function toggleStrategy(strategyId: string) {
    setSelectedStrategies((current) => {
      if (current.includes(strategyId)) {
        return current.filter((item) => item !== strategyId);
      }
      if (current.length >= 2) {
        return [current[1], strategyId];
      }
      return [...current, strategyId];
    });
  }

  async function handleSaveParticipant(participantId: string) {
    const participant = participants.find((item) => item.id === participantId);
    if (!participant) {
      return;
    }
    try {
      setSavingParticipantId(participantId);
      setStatus(`正在保存 ${participant.name} 的默认人格...`);
      await updateParticipantPersonality(projectId, participantId, participant.editable_personality);
      const nextData = await getProjectParticipants(projectId);
      setData(nextData);
      setParticipants(nextData.participants);
      setStatus(`${participant.name} 的默认人格已保存。`);
      setError("");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "保存人格失败");
    } finally {
      setSavingParticipantId(null);
    }
  }

  async function handleApplyPreset(presetSlug: string, participantId: string) {
    try {
      setStatus("正在应用人格 preset...");
      const nextData = await applyPersonalityPreset(projectId, presetSlug, [participantId]);
      setData(nextData);
      setParticipants(nextData.participants);
      setError("");
    } catch (presetError) {
      setError(presetError instanceof Error ? presetError.message : "应用 preset 失败");
    }
  }

  async function handleLaunchSimulation() {
    try {
      setLaunching(true);
      setStatus("正在启动本次 simulation...");
      const simulation = await createSimulation(projectId, {
        strategyCards: selectedStrategies,
        selectedParticipantIds,
      });
      router.push(`/simulations/${simulation.id}`);
    } catch (launchError) {
      setError(launchError instanceof Error ? launchError.message : "启动 simulation 失败");
    } finally {
      setLaunching(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="app-header">
        <div>
          <span className="eyebrow">Participant Setup</span>
          <h1>{data?.project_name ?? "Phase 3 Participant Workspace"}</h1>
          <p>这里不再区分“主角”和“其他人”。所有角色都能独立调人格、应用 preset、决定是否进入本次多人 runtime。</p>
        </div>
        <div className="header-actions">
          <Link className="ghost-link" href="/">
            返回首页
          </Link>
        </div>
      </section>

      {error ? <p className="inline-error">{error}</p> : null}

      <section className="overview-grid">
        <article className="content-card overview-hero-card">
          <span className="eyebrow subtle">Launch Control</span>
          <h2>本次参演名单与全局策略</h2>
          <p>{status}</p>
          <div className="metric-chip-row">
            {selectedParticipantIds.map((participantId) => {
              const participant = participants.find((item) => item.id === participantId);
              return participant ? (
                <span key={participantId} className="metric-chip">
                  {participant.name}
                </span>
              ) : null;
            })}
          </div>
          <button
            className="primary-button"
            onClick={handleLaunchSimulation}
            disabled={launching || selectedParticipantIds.length < 3}
          >
            {launching ? "正在启动 simulation..." : "用当前配置启动 simulation"}
          </button>
        </article>

        <article className="content-card compact-stat-card">
          <h3>策略卡</h3>
          <div className="strategy-list">
            {strategyOptions.map((strategy) => {
              const isActive = selectedStrategies.includes(strategy.id);
              return (
                <button
                  key={strategy.id}
                  type="button"
                  className={`strategy-option${isActive ? " active" : ""}`}
                  onClick={() => toggleStrategy(strategy.id)}
                >
                  <strong>{strategy.title}</strong>
                  <span>{strategy.description}</span>
                </button>
              );
            })}
          </div>
        </article>
      </section>

      <section className="participant-grid">
        {participants.map((participant) => {
          const changedFields = diffPersonality(
            participant.editable_personality,
            baselineMap[participant.id] ?? participant.editable_personality,
          );
          return (
            <article key={participant.id} className="content-card participant-card">
              <div className="card-heading">
                <div>
                  <span className="eyebrow subtle">{formatCastRole(participant.cast_role)}</span>
                  <h2>{participant.name}</h2>
                </div>
                <label className="selection-toggle">
                  <input
                    type="checkbox"
                    checked={selectedParticipantIds.includes(participant.id)}
                    onChange={() => toggleParticipant(participant.id)}
                  />
                  <span>加入本次 simulation</span>
                </label>
              </div>

              <div className="participant-toolbar">
                {data?.presets.map((preset) => (
                  <button
                    key={`${participant.id}-${preset.slug}`}
                    type="button"
                    className="soft-tag-button"
                    onClick={() => handleApplyPreset(preset.slug, participant.id)}
                  >
                    {preset.name}
                  </button>
                ))}
              </div>

              <div className="metric-chip-row">
                {changedFields.length ? (
                  changedFields.map((field) => (
                    <span key={field} className="metric-chip">
                      {formatPersonalityFieldLabel(field)}
                    </span>
                  ))
                ) : (
                  <span className="card-footnote">当前与项目默认一致</span>
                )}
              </div>

              {participant.personality_summary ? (
                <p className="card-intro">{participant.personality_summary}</p>
              ) : null}
              {participant.background_summary ? (
                <p className="card-footnote">{participant.background_summary}</p>
              ) : null}

              <div className="slider-grid">
                {[
                  ["extroversion", "外向度"],
                  ["initiative", "主动性"],
                  ["emotional_openness", "情感开放"],
                  ["self_esteem_stability", "自我稳定"],
                ].map(([key, label]) => {
                  const value = participant.editable_personality[key as keyof ParticipantEditablePersonality] as number;
                  return (
                    <label key={key} className="field-block">
                      <span className="field-label">
                        {label} <strong>{value}</strong>
                      </span>
                      <input
                        type="range"
                        min={0}
                        max={100}
                        value={value}
                        onChange={(event) =>
                          updateParticipant(participant.id, (current) => ({
                            ...current,
                            editable_personality: {
                              ...current.editable_personality,
                              [key]: Number(event.target.value),
                            },
                          }))
                        }
                      />
                    </label>
                  );
                })}
              </div>

              <div className="two-column-fields">
                <label className="field-block">
                  <span className="field-label">依恋风格</span>
                  <select
                    className="field-input"
                    value={participant.editable_personality.attachment_style}
                    onChange={(event) =>
                      updateParticipant(participant.id, (current) => ({
                        ...current,
                        editable_personality: {
                          ...current.editable_personality,
                          attachment_style: event.target.value,
                        },
                      }))
                    }
                  >
                    <option value="secure">{formatEnumLabel("secure")}</option>
                    <option value="anxious">{formatEnumLabel("anxious")}</option>
                    <option value="avoidant">{formatEnumLabel("avoidant")}</option>
                  </select>
                </label>
                <label className="field-block">
                  <span className="field-label">关系目标</span>
                  <select
                    className="field-input"
                    value={participant.editable_personality.commitment_goal}
                    onChange={(event) =>
                      updateParticipant(participant.id, (current) => ({
                        ...current,
                        editable_personality: {
                          ...current.editable_personality,
                          commitment_goal: event.target.value,
                        },
                      }))
                    }
                  >
                    <option value="serious_relationship">{formatEnumLabel("serious_relationship")}</option>
                    <option value="observe_first">{formatEnumLabel("observe_first")}</option>
                    <option value="slow_burn">{formatEnumLabel("slow_burn")}</option>
                  </select>
                </label>
              </div>

              <div className="two-column-fields">
                <label className="field-block">
                  <span className="field-label">偏好特质</span>
                  <input
                    className="field-input"
                    value={csvValue(participant.editable_personality.preferred_traits)}
                    onChange={(event) =>
                      updateParticipant(participant.id, (current) => ({
                        ...current,
                        editable_personality: {
                          ...current.editable_personality,
                          preferred_traits: event.target.value
                            .split(",")
                            .map((item) => item.trim())
                            .filter(Boolean),
                        },
                      }))
                    }
                  />
                </label>
                <label className="field-block">
                  <span className="field-label">反感特质</span>
                  <input
                    className="field-input"
                    value={csvValue(participant.editable_personality.disliked_traits)}
                    onChange={(event) =>
                      updateParticipant(participant.id, (current) => ({
                        ...current,
                        editable_personality: {
                          ...current.editable_personality,
                          disliked_traits: event.target.value
                            .split(",")
                            .map((item) => item.trim())
                            .filter(Boolean),
                        },
                      }))
                    }
                  />
                </label>
              </div>

              <button
                className="secondary-button"
                onClick={() => handleSaveParticipant(participant.id)}
                disabled={savingParticipantId === participant.id}
              >
                {savingParticipantId === participant.id ? "正在保存..." : "保存为项目默认人格"}
              </button>
            </article>
          );
        })}
      </section>
    </main>
  );
}
