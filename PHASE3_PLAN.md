# 第三阶段实现计划

这份文档定义 Phase 3 的目标、范围、系统改造、执行清单、交付要求和验收标准。

这不是一个“下一步可以做什么”的 brainstorming 文档，而是一份可以直接开工的实现清单。目标是让下一次 session 的 agent 团队不需要重新理解上下文，就能顺序推进并交付。

这份计划按以下 3 个 skill 的工作方式收敛：

1. `office-hours`：先重构问题本身，避免继续沿着“主角带动配角”的假设做增量修补
2. `plan-ceo-review`：把产品目标从“主角视角恋综模拟”提升为“多角色平权关系模拟器”
3. `plan-eng-review`：把抽象愿景拆成数据库、runtime、API、前端、验证和验收清单

---

## 1. Phase 3 总目标

Phase 3 必须同时完成以下 2 个核心升级：

1. 把当前 `scene_01_intro` 的“每人只有一轮发言”的最小闭环，升级为“多轮次、多人交叉、可持续推进”的真实群体对话 runtime
2. 把当前系统中“主角 + 其他嘉宾附庸”的单中心假设，升级为“所有角色平等”的多 Agent 关系系统，并允许用户调整每个角色的人格

Phase 3 的结果必须让系统从：

```text
用户主角
  ->
其余嘉宾围绕主角反应
```

升级为：

```text
多名平等参与者
  ->
彼此观察、发言、结盟、误解、偏好转移
  ->
形成动态关系图
```

也就是说，Phase 3 交付的不是“主角更真实”，而是“系统终于从单中心假多 Agent 变成去中心化真多 Agent”。

---

## 2. 为什么必须做 Phase 3

Phase 2 虽然已经完成了真实多 Agent runtime 的最小闭环，但仍然有明显上限：

1. 对话轮次太短，无法形成真正的多人场内动态
2. 关系更新仍然主要围绕“主角对每位嘉宾”
3. Agent 的世界模型仍然把主角当作关系中心
4. 角色人格仍然更像导入资料，而不是可调的长期运行参数
5. `scene_02_free_talk` 仍未真正落地

如果继续沿用 Phase 2 的结构，只会得到：

1. 更长一点的“主角被多人回应”
2. 更多条 transcript
3. 但不会得到更真实的关系演化

Phase 3 的设计原则是：

1. 不再默认任何人是叙事中心
2. 不再默认关系只从一个人向外发散
3. 不再默认一场 scene 只需要一轮“我说一句，你们轮流接”
4. 不再默认人格只能来自初始导入资料

---

## 3. Phase 3 产品重定义

从 Phase 3 开始，这个项目的产品定义调整为：

> 一个可调人格、可观察多边关系图、支持多轮多人场景推进的关系模拟器。

这一定义有 4 个直接后果：

1. 角色是平等的
2. 关系必须是图，而不是主角单中心表
3. Scene 的最小单位不再是一轮回应，而是一次多人互动段落
4. 人格必须是可配置系统，而不是一次性导入文档

---

## 4. Phase 3 必须遵守的硬性原则

Phase 3 必须遵守以下原则，不能退让：

### 4.1 角色平权原则

必须满足：

1. 系统中不再存在“产品级默认主角”
2. 所有角色都使用统一的 participant 模型
3. 所有角色都可以拥有独立人格配置
4. 所有角色都能对其他角色产生主动行为
5. 所有角色都能成为被关注、被忽视、被竞争、被误解的一方

禁止：

1. 用字段名、API 命名、表结构继续硬编码 `protagonist`
2. 仍然把其他角色的动机只写成“回应主角”
3. 仍然只给一个人开放人格调节能力

### 4.2 多轮多人原则

必须满足：

1. 每个核心 scene 至少支持 6 个 turn
2. 支持 3-5 名参与者在同一 scene 中交替发言
3. turn 顺序不能固定成“某个人永远先说 + 其他人依次回应”
4. 允许一个角色连续两次参与同一小段互动，但必须有可解释原因
5. 允许非中心角色之间直接互动，而不是都只对着某个中心角色说话

### 4.3 人格可调原则

必须满足：

1. 每个角色都能查看当前人格配置
2. 每个角色都能被用户调整稳定人格层字段
3. 人格调整必须进入 simulation 输入上下文
4. 调整后的差异必须能体现在 scene 行为与结果中
5. 调整必须可审计、可对比、可回溯

