## Soul.md 模板

`Soul.md` 是单个 Agent 的人格与关系状态文件。

它不是人物介绍页，而是模拟过程中持续读取和更新的状态源。实现时建议每位嘉宾各有一份独立 `Soul.md`，主角的主线人格和实验分支人格也各自独立存储。

## 文件职责

`Soul.md` 解决 4 件事：

1. 定义这个人“本来是谁”
2. 定义这个人“当前处于什么情感状态”
3. 定义这个人“和每个对象现在是什么关系”
4. 给多 Agent 模拟提供稳定、可更新、可解释的上下文

## 字段原则

字段分成两层：

1. 稳定层：短期不会因为一两次聊天就改变
2. 可变层：会随场景推进持续更新

实现约束：

1. 稳定层默认只允许用户在“实验分支”中修改
2. 可变层只能由模拟过程更新，不能让用户手工直接改分
3. 所有可变字段都要有取值范围，避免状态漂移
4. 任何“解释文案”都必须能回溯到字段变化

## 建议文件结构

建议使用如下结构：

```yaml
agent_id: guest_01
agent_name: 林夏
role: protagonist
source:
  imported_from:
    - wechat_chat
    - profile_doc
  confidence: 0.78

stable_profile:
  basic_info:
    age: 27
    city: Shanghai
    job: Brand Strategist
    education: Bachelor
    appearance_tags:
      - clean
      - athletic
      - stylish
  personality_core:
    extroversion: 62
    initiative: 58
    emotional_openness: 41
    conflict_style: avoid_then_explode
    attachment_style: anxious
    self_esteem_stability: 46
  dating_preferences:
    preferred_traits:
      - emotionally_stable
      - humorous
      - proactive
    disliked_traits:
      - cold
      - ambiguous
      - controlling
    pace_preference: gradual_but_clear
    commitment_goal: serious_relationship
  boundaries:
    hard_boundaries:
      - public_humiliation
      - repeated_disrespect
    soft_boundaries:
      - late_replies
      - over_flirting_with_others
  expression_style:
    affection_style: acts_of_service
    communication_style: indirect_with_tests
    reassurance_need: high

dynamic_state:
  mood_baseline: 57
  emotional_energy: 63
  social_fatigue: 34
  self_doubt: 48
  current_focus:
    - guest_03
  current_goal: find_mutual_and_secure_connection
  last_scene_summary: "在多人晚餐中表现积极，但对 guest_03 的吃醋情绪变重。"

relationships:
  guest_02:
    initial_attraction: 52
    attraction: 57
    trust: 44
    comfort: 49
    understood: 38
    expectation: 61
    disappointment: 23
    conflict: 18
    anxiety: 47
    curiosity: 55
    exclusivity_pressure: 12
    commitment_alignment: 51
    recent_trend: warming
    status: observing
    key_memories:
      - "破冰时对方主动接话，降低了陌生感"
      - "夜间短信没有收到回应，期待落空"
  guest_03:
    initial_attraction: 71
    attraction: 76
    trust: 62
    comfort: 58
    understood: 67
    expectation: 72
    disappointment: 34
    conflict: 29
    anxiety: 53
    curiosity: 64
    exclusivity_pressure: 44
    commitment_alignment: 59
    recent_trend: unstable
    status: heating_up
    key_memories:
      - "双人约会中价值观对齐，信任提升"
      - "多人晚餐里出现竞争对象，焦虑上升"

scene_memory:
  completed_scenes:
    - scene_01_intro
    - scene_02_free_talk
    - scene_03_date_pick
  notable_events:
    - scene_id: scene_03_date_pick
      event_type: mutual_choice
      impact_targets:
        - guest_03
      note: "双向选择强化了关系期待"
    - scene_id: scene_04_group_dinner
      event_type: jealousy_trigger
      impact_targets:
        - guest_03
      note: "竞争压力导致焦虑上升"

strategy_bias:
  default_cards:
    - seek_clarity
    - reassure_before_push
  disabled_cards:
    - play_hard_to_get

explanation_hooks:
  core_pattern: "容易因为不确定性而放大竞争威胁"
  growth_edge: "如果能更早表达需求，会减少试探和误判"
```

## 字段定义

