"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import {
  createProject,
  createSimulation,
  importParticipants,
  ParticipantEditablePersonality,
  ParticipantImportRequest,
} from "../lib/api";

const strategyOptions = [
  {
    id: "warm_presence",
    title: "暖场在场感",
    description: "降低陌生感，让多人场更容易接话。",
  },
  {
    id: "playful_opening",
    title: "俏皮开场",
    description: "提高火花感和可见度，也更容易引出交叉互动。",
  },
  {
    id: "seek_common_ground",
    title: "主动找共同点",
    description: "更快建立舒适感和被理解感。",
  },
  {
    id: "ask_deeper_questions",
    title: "追问更深层",
    description: "提高被理解感，但也会更早暴露价值观差异。",
  },
];

function basePersonality(
  overrides: Partial<ParticipantEditablePersonality>,
): ParticipantEditablePersonality {
  return {
    extroversion: 50,
    initiative: 50,
    emotional_openness: 50,
    attachment_style: "secure",
    conflict_style: "avoid_then_explode",
    self_esteem_stability: 50,
    pace_preference: "gradual_but_clear",
    commitment_goal: "serious_relationship",
    preferred_traits: [],
    disliked_traits: [],
    boundaries: {
      hard_boundaries: [],
      soft_boundaries: [],
    },
    expression_style: {
      communication_style: "balanced",
      reassurance_need: "medium",
    },
    ...overrides,
  };
}

const initialPayload: ParticipantImportRequest = {
  participants: [
    {
      name: "林夏",
      cast_role: "main_cast",
      age: 27,
      city: "Shanghai",
      occupation: "Brand Strategist",
      background_summary: "第一次参加恋综，希望确认真正稳定而且能认真沟通的人。",
      personality_summary: "慢热但观察细，一旦确认对方在认真听，就会明显更主动。",
      attachment_style: "anxious",
      appearance_tags: ["clean", "stylish", "athletic"],
      personality_tags: ["observant", "humorous", "sincere"],
      preferred_traits: ["emotionally_stable", "humorous", "proactive", "sincere"],
      disliked_traits: ["cold", "ambiguous"],
      editable_personality: basePersonality({
        extroversion: 46,
        initiative: 58,
        emotional_openness: 42,
        attachment_style: "anxious",
        self_esteem_stability: 46,
        preferred_traits: ["emotionally_stable", "humorous", "proactive", "sincere"],
        disliked_traits: ["cold", "ambiguous"],
      }),
      display_order: 0,
    },
    {
      name: "周予安",
      cast_role: "main_cast",
      age: 29,
      city: "Shanghai",
      occupation: "Architect",
      background_summary: "节奏稳，讨厌没有边界感的暧昧，偏好长期稳定关系。",
      personality_summary: "克制温和，先观察，但对真正有意思的话题会追问。",
      attachment_style: "secure",
      appearance_tags: ["clean", "gentle", "minimal"],
      personality_tags: ["emotionally_stable", "patient", "precise"],
      preferred_traits: ["warm", "clear", "kind"],
      disliked_traits: ["dramatic"],
      editable_personality: basePersonality({
        extroversion: 41,
        initiative: 52,
        emotional_openness: 47,
        attachment_style: "secure",
        conflict_style: "steady_boundary",
        self_esteem_stability: 72,
        preferred_traits: ["warm", "clear", "kind"],
        disliked_traits: ["dramatic"],
      }),
      display_order: 1,
    },
    {
      name: "陈屿",
      cast_role: "main_cast",
      age: 26,
      city: "Hangzhou",
      occupation: "Content Director",
      background_summary: "强表达欲，喜欢有火花的互动，但认真关系里怕被束缚。",
      personality_summary: "很会调动气氛，也容易在多人场里制造注意力。",
      attachment_style: "avoidant",
      appearance_tags: ["fashionable", "playful", "sharp"],
      personality_tags: ["creative", "direct", "playful"],
      preferred_traits: ["confident", "interesting"],
      disliked_traits: ["clingy"],
      commitment_goal: "observe_first",
      editable_personality: basePersonality({
        extroversion: 79,
        initiative: 74,
        emotional_openness: 64,
        attachment_style: "avoidant",
        conflict_style: "observe_then_withdraw",
        self_esteem_stability: 43,
        commitment_goal: "observe_first",
        preferred_traits: ["confident", "interesting"],
        disliked_traits: ["clingy"],
      }),
      display_order: 2,
    },
    {
      name: "沈知意",
      cast_role: "main_cast",
      age: 28,
      city: "Beijing",
      occupation: "Product Manager",
      background_summary: "理性克制，重视长期价值观一致，不喜欢反复试探。",
      personality_summary: "沟通清晰，遇到复杂关系时会更想把话说明白。",
      attachment_style: "secure",
      appearance_tags: ["sharp", "elegant"],
      personality_tags: ["proactive", "clear", "emotionally_stable"],
      preferred_traits: ["clear", "stable", "growth_oriented"],
      disliked_traits: ["avoidant"],
      editable_personality: basePersonality({
        extroversion: 55,
        initiative: 66,
        emotional_openness: 60,
        attachment_style: "secure",
        conflict_style: "clarify_early",
        self_esteem_stability: 67,
        preferred_traits: ["clear", "stable", "growth_oriented"],
        disliked_traits: ["avoidant"],
      }),
      display_order: 3,
    },
  ],
};