### 4.4 可解释性原则

必须满足：

1. 任意关系变化都能追溯到具体 event / turn
2. 任意人格影响都能追溯到具体字段
3. 任意“为什么某人更主动 / 更防御 / 更沉默”都能解释给用户
4. 前端展示必须是人可读叙事，不是变量 dump

---

## 5. Phase 3 范围

### 5.1 必做范围

Phase 3 必做内容：

1. 移除系统中的默认主角中心假设
2. 把单中心关系表升级为多边关系图
3. 把 `GuestImportPayload` 升级为统一 participant 导入格式
4. 新增 participant 人格配置与编辑能力
5. 把 `scene_01_intro` 升级为 6-12 turn 的多人多轮 scene
6. 完整实现 `scene_02_free_talk`
7. 支持跨 scene 保留多人互动记忆
8. 新增关系图谱与人格编辑前端页面
9. 重做 overview / replay 的展示方式，使其适配“平等角色”而不是“主角中心”
10. 用真实浏览器再次验证全部关键页面

### 5.2 暂不做范围

Phase 3 明确不做：

1. 完整 9 个场景全部落地
2. 云端多用户协作
3. 完整 AB branch compare 系统
4. 语音、多模态、视频 avatar
5. token 级流式 UI
6. 完整社交图时间轴可视化编辑器

### 5.3 场景范围

Phase 3 至少必须完成：

1. `scene_01_intro` 升级为多人多轮真实互动
2. `scene_02_free_talk` 从占位变为可运行场景

可预留但不强制交付：

1. `scene_03_date_pick` 的结构化接口

---

## 6. 当前系统的关键结构问题

当前代码与数据模型中，以下地方仍然锁死了单中心假设：

1. `GuestImportPayload` 使用 `protagonist + guests`
2. `GuestProfile.role` 默认把角色分成 `protagonist` 与 `guest`
3. `RelationshipState` 使用 `protagonist_guest_id + target_guest_id`
4. `scene_01_intro` planner prompt 明确要求 protagonist 先发言
5. runtime 可见性规则把其他角色对齐到“对主角的关系”
6. 首页 UI 直接以“主角设定”作为主入口
7. scene 输出默认解释“谁对你有兴趣”

这些结构如果不改，Phase 3 只会是假平权。必须真正迁移。

---

## 7. Phase 3 架构升级目标

Phase 2 当前链路是：

```text
participants (1 protagonist + N guests)
  ->
director_plan
  ->
single-pass turn_order
  ->
scene_referee
  ->
apply protagonist-centered relationship deltas
```

Phase 3 必须升级为：

```text
participants (all equal)
  ->
scene orchestrator
  ->
multi-round group dialogue planner
  ->
agent turn scheduler
  ->
turn loop with dynamic next speaker selection
  ->
scene referee
  ->
pairwise / group state graph update
  ->
next scene memory pack
```

### 7.1 新角色职责

#### Scene Orchestrator

职责：

1. 定义场景目标
2. 给出参与者清单
3. 决定本场最大回合数与 stop condition
4. 决定是否需要小组拆分、私聊插入或回到全员互动

不负责：

1. 代替任意角色说话
2. 直接决定谁必须围着谁转

#### Turn Scheduler

职责：

1. 根据当前 transcript、关系图和 tension 决定下一个发言者
2. 防止轮次被单个角色垄断
3. 允许自然打断、追问、转移话题
4. 保证多人场景里每个角色都有存在感

不负责：

1. 生成最终裁决
2. 修改人格设定

#### Participant Agent

职责：

1. 基于自己的人格、当前可见上下文、关系图局部视图生成发言
2. 决定这轮主要目标对象
3. 输出行为摘要、意图标签、下一步倾向

不负责：

1. 偷看全局隐藏状态
2. 决定他人真实内心
3. 决定最终关系结果

#### Graph State Engine

职责：

1. 应用 pairwise relationship deltas
2. 支持一对多、多人场压力和小群体张力
3. 更新 scene memory / participant memory
4. 维护解释链

---

## 8. 数据模型升级

### 8.1 Participant 模型替代 Protagonist/Guest 二元结构

Phase 3 必须把导入和存储从：

```json
{
  "protagonist": {...},
  "guests": [...]
}
```

升级为：

