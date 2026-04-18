## 状态更新规则表

这份文档定义 `Soul.md` 中关系变量的初始化、更新和结算规则。

目标不是做一个过度复杂的数学系统，而是建立一套：

1. 能稳定跑
2. 能解释给用户听
3. 能支持多次实验对比

的规则。

## 设计原则

1. 先可解释，再追求拟真
2. 每次变量变化都必须能对应到事件标签
3. 一次事件不应让稳定关系瞬间翻盘，除非本来就很脆弱
4. 冲突和修复都必须是结构化的
5. 最终“恋爱可能性”由多变量组成，不能只看吸引力

## 变量清单

所有关系变量默认范围为 `0-100`。

| 变量 | 含义 | 高分意味着什么 |
|------|------|----------------|
| `initial_attraction` | 初始外在/气质吸引 | 第一眼更有兴趣 |
| `attraction` | 当前心动与恋爱兴趣 | 更容易主动靠近 |
| `trust` | 信任与安全感 | 更愿意投入真实情绪 |
| `comfort` | 相处舒适度 | 互动更自然 |
| `understood` | 被理解感 | 更容易建立深连接 |
| `expectation` | 对关系的未来期待 | 更愿意下注 |
| `disappointment` | 失望累积 | 更容易撤退或防御 |
| `conflict` | 冲突和未修复伤害累积 | 高时关系脆弱 |
| `anxiety` | 关系焦虑和不确定感 | 高时更容易误判 |
| `curiosity` | 继续探索的意愿 | 决定会不会给关系机会 |
| `exclusivity_pressure` | 竞争和独占压力 | 高时更容易吃醋、比较 |
| `commitment_alignment` | 关系目标一致性 | 决定能否从暧昧进入稳定关系 |

## 初始值规则

### 1. 初始吸引力

`initial_attraction` 建议由 4 部分组成：

```text
initial_attraction =
  外形/风格偏好匹配 * 0.35 +
  性格想象匹配 * 0.20 +
  择偶标准命中 * 0.30 +
  节目第一印象加成 * 0.15
```

说明：

1. 第一印象只做小权重，避免锁死后续逆转
2. 命中“硬性雷点”时，初始吸引力上限建议限制在 `45`

### 2. 初始信任

默认初始信任不高，建议：

```text
trust = 20 + (资料完整度 * 0.1) + (初见互动质量 * 0.2)
```

初始范围建议控制在 `20-40`。

### 3. 初始焦虑

根据依恋风格和多人竞争环境设定：

```text
anxiety =
  依恋基础焦虑 +
  竞争敏感度 +
  初始不确定性
```

建议：

1. 安全型人格默认 `25-40`
2. 焦虑型人格默认 `45-65`
3. 回避型人格表面焦虑低，但会转化为舒适度下降和关系回避

## 更新机制

### 1. 更新单位

一次状态更新基于“事件标签”而不是一句对话。

每个场景会生成若干 `event_tag`，例如：

1. `mutual_choice`
2. `clear_affection`
3. `missed_signal`
4. `value_alignment`
5. `public_embarrassment`
6. `repair_attempt`
7. `competition_threat`
8. `emotional_validation`
9. `avoidant_response`
10. `boundary_respected`

### 2. 单次更新幅度

单次事件对变量的基础改动建议控制在 `-18` 到 `+18`。

只有“关键场景 + 高脆弱关系 + 高强度事件”才允许接近极值。

## 事件标签影响表

| 事件标签 | attraction | trust | comfort | understood | expectation | disappointment | conflict | anxiety |
|----------|------------|-------|---------|------------|-------------|----------------|----------|---------|
| `mutual_choice` | +10 | +8 | +5 | +3 | +12 | -2 | 0 | -6 |
| `clear_affection` | +8 | +7 | +4 | +5 | +10 | -1 | 0 | -5 |
| `value_alignment` | +4 | +8 | +6 | +10 | +6 | 0 | -2 | -3 |
| `emotional_validation` | +3 | +9 | +6 | +12 | +5 | -3 | -4 | -8 |
| `missed_signal` | -4 | -6 | -3 | -5 | -8 | +9 | +2 | +7 |
| `public_embarrassment` | -8 | -10 | -8 | -6 | -6 | +10 | +10 | +8 |
| `competition_threat` | +2 | -4 | -3 | -2 | +4 | +4 | +3 | +10 |
| `repair_attempt` | +1 | +6 | +4 | +6 | +2 | -5 | -7 | -5 |
| `avoidant_response` | -3 | -5 | -4 | -8 | -5 | +6 | +2 | +5 |
| `boundary_respected` | +2 | +8 | +5 | +4 | +3 | -2 | -4 | -4 |

## 场景修正系数

同一个事件在不同场景中的影响不一样。

建议乘以场景系数：

| 场景 | 系数 | 说明 |
|------|------|------|
| 破冰初见 | `0.8` | 影响轻，防止第一印象锁死 |
| 自由交流 | `1.0` | 标准系数 |
| 双人约会选择 | `1.2` | 被选择感和落空感更强 |
| 多人晚餐 | `1.1` | 焦虑和冲突放大 |
| 私聊澄清 | `1.25` | 信任和修复权重更高 |
| 夜间短信 | `1.15` | 期待和失望更敏感 |
| 冲突事件 | `1.3` | 高风险高收益 |
| 关键选择夜 | `1.2` | 对齐度与焦虑变化更明显 |
| 最终告白 | 结算专用 | 不直接做常规增减 |

## 策略卡修正

用户的策略卡不直接改分，而是改变事件更容易生成什么标签。

例如：

