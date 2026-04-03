const statusLabels: Record<string, string> = {
  pending: "待解锁",
  queued: "排队中",
  claimed: "已领取",
  running: "执行中",
  completed: "已完成",
  failed: "失败",
  observing: "观察中",
  warming: "轻微升温",
  heating_up: "明显升温",
  unstable: "有火花但不稳",
  cooling: "正在降温",
  blocked: "被卡住",
  out: "基本出局",
  paired: "形成互选",
};

const metricLabels: Record<string, string> = {
  initial_attraction: "初始吸引",
  attraction: "吸引力",
  comfort: "舒适度",
  trust: "信任",
  intimacy: "亲密度",
  understood: "被理解感",
  curiosity: "探索意愿",
  anxiety: "焦虑",
  competition_sense: "竞争感",
  self_esteem: "自尊波动",
  expectation_gap: "期待落差",
  expectation: "期待",
  disappointment: "失望",
  conflict: "冲突",
  exclusivity_pressure: "独占压力",
  commitment_alignment: "目标对齐",
};

const sceneLabels: Record<string, string> = {
  scene_01_intro: "Scene 01 · 破冰初见",
  scene_02_free_talk: "Scene 02 · 第一次自由交流",
  scene_03_random_date: "Scene 03 · 随机约会",
  scene_04_group_dinner: "Scene 04 · 多人晚餐与暗流",
  scene_05_conversation_choosing: "Scene 05 · 主动选择交流",
  scene_06_private_signal: "Scene 06 · 匿名表达与私密信号",
  scene_07_new_date: "Scene 07 · 主动约会竞争",
};

const castRoleLabels: Record<string, string> = {
  main_cast: "主阵容",
  observer: "观察位",
};

const strategyCardLabels: Record<string, string> = {
  warm_presence: "暖场在场感",
  playful_opening: "俏皮开场",
  seek_common_ground: "主动找共同点",
  ask_deeper_questions: "追问更深层",
  hold_center: "稳住场面",
  focus_one_person: "聚焦一人",
  avoid_competition: "回避竞争",
  choose_by_emotion: "按心动选择",
  choose_by_stability: "按稳定性选择",
  test_uncertain_target: "试探不确定对象",
  wait_to_be_chosen: "等待被选择",
  send_clear_signal: "发送明确信号",
  keep_ambiguity: "保持模糊",
  protect_self_image: "保护自我形象",
  signal_multiple_targets: "多目标分散信号",
  act_first: "先手邀约",
  compete_for_top_choice: "争夺第一目标",
  fallback_strategy: "次优回退策略",
  withdraw_if_rejected: "被拒后退出",
};

const strategyCardDescriptions: Record<string, string> = {
  warm_presence: "降低陌生感，让多人场更容易接住话头。",
  playful_opening: "提高火花感和注意力，容易催出交叉互动。",
  seek_common_ground: "更快建立舒适感和被理解感。",
  ask_deeper_questions: "更早暴露价值观，也更容易筛出真正聊得来的人。",
  hold_center: "提高公开场合稳定度，降低失态风险。",
  focus_one_person: "公开释放偏好，可能放大竞争感。",
  avoid_competition: "减少正面对位冲突，但可能降低存在感。",
  choose_by_emotion: "优先按吸引力和情绪驱动做选择。",
  choose_by_stability: "优先按信任和稳定性做选择。",
  test_uncertain_target: "主动试探高不确定关系。",
  wait_to_be_chosen: "降低主动暴露，等待对方动作。",
  send_clear_signal: "提高表达清晰度，也提高落空风险。",
  keep_ambiguity: "保留退路，降低推进强度。",
  protect_self_image: "偏防御表达，降低直接受伤风险。",
  signal_multiple_targets: "分散表达，降低单点风险但增加误判。",
  act_first: "提高抢先邀约概率。",
  compete_for_top_choice: "优先争夺第一目标，失败成本更高。",
  fallback_strategy: "首邀失败后尝试次优对象。",
  withdraw_if_rejected: "被拒后退出，避免二次冲突。",
};

const personalityFieldLabels: Record<string, string> = {
  extroversion: "外向度",
  initiative: "主动性",
  emotional_openness: "情感开放",
  attachment_style: "依恋风格",
  conflict_style: "冲突风格",
  self_esteem_stability: "自我稳定",
  pace_preference: "推进节奏",
  commitment_goal: "关系目标",
  preferred_traits: "偏好特质",
  disliked_traits: "反感特质",
  boundaries: "边界",
  expression_style: "表达方式",
};

const enumLabels: Record<string, string> = {
  secure: "安全型",
  anxious: "焦虑型",
  avoidant: "回避型",
  avoid_then_explode: "先忍后爆",
  steady_boundary: "稳定立边界",
  observe_then_withdraw: "先观察再抽离",
  clarify_early: "尽早说清楚",
  gradual_but_clear: "慢一点但要明确",
  serious_relationship: "认真进入关系",
  observe_first: "先观察再推进",
  slow_burn: "慢热长期线",
  balanced: "平衡表达",
  direct: "直接表达",
  gentle: "温和表达",
  low: "低",
  medium: "中",
  high: "高",
};

export function formatStatusLabel(value: string) {
  return statusLabels[value] ?? value;
}

export function formatMetricLabel(value: string) {
  return metricLabels[value] ?? value;
}

export function formatSceneTitle(value: string) {
  return sceneLabels[value] ?? value;
}

export function formatCastRole(value: string) {
  return castRoleLabels[value] ?? value;
}

export function formatPersonalityFieldLabel(value: string) {
  return personalityFieldLabels[value] ?? value;
}

export function formatStrategyCard(value: string) {
  return strategyCardLabels[value] ?? value;
}

export function formatStrategyDescription(value: string) {
  return strategyCardDescriptions[value] ?? value;
}

export function formatEnumLabel(value: string) {
  return enumLabels[value] ?? value.replaceAll("_", " ");
}

export function formatPersonalityValue(field: string, value: unknown) {
  if (Array.isArray(value)) {
    return value.length ? value.join(" / ") : "未设置";
  }
  if (field === "boundaries" && value && typeof value === "object") {
    const record = value as { hard_boundaries?: string[]; soft_boundaries?: string[] };
    const hard = record.hard_boundaries?.length
      ? `硬边界：${record.hard_boundaries.join(" / ")}`
      : "硬边界：未设置";
    const soft = record.soft_boundaries?.length
      ? `软边界：${record.soft_boundaries.join(" / ")}`
      : "软边界：未设置";
    return `${hard}；${soft}`;
  }
  if (field === "expression_style" && value && typeof value === "object") {
    const record = value as { communication_style?: string; reassurance_need?: string };
    return `沟通方式：${formatEnumLabel(record.communication_style ?? "balanced")}；确认需求：${formatEnumLabel(record.reassurance_need ?? "medium")}`;
  }
  if (typeof value === "string") {
    return formatEnumLabel(value);
  }
  if (typeof value === "number") {
    return String(value);
  }
  if (typeof value === "boolean") {
    return value ? "是" : "否";
  }
  if (value == null) {
    return "未设置";
  }
  return JSON.stringify(value);
}

export function formatReasonText(value: string) {
  const uniqueSegments = value
    .split(/[；;]+/)
    .map((item) => item.trim())
    .filter(Boolean)
    .filter((item, index, items) => items.indexOf(item) === index);
  return uniqueSegments.join("；");
}