```json
{
  "participants": [
    {
      "participant_id": "p_01",
      "name": "林夏",
      "cast_role": "main_cast",
      "editable_personality": {...}
    }
  ]
}
```

字段要求：

1. `participant_id`
2. `name`
3. `cast_role`
4. `imported_profile`
5. `editable_personality`
6. `soul_data`
7. `is_active`
8. `display_order`

说明：

1. `cast_role` 只描述节目席位，不描述谁是关系中心
2. `editable_personality` 是用户显式可调的人格层
3. 所有 participant 使用统一 schema

### 8.2 RelationshipState 升级为 Pairwise Graph

当前表结构是：

1. `protagonist_guest_id`
2. `target_guest_id`

Phase 3 必须升级为真正的 pairwise graph，例如：

1. `source_participant_id`
2. `target_participant_id`
3. `relationship_kind`
4. `metrics`
5. `status`
6. `recent_trend`
7. `notes`
8. `updated_by_scene_run_id`

强约束：

1. 同一 simulation 内，任意 `A -> B` 都必须可存储
2. 默认要求 `A -> B` 和 `B -> A` 分开存储，因为感受不一定对称
3. 不允许继续依赖“主角对所有人”的单向表

### 8.3 新增 PersonalityPreset / PersonalityOverride

建议新增：

1. `personality_presets`
2. `participant_personality_overrides`

用途：

1. 保存基础人格模板
2. 保存当前 simulation 对每个 participant 的人格 override
3. 支持后续分支实验

### 8.4 Scene Memory 升级

Phase 3 新增或强化：

1. `participant_scene_memories`
2. `scene_event_links`

每条 scene memory 至少包括：

1. `participant_id`
2. `scene_run_id`
3. `memory_type`
4. `target_participant_ids`
5. `summary`
6. `importance`
7. `event_tags`

---

## 9. 人格系统升级

### 9.1 目标

Phase 3 的人格系统必须让用户能真正控制“这个角色是怎样的人”，而不是只改一段简历文案。

### 9.2 必须可调的人格字段

每个 participant 至少支持调整：

1. `extroversion`
2. `initiative`
3. `emotional_openness`
4. `attachment_style`
5. `conflict_style`
6. `self_esteem_stability`
7. `pace_preference`
8. `commitment_goal`
9. `preferred_traits`
10. `disliked_traits`
11. `boundaries`
12. `expression_style`

### 9.3 调整规则

必须支持：

1. 项目级默认人格导入
2. simulation 创建前调节每个角色人格
3. simulation 内只读展示当前人格
4. 审计记录“修改了什么字段”

禁止：

1. 直接让用户改 `trust`、`comfort` 之类动态关系分
2. 把人格调整写成 prompt 片段而不落库

### 9.4 前端交互要求

人格编辑器必须具备：

1. 每位 participant 的可编辑面板
2. 预设模板切换
3. 修改字段高亮
4. “恢复默认”按钮
5. 本次 simulation 使用的人格快照预览

---

## 10. 多轮多人 scene runtime 设计

### 10.1 Phase 3 的最小真实多人流程

`scene_01_intro` 必须升级为：

1. `SceneOrchestratorPlan`
2. `Round 1 opening`
3. `Round 1 response cluster`
4. `Round 2 follow-up`
5. `Round 2 cross-talk`
6. 必要时 `Round 3 escalation / clarification`
7. `SceneRefereeResult`

### 10.2 Turn 数量硬要求

`scene_01_intro`：

1. 最少 6 turn
2. 推荐 8-10 turn
3. 最多 12 turn

`scene_02_free_talk`：

1. 最少 8 turn
2. 推荐 10-14 turn
3. 最多 16 turn

### 10.3 Speaker Scheduling 规则

必须支持：

1. 非固定顺序
2. 同一角色在合理情况下可再次发言
3. 上一轮被点名的角色优先获得回应机会
4. 被连续忽略的角色权重上升
5. 不能让单一角色连续霸屏超过 2 次

### 10.4 Turn 输出 schema 升级

Phase 3 的 `AgentTurn` 至少包括：

```json
{
  "speaker_participant_id": "p_02",
  "speaker_name": "周予安",
  "turn_index": 6,
  "round_index": 2,
  "utterance": "如果你把通勤当成观察样本，那你应该很擅长看出谁是真的在认真听。",
  "behavior_summary": "语气平稳，带试探性的追问",
  "intent_tags": ["signal_interest", "probe_depth"],
  "target_participant_ids": ["p_01"],
  "addressed_from_turn_id": "turn_0004",
  "topic_tags": ["commute", "attention", "first_impression"],
  "next_speaker_suggestions": ["p_01", "p_03"],
  "self_observation": "我想看她会不会接这个更深一点的话题。"
}
```