### 1. 顶层字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `agent_id` | string | Agent 唯一标识 |
| `agent_name` | string | 嘉宾名 |
| `role` | enum | `protagonist`、`guest`、`observer` |
| `source` | object | 数据来源和置信度 |

### 2. 稳定层字段

这些字段默认按 `0-100` 打分，数值越高代表该特质越强。

| 字段 | 说明 | 是否允许实验分支修改 |
|------|------|----------------------|
| `extroversion` | 外向程度 | 是 |
| `initiative` | 主动推进关系的倾向 | 是 |
| `emotional_openness` | 情感表达透明度 | 是 |
| `self_esteem_stability` | 自我价值稳定性 | 是 |
| `attachment_style` | 依恋风格 | 是，但只能切换到预设枚举 |
| `conflict_style` | 冲突处理方式 | 是，但只能切换到预设枚举 |
| `preferred_traits` | 偏好特征 | 是 |
| `disliked_traits` | 负向触发点 | 是 |
| `pace_preference` | 关系推进节奏偏好 | 是 |
| `commitment_goal` | 参与节目的目标 | 是 |

### 3. 可变层字段

这些字段必须在模拟中自动更新。

建议统一采用 `0-100` 范围：

| 字段 | 说明 | 备注 |
|------|------|------|
| `attraction` | 当前吸引力 | 不是最终关系分，更多是心动程度 |
| `trust` | 信任度 | 决定关系能否稳定推进 |
| `comfort` | 相处舒适度 | 高频互动的基础 |
| `understood` | 被理解感 | 影响深度连接 |
| `expectation` | 对未来关系的期待 | 高但落空时容易转成失望 |
| `disappointment` | 失望值 | 过高会拖垮关系 |
| `conflict` | 冲突累积值 | 包含摩擦和未修复的伤害 |
| `anxiety` | 关系焦虑值 | 高时更容易误判和试探 |
| `curiosity` | 探索意愿 | 初期很重要 |
| `exclusivity_pressure` | 独占/竞争压力 | 多人关系时关键 |
| `commitment_alignment` | 双方关系目标对齐度 | 决定是否能进入稳定关系 |

### 4. 关系状态枚举

每对关系必须有一个可读状态，便于前端展示。

| 状态 | 说明 |
|------|------|
| `observing` | 有兴趣，但还在观察 |
| `warming` | 轻微升温 |
| `heating_up` | 明显升温 |
| `unstable` | 有吸引但不稳定 |
| `cooling` | 正在降温 |
| `blocked` | 被冲突、误会或目标错位卡住 |
| `out` | 基本出局 |
| `paired` | 已形成明确互选 |

## 主角与普通嘉宾的区别

主角 Agent 需要额外 3 类信息：

1. `strategy_bias`：用户长期偏好的策略卡
2. `explanation_hooks`：用于生成成长建议的模式总结
3. 实验分支元信息：这个分支相对主线改了什么

建议在实验分支文件顶部增加：

```yaml
experiment_meta:
  branch_id: exp_2026_03_28_01
  based_on: main_protagonist_v1
  changed_fields:
    - stable_profile.personality_core.emotional_openness
    - stable_profile.personality_core.initiative
  hypothesis: "如果我更主动且更坦诚，是否能减少和 guest_03 的错位。"
```

## 更新边界

以下内容不能在单轮场景中大幅波动：

1. 依恋风格
2. 核心边界
3. 长期择偶标准

以下内容允许快速波动：

1. 吸引力
2. 信任
3. 焦虑
4. 失望
5. 冲突
6. 关系状态

## 最小实现版本

如果一开始不想做太重，`Soul.md` 的 MVP 可以先保留下面这些字段：

```yaml
stable_profile:
  personality_core:
    extroversion: 50
    initiative: 50
    emotional_openness: 50
    attachment_style: secure
  dating_preferences:
    preferred_traits: []
    disliked_traits: []
dynamic_state:
  mood_baseline: 50
relationships:
  guest_x:
    attraction: 50
    trust: 50
    comfort: 50
    anxiety: 50
    conflict: 0
    status: observing
```

## 实现建议

1. 用 `Soul.md` 作为人类可读模板
2. 真正运行时可同步生成结构化 `json` 版本
3. 每个场景结束后只更新变动字段，不要整份重写为纯自然语言
4. 每次变更都记录 `scene_id` 和 `reason_tag`，否则后续解释会失真