function csvValue(items?: string[]) {
  return (items ?? []).join(", ");
}

export default function HomePage() {
  const router = useRouter();
  const [projectName, setProjectName] = useState("恋爱模拟器 Phase 3");
  const [description, setDescription] = useState("多角色平权关系模拟器");
  const [payload, setPayload] = useState<ParticipantImportRequest>(initialPayload);
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([
    "warm_presence",
    "ask_deeper_questions",
  ]);
  const [status, setStatus] = useState("准备启动多人多轮 runtime。");
  const [error, setError] = useState("");
  const [isLaunching, setIsLaunching] = useState(false);
  const [isCreatingWorkspace, setIsCreatingWorkspace] = useState(false);

  function updateParticipant(index: number, updater: (current: ParticipantImportRequest["participants"][number]) => ParticipantImportRequest["participants"][number]) {
    setPayload((current) => ({
      participants: current.participants.map((participant, participantIndex) =>
        participantIndex === index ? updater(participant) : participant,
      ),
    }));
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

  async function handleLaunchSimulation() {
    try {
      setIsLaunching(true);
      setError("");
      setStatus("正在创建项目...");
      const project = await createProject({
        name: projectName,
        description,
      });

      setStatus("正在导入 participant 与人格配置...");
      await importParticipants(project.id, payload);

      setStatus("正在启动 scene_01_intro 到 scene_06_private_signal runtime...");
      const simulation = await createSimulation(project.id, {
        strategyCards: selectedStrategies,
      });
      router.push(`/simulations/${simulation.id}`);
    } catch (launchError) {
      setError(launchError instanceof Error ? launchError.message : "启动模拟失败");
      setStatus("实验启动失败，请检查后端和 worker 日志。");
    } finally {
      setIsLaunching(false);
    }
  }

  async function handleOpenWorkspace() {
    try {
      setIsCreatingWorkspace(true);
      setError("");
      setStatus("正在创建可编辑的 cast workspace...");
      const project = await createProject({
        name: projectName,
        description,
      });
      await importParticipants(project.id, payload);
      router.push(`/projects/${project.id}/participants`);
    } catch (workspaceError) {
      setError(workspaceError instanceof Error ? workspaceError.message : "创建 workspace 失败");
      setStatus("未能打开 participant workspace。");
    } finally {
      setIsCreatingWorkspace(false);
    }
  }

  return (
    <main className="marketing-shell">
      <section className="hero-card">
        <div className="hero-copy">
          <span className="eyebrow">Phase 3 / Decentralized Runtime</span>
          <h1>把“主角恋综”升级成真正的多人关系场</h1>
          <p className="hero-body">
            这里不再是“主角 + 其他人回应”的单中心入口。你会先配置所有 participant
            的人格，再启动一个连续运行的 runtime，让 scene_01_intro、scene_02_free_talk、scene_03_random_date、scene_04_group_dinner、scene_05_conversation_choosing 和 scene_06_private_signal
            在同一局里形成真实的多人多轮关系图。
          </p>
          <div className="hero-metrics">
            <article>
              <strong>所有角色平权</strong>
              <span>每个人都能被调整人格、主动发言、影响他人与被他人观察。</span>
            </article>
            <article>
              <strong>六场连续 runtime</strong>
              <span>scene_01_intro 建立张力，scene_02_free_talk 拉开偏好，scene_03_random_date 触发意外连接，scene_04_group_dinner 放大多人竞争，scene_05_conversation_choosing 明确主动选择方向，scene_06_private_signal 揭示私密信号与期待落差。</span>
            </article>
            <article>
              <strong>Pairwise Graph</strong>
              <span>关系不再围绕单一中心，而是存成 A→B、B→A 分离的图结构。</span>
            </article>
          </div>
        </div>

        <aside className="launch-panel">
          <div className="panel-header">
            <span className="panel-kicker">Simulation Setup</span>
            <h2>启动一局 Phase 3</h2>
          </div>
          <label className="field-label">项目名</label>
          <input
            className="field-input"
            value={projectName}
            onChange={(event) => setProjectName(event.target.value)}
          />
          <label className="field-label">描述</label>
          <textarea
            className="field-textarea compact"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />

          <div className="status-panel">
            <span className="status-dot" />
            <div>
              <strong>当前状态</strong>
              <p>{status}</p>
            </div>
          </div>

          <button className="primary-button" onClick={handleLaunchSimulation} disabled={isLaunching || isCreatingWorkspace}>
            {isLaunching ? "正在创建 Phase 3..." : "启动多轮多人模拟"}
          </button>
          <button
            className="secondary-button"
            onClick={handleOpenWorkspace}
            disabled={isLaunching || isCreatingWorkspace}
          >
            {isCreatingWorkspace ? "正在打开工作台..." : "先进入 participant 工作台"}
          </button>
          {error ? <p className="inline-error">{error}</p> : null}
        </aside>
      </section>

      <section className="content-card">
        <div className="card-heading">
          <div>
            <span className="eyebrow subtle">Strategy Cards</span>
            <h2>全局策略偏置</h2>
          </div>
        </div>
        <p className="card-intro">选择最多 2 张，影响六场 scene 的整体互动倾向。</p>
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
      </section>

      <section className="participant-grid">
        {payload.participants.map((participant, index) => (
          <article key={participant.name} className="content-card participant-card">
            <div className="card-heading">
              <div>
                <span className="eyebrow subtle">Participant {index + 1}</span>
                <h2>{participant.name}</h2>
              </div>
              <span className="soft-tag">{participant.cast_role}</span>
            </div>

            <div className="two-column-fields">
              <label className="field-block">
                <span className="field-label">姓名</span>
                <input
                  className="field-input"
                  value={participant.name}
                  onChange={(event) =>
                    updateParticipant(index, (current) => ({ ...current, name: event.target.value }))
                  }
                />
              </label>
              <label className="field-block">
                <span className="field-label">职业</span>
                <input
                  className="field-input"
                  value={participant.occupation ?? ""}
                  onChange={(event) =>
                    updateParticipant(index, (current) => ({
                      ...current,
                      occupation: event.target.value,
                    }))
                  }
                />
              </label>
            </div>

            <label className="field-block">
              <span className="field-label">角色描述</span>
              <textarea
                className="field-textarea compact"
                value={participant.personality_summary ?? ""}
                onChange={(event) =>
                  updateParticipant(index, (current) => ({
                    ...current,
                    personality_summary: event.target.value,
                  }))
                }
              />
            </label>

            <div className="slider-grid">
              {[
                ["extroversion", "外向度"],
                ["initiative", "主动性"],
                ["emotional_openness", "情感开放"],
                ["self_esteem_stability", "自我稳定"],
              ].map(([key, label]) => {
                const value = participant.editable_personality?.[
                  key as keyof ParticipantEditablePersonality
                ] as number;
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
                        updateParticipant(index, (current) => ({
                          ...current,
                          editable_personality: {
                            ...current.editable_personality!,
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
                  value={participant.editable_personality?.attachment_style}
                  onChange={(event) =>
                    updateParticipant(index, (current) => ({
                      ...current,
                      attachment_style: event.target.value,
                      editable_personality: {
                        ...current.editable_personality!,
                        attachment_style: event.target.value,
                      },
                    }))
                  }
                >
                  <option value="secure">secure</option>
                  <option value="anxious">anxious</option>
                  <option value="avoidant">avoidant</option>
                </select>
              </label>
              <label className="field-block">
                <span className="field-label">关系目标</span>
                <select
                  className="field-input"
                  value={participant.editable_personality?.commitment_goal}
                  onChange={(event) =>
                    updateParticipant(index, (current) => ({
                      ...current,
                      commitment_goal: event.target.value,
                      editable_personality: {
                        ...current.editable_personality!,
                        commitment_goal: event.target.value,
                      },
                    }))
                  }
                >
                  <option value="serious_relationship">serious_relationship</option>
                  <option value="observe_first">observe_first</option>
                  <option value="slow_burn">slow_burn</option>
                </select>
              </label>
            </div>

            <div className="two-column-fields">
              <label className="field-block">
                <span className="field-label">偏好特质</span>
                <input
                  className="field-input"
                  value={csvValue(participant.editable_personality?.preferred_traits)}
                  onChange={(event) =>
                    updateParticipant(index, (current) => ({
                      ...current,
                      preferred_traits: event.target.value.split(",").map((item) => item.trim()).filter(Boolean),
                      editable_personality: {
                        ...current.editable_personality!,
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
                  value={csvValue(participant.editable_personality?.disliked_traits)}
                  onChange={(event) =>
                    updateParticipant(index, (current) => ({
                      ...current,
                      disliked_traits: event.target.value.split(",").map((item) => item.trim()).filter(Boolean),
                      editable_personality: {
                        ...current.editable_personality!,
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
          </article>
        ))}
      </section>
    </main>
  );
}