### 10.5 Scene Stop Condition

必须不再是“每个人说一次就结束”，而要满足：

1. 至少完成 2 轮有效互动
2. 至少出现 2 次交叉互动或追问
3. 至少出现 1 次非开场角色之间的间接影响
4. transcript 达到最小信息量阈值
5. 已形成下一场 tension

---

## 11. Scene 01 重做要求

`scene_01_intro` 在 Phase 3 中的目标不再只是建立“主角第一印象”，而是：

1. 建立全员对全员的第一轮关系偏置
2. 形成初始场内张力图
3. 识别谁主动、谁保守、谁观察、谁竞争

必须体现：

1. 至少 3 人直接互动
2. 至少 1 次话题延续
3. 至少 1 次非中心人物被其他人注意到
4. 至少 1 次“谁在观察谁”的结构化裁决

用户最终要看懂：

1. 谁在主动发起连接
2. 谁只是礼貌在场
3. 谁已经开始产生竞争意识
4. 谁虽然没说很多，但被谁注意到了

---

## 12. Scene 02 必须落地

`scene_02_free_talk` 在 Phase 3 中不允许继续占位。

### 12.1 目标

1. 从“第一印象”进入“互动兼容性”
2. 让话题真正扩展、分叉、回流
3. 让角色间不止一条连接线

### 12.2 结构要求

必须支持：

1. 2-3 个局部话题簇
2. 角色在不同话题簇间切换
3. 关系更新不只发生在单一 pair
4. `comfort`、`understood`、`curiosity` 真正拉开差距

### 12.3 前端反馈

用户必须能看懂：

1. 谁和谁聊得最顺
2. 谁看似在聊，实际没有建立连接
3. 谁在群体里被边缘化

---

## 13. 状态引擎升级

### 13.1 从单中心状态更新升级到图更新

Phase 2 主要是：

1. 一个中心人
2. 对每位 guest 的关系变动

Phase 3 必须支持：

1. `A -> B`
2. `B -> A`
3. `A -> C`
4. `B -> C`
5. 群体层 tension

### 13.2 新增 group-level state

建议新增 `group_state_snapshot`，至少包括：

1. `scene_run_id`
2. `dominant_topics`
3. `attention_distribution`
4. `tension_pairs`
5. `emerging_clusters`
6. `isolated_participants`

### 13.3 事件标签升级

Phase 3 新增的 event tags 至少包括：

1. `cross_talk_alignment`
2. `attention_shift`
3. `competitive_probe`
4. `social_exclusion_signal`
5. `mutual_topic_lock`
6. `soft_interruption`
7. `protective_observation`
8. `status_display`

### 13.4 解释链要求

每次 relationship delta 必须能关联：

1. 来源 event tag
2. 来源 turn id 列表
3. 受影响 participant pair
4. 理由文案

---

## 14. API 设计

### 14.1 导入接口升级

把原有导入接口升级为统一 participant 结构。

建议：

1. 保留旧接口兼容一段时间
2. 新增 `POST /api/projects/{project_id}/participants/import`
3. 新增 `GET /api/projects/{project_id}/participants`

### 14.2 人格编辑接口

至少新增：

1. `GET /api/projects/{project_id}/participants/{participant_id}/personality`
2. `PATCH /api/projects/{project_id}/participants/{participant_id}/personality`
3. `POST /api/projects/{project_id}/personality-presets/apply`

### 14.3 simulation 创建接口升级

`POST /api/projects/{project_id}/simulations` 必须支持：

1. strategy cards
2. participant personality overrides
3. selected participants
4. optional scene pack config

### 14.4 overview DTO 升级

总览页至少新增：

1. `participant_cards`
2. `relationship_graph_preview`
3. `group_tension_summary`
4. `hot_pairs`
5. `isolated_participants`

### 14.5 scene replay DTO 升级

scene replay 至少新增：

1. `rounds`
2. `speaker_switch_summary`
3. `pairwise_impacts`
4. `group_state_after_scene`

### 14.6 新增关系图接口

新增：