| 策略卡 | 主要倾向 |
|--------|----------|
| `be_direct` | 更容易触发 `clear_affection`，也更容易触发 `public_embarrassment` |
| `reassure_first` | 更容易触发 `emotional_validation` 和 `repair_attempt` |
| `stay_mysterious` | 更容易提高 `curiosity`，但也提高 `missed_signal` 概率 |
| `focus_one_person` | 增加目标对象的 `expectation`，同时增加其他人的 `competition_threat` |
| `protect_self_image` | 降低 `public_embarrassment` 风险，但提高 `avoidant_response` 概率 |

## 稳定层对更新的影响

不同人格会放大或削弱同一事件的效果。

建议加入人格修正：

### 1. 焦虑型人格

1. `competition_threat` 对 `anxiety` 的增幅增加 `+30%`
2. `missed_signal` 对 `disappointment` 的增幅增加 `+20%`
3. `emotional_validation` 对 `trust` 的增幅增加 `+15%`

### 2. 回避型人格

1. `clear_affection` 不一定提升 `comfort`，可能额外 `-5`
2. `repair_attempt` 对 `trust` 的收益减半
3. `boundary_respected` 的收益更大

### 3. 高情感开放人格

1. `value_alignment` 和 `emotional_validation` 的增益更高
2. `missed_signal` 的伤害较小，因为更容易主动求证

## 状态衰减与恢复

为了避免变量无限堆积，建议引入轻度衰减：

1. `anxiety` 如果连续 2 个场景没有负面事件，自动 `-5`
2. `conflict` 只有在出现 `repair_attempt` 或 `boundary_respected` 时才显著下降
3. `expectation` 在连续两轮无回应时自动 `-8`
4. `curiosity` 在连续两轮无新正向刺激时自动 `-6`

## 关系状态判定规则

建议每个场景后根据阈值刷新 `status`：

### 1. `observing`

满足：

1. `attraction >= 40`
2. `trust < 50`
3. `commitment_alignment < 55`

### 2. `warming`

满足：

1. `attraction >= 50`
2. `comfort >= 50`
3. `trust >= 45`
4. `conflict < 40`

### 3. `heating_up`

满足：

1. `attraction >= 65`
2. `trust >= 60`
3. `understood >= 55`
4. `expectation >= 55`
5. `conflict < 45`

### 4. `unstable`

满足：

1. `attraction >= 60`
2. `anxiety >= 55` 或 `conflict >= 50`

### 5. `cooling`

满足：

1. `attraction < 45` 或 `curiosity < 35`
2. `disappointment >= 50`

### 6. `blocked`

满足：

1. `trust < 35`
2. `conflict >= 60`
3. 或 `commitment_alignment < 35`

### 7. `out`

满足以下任一：

1. `attraction < 25` 且 `trust < 25`
2. `disappointment >= 75`
3. 连续 3 个关键场景没有任何正向标签

### 8. `paired`

满足：

1. `attraction >= 70`
2. `trust >= 68`
3. `commitment_alignment >= 65`
4. `conflict < 35`
5. 双方都有明确选择意愿

## 最终恋爱可能性计算

最终不要只输出一个黑盒分数，但系统内部仍建议计算一个综合分：

```text
romance_score =
  attraction * 0.18 +
  trust * 0.22 +
  comfort * 0.12 +
  understood * 0.12 +
  commitment_alignment * 0.18 +
  curiosity * 0.06 +
  expectation * 0.05 -
  disappointment * 0.04 -
  conflict * 0.06 -
  anxiety * 0.05 -
  exclusivity_pressure * 0.02
```

映射建议：

| 分数 | 解释 |
|------|------|
| `80+` | 高概率进入稳定关系 |
| `65-79` | 有明显可能，但存在关键风险 |
| `50-64` | 有吸引，未形成稳定推进 |
| `35-49` | 关系摇摆，多半卡在误会或目标错位 |
| `<35` | 当前不具备进入关系的条件 |

## 多人竞争规则

这是你这个产品必须做好的部分。

### 1. 竞争压力来源

当一个对象同时对多个候选人保持高吸引和高好奇时，所有竞争者的 `exclusivity_pressure` 上升。

建议：

```text
若目标对象同时满足：
  对 A 的 attraction >= 55
  对 B 的 attraction >= 55
则 A 和 B 的 exclusivity_pressure 都增加 8-15
```

### 2. 竞争不等于自动掉分

竞争关系不应直接让 `attraction` 暴跌，更合理的是：

1. 先升 `anxiety`
2. 再根据用户反应决定是否伤害 `trust` 和 `comfort`

### 3. 三角关系的解释原则

当用户输掉竞争，不要只说“对方更喜欢别人”，要解释是：

1. 你们的推进节奏错位
2. 对方在安全感上更信任另一个人
3. 你在竞争场景中的应对放大了对方的不确定感

## 解释生成规则

每次结算至少给出 3 类解释：

1. 初始阶段：为什么会被吸引或不被吸引
2. 转折阶段：哪一个场景改变了关系走势
3. 最终阶段：为什么进入关系，或为什么没进入关系

解释模板建议：

```text
你和 {target} 本来在 {dimension} 上有优势，
但在 {scene_name} 中因为 {event_tag}，
导致 {key_variable} 发生明显变化，
最终让关系停在了 {status}。
```

## 分支对比规则

实验分支的价值在于比较。

建议每次实验结束后，固定输出：

1. 相比主线，哪 3 个变量变化最大
2. 哪个场景开始出现分歧
3. 结果差异是来自人格修改，还是策略卡修改

## MVP 建议

如果第一版想尽快跑起来，先只做下面 6 个核心变量：

1. `attraction`
2. `trust`
3. `comfort`
4. `anxiety`
5. `conflict`
6. `commitment_alignment`

等第一版验证“好不好玩”后，再加入 `understood`、`disappointment`、`exclusivity_pressure` 这些更细的变量。