1. `GET /api/simulations/{simulation_id}/relationship-graph`

返回至少包括：

1. nodes
2. directed edges
3. edge weights
4. status labels
5. strongest signals

---

## 15. 前端页面规划

Phase 3 至少做 6 个页面层级。

### 15.1 首页 `/`

不再以“主角设定”作为首页主结构，而是：

1. cast roster
2. participant personality setup
3. strategy / scenario setup
4. launch simulation

### 15.2 participant setup 页

建议新增：

1. `/projects/{id}/participants`

必须支持：

1. 查看所有角色
2. 编辑每个角色人格
3. 应用人格预设
4. 预览本次 simulation 的 cast 配置

### 15.3 simulation 总览页

必须展示：

1. 当前 scene
2. scene 进度
3. group tension
4. hot pairs
5. isolated participants
6. scene 跳转

### 15.4 scene 回放页

必须升级为：

1. 按 round 分组
2. 按 turn 展示
3. 可看出谁对谁说
4. 可看出哪些轮次改变了关系图

### 15.5 relationships 页

必须拆成：

1. pairwise cards
2. relationship graph summary
3. 筛选单个 participant 的视图

### 15.6 personality 页

建议新增：

1. `/simulations/{id}/personalities`

必须展示：

1. 本次 simulation 生效的人格快照
2. 与项目默认人格的差异

---

## 16. 前端设计要求

Phase 3 的 UI 必须让用户直观理解“多边关系”。

必须达到：

1. 不再出现“主角视角”主导全页面文案
2. 多角色信息有清晰信息层级
3. 用户能快速理解谁在主导场上氛围
4. 人格配置面板清晰可调，不是 JSON 表单
5. scene replay 明确呈现多轮与多人交叉

避免：

1. 仍然把全局叙事写成“你和他们”
2. 仍然只展示某个人对所有人的单向卡片
3. 仅用原始 metric table 替代叙事展示

---

## 17. 数据迁移要求

Phase 3 必须提供明确的数据迁移策略。

### 17.1 数据库迁移

至少包括：

1. 新建 pairwise relationship graph 表
2. 新建 personality override 表
3. 新建 participant memory 表
4. 保留旧表一段过渡期，或提供一次性迁移脚本

### 17.2 兼容策略

建议：

1. Phase 3 API 先兼容旧导入格式
2. 后端内部统一转换为新 participant 结构
3. 新前端只使用新接口

### 17.3 明确废弃项

Phase 3 结束时，以下结构必须被标记 deprecated：

1. `protagonist_guest_id`
2. `target_guest_id`
3. 首页“主角设定”中心入口
4. planner prompt 中强制 protagonist first 的规则

---

## 18. 实现顺序

Phase 3 必须按下面顺序推进，不允许乱序堆功能。

### Step 1：定义新产品边界和统一 participant schema

完成：

1. 定义 participant 导入格式
2. 定义 personality editable schema
3. 定义 pairwise relationship graph schema
4. 定义新的 replay / overview / graph DTO

交付物：

1. schema 文档
2. Pydantic models
3. API contract 草案

### Step 2：数据库迁移

完成：

1. 新增 pairwise relationship graph 表
2. 新增 participant personality override 表
3. 新增 participant scene memory 表
4. 编写 Alembic migration

交付物：

1. Alembic migration
2. ORM models
3. 迁移说明

### Step 3：移除 protagonist 中心假设

完成：

1. 后端导入逻辑改为统一 participant
2. runtime context 不再使用 protagonist special path
3. planner / agent / referee prompt 去中心化
4. state engine 从单中心更新改为 pairwise graph 更新

交付物：

1. runtime context v2
2. planner/agent/referee prompt v2
3. pairwise update logic

### Step 4：实现多轮多人 turn scheduler

完成：

1. scene orchestrator 输出 round plan
2. next speaker selection
3. 至少 6-12 turn 的 runtime loop
4. turn-level audit / replay persistence

交付物：

1. turn scheduler service
2. multi-round runtime service
3. scheduler test cases

### Step 5：重做 scene_01_intro

完成：

1. 全员第一印象交叉互动
2. 多轮多人 transcript
3. pairwise graph delta
4. group tension summary

交付物：

1. `scene_01_intro` runtime v3
2. replay DTO v3

### Step 6：落地 scene_02_free_talk

完成：

1. `scene_02_free_talk` director/orchestrator
2. 多话题多人互动
3. comfort / understood / curiosity 更新
4. next scene tension 输出

交付物：

1. `scene_02_free_talk` runtime
2. replay API
3. scene acceptance tests

### Step 7：人格编辑能力

完成：

1. participant personality API
2. 前端 personality editor
3. simulation create 时带 override
4. 前端显示本次人格快照

交付物：

1. personality editor page
2. personality persistence
3. audit logs

### Step 8：重做前端页面

完成：

1. 首页去主角中心化
2. overview 支持 group tension
3. replay 支持 rounds
4. relationships 支持图谱视图
5. personalities 页

交付物：

1. 新页面 UI
2. 交互流程验证
3. 截图证据

### Step 9：浏览器验收与 live 验证

完成：

1. 桌面检查
2. 移动检查
3. console 检查
4. network 检查
5. 至少连续 3 次 live simulation 成功

---

## 19. 极为具体的执行清单

这一节是给实施 agent 直接照着做的 checklist。

### 19.1 后端 schema checklist

- 新建 `ParticipantImportRequestV2`
- 新建 `ParticipantPersonalityEditable`
- 新建 `ParticipantPersonalitySnapshot`
- 新建 `PairwiseRelationshipState`
- 新建 `RelationshipGraphResponse`
- 新建 `SceneRound`
- 新建 `SceneReplayResponseV3`
- 新建 `SimulationOverviewResponseV3`

### 19.2 数据库 checklist

- 新增 `participant_personality_overrides`
- 新增 `participant_scene_memories`
- 新增 `relationship_edges` 或等价命名表
- 为 `relationship_edges` 建唯一约束：`simulation_run_id + source_participant_id + target_participant_id`
- 新增 `edge_last_event_tags`
- 新增必要索引：
  - `simulation_run_id`
  - `scene_run_id`
  - `source_participant_id`
  - `target_participant_id`

### 19.3 runtime checklist

- 新建 `scene_orchestrator.py`
- 新建 `turn_scheduler.py`
- 新建 `participant_agent.py`
- 新建 `graph_state_engine.py`
- 把 `scene_01_intro.py` 拆成 planner / scheduler / finalize 结构
- 新增 `scene_02_free_talk.py`
- 新增 `build_pairwise_visibility_context()`
- 新增 `build_group_state_snapshot()`
- 新增 `derive_next_speaker_candidates()`
- 新增 `normalize_multi_round_plan_payload()`
- 新增 `normalize_multi_agent_turn_payload()`
- 新增 `normalize_graph_referee_payload()`

### 19.4 API checklist

- 新增 `POST /participants/import`
- 新增 `GET /participants`
- 新增 `GET /participants/{id}/personality`
- 新增 `PATCH /participants/{id}/personality`
- 新增 `GET /simulations/{id}/relationship-graph`
- 升级 `POST /simulations`
- 升级 `GET /simulations/{id}`
- 升级 `GET /simulations/{id}/scenes/{sceneRunId}`

### 19.5 前端 checklist

- 首页从“主角设定”改为“cast setup”
- 新建 participant roster 卡片
- 新建 personality editor drawer / page
- 新建 relationship graph preview 区
- replay 页支持 rounds 和 target participant 渲染
- overview 页显示 hot pairs / isolated participants / active clusters
- relationships 页支持 participant 过滤器

### 19.6 测试 checklist

- participant 导入兼容旧格式
- personality override 落库成功
- pairwise graph 初始化正确
- `scene_01_intro` 生成至少 6 turn
- `scene_02_free_talk` 能完整运行
- 非中心角色之间能直接互动
- relationship graph 更新不是只围绕单个 participant
- live 模式连续运行 3 次成功

---

## 20. 交付要求

这一节是 Phase 3 的硬性交付要求，不能只做其中一部分。

### 20.1 文档交付

必须交付：

1. `PHASE3_PLAN.md`
2. 数据迁移说明
3. personality schema 文档
4. relationship graph 说明
5. 页面截图与验证记录

### 20.2 后端交付

必须交付：

1. 新 ORM 模型
2. Alembic migration
3. 新 runtime 服务
4. 新 API DTO
5. `scene_02_free_talk` 实现

### 20.3 前端交付

必须交付：

1. 首页去主角中心化改版
2. personality 编辑页
3. overview v3
4. replay v3
5. relationships v3

### 20.4 验证交付

必须交付：

1. 至少 4 张桌面截图
2. 至少 2 张移动截图
3. console 检查结果
4. network 检查结果
5. live 成功运行记录

---

## 21. Phase 3 验收标准

这一节是最重要的。只有全部满足，Phase 3 才算完成。

### 21.1 架构验收标准

必须同时满足：

1. 后端内部不再依赖 `protagonist_guest_id`
2. 后端内部不再要求 `role == protagonist` 才能成为关系中心
3. pairwise relationship graph 能表达任意角色对任意角色的状态
4. personality override 能进入 simulation runtime

### 21.2 runtime 验收标准

必须同时满足：

1. `scene_01_intro` 至少生成 6 turn
2. `scene_02_free_talk` 能完整运行
3. transcript 中存在非中心角色之间的直接或间接互动
4. next speaker 不是固定死序
5. pairwise relationship updates 不只发生在单一角色向外

### 21.3 前端验收标准

必须同时满足：

1. 首页不再以“主角设定”为中心
2. 用户可以调整每个角色的人格
3. overview 能展示 group tension 和多边关系概览
4. replay 页能看懂多轮多人互动
5. relationships 页能看懂多边关系，而不是单中心卡片

### 21.4 浏览器验收标准

必须同时满足：

1. 首页 `console` 无关键错误
2. personality 编辑页无关键错误
3. replay 页无关键 API 失败
4. relationships 页无 loading 卡死
5. 桌面端可正常操作
6. 移动端无明显布局崩坏

### 21.5 live 验收标准

必须同时满足：

1. 在 live DashScope 模式下连续 3 次完成 `scene_01_intro`
2. 在 live DashScope 模式下连续 3 次完成 `scene_02_free_talk`
3. 不允许因为 schema 漂移直接导致 runtime 崩溃
4. 失败时保留当次已生成 transcript 和 audit logs

### 21.6 用户体验验收标准

必须同时满足：

1. 用户可以看懂“谁在和谁建立连接”
2. 用户可以看懂“谁只是围观”
3. 用户可以看懂“为什么某个角色变主动或变回避”
4. 用户可以看懂“人格调整如何影响结果”

### 21.7 明确判定为未完成的情况

出现下面任一情况，Phase 3 一律判定为未完成：

1. 只是把 Phase 2 的 turn 数改长，但关系仍然是主角中心
2. 虽然 UI 改成多人，但数据库仍然使用 `protagonist_guest_id`
3. 虽然号称平权，但只有一个角色能调人格
4. `scene_02_free_talk` 仍然只是占位
5. replay 页仍然看不出多人交叉互动
6. pairwise relationship graph 只是前端假数据

---

## 22. 推荐改造文件清单

建议至少新增或改造这些文件：

```text
backend/alembic/versions/0003_phase3_participant_graph.py

backend/app/models/participant_personality_override.py
backend/app/models/participant_scene_memory.py
backend/app/models/relationship_edge.py

backend/app/schemas/participant.py
backend/app/schemas/personality.py
backend/app/schemas/relationship_graph.py
backend/app/schemas/runtime_v3.py

backend/app/services/simulation/participant_service.py
backend/app/services/simulation/graph_state_engine.py
backend/app/services/simulation/turn_scheduler.py
backend/app/services/simulation/scene_orchestrator.py

backend/app/services/director/scene_01_intro_v3.py
backend/app/services/director/scene_02_free_talk.py

backend/app/api/routes/participants.py

frontend/app/page.tsx
frontend/app/projects/[id]/participants/page.tsx
frontend/app/simulations/[id]/page.tsx
frontend/app/simulations/[id]/scenes/[sceneRunId]/page.tsx
frontend/app/simulations/[id]/relationships/page.tsx
frontend/app/simulations/[id]/personalities/page.tsx
frontend/lib/api.ts
frontend/lib/presentation.ts
```

---

## 23. 最终结论

Phase 3 的本质不是“让当前系统多说几句话”，而是：

1. 把单中心结构升级为平等多边结构
2. 把最小 turn loop 升级为真实多人多轮场景
3. 把人物资料升级为可调人格系统

如果只完成其中一个方向，Phase 3 都不算完成。

Phase 3 的唯一合格交付，是一个：

> 能跑多轮多人互动、能表达多边关系图、且允许用户调整每个角色人格的去中心化关系模拟器。
