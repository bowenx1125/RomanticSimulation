# 第二阶段实现计划

这份文档定义 Phase 2 的目标、范围、架构、接口、数据表、执行时序、前端页面和验收标准。

目标不是继续堆概念，而是把下一阶段的实现边界锁死，让下一个 session 的 agent 可以直接开工，不需要用户反复补充上下文。

---

## 1. Phase 2 总目标

Phase 2 必须同时完成两件事：

1. 把当前 `scene_01_intro` 从“单次 Director 产出结果”升级为“Director 编排 + 多个 LLM Agent 来回对话 + Referee/Director Finalize 收束”的真实多 Agent runtime
2. 把当前调试型前端升级为可用的产品界面，并且把浏览器级页面检查纳入实现流程

当前 Phase 1 已经证明：

1. `project -> import -> simulation -> worker -> scene_01_intro -> result` 这条最小链路能跑通
2. DashScope 百炼兼容接口可以调用
3. Director 的 live 输出会出现 schema 漂移，因此 Phase 2 必须明确协议层

Phase 2 的重点不是扩更多场景，而是先把“单场景的真实多 Agent 系统”做对，再扩展到后续场景。

---

## 2. Phase 2 范围

### 2.1 必做范围

Phase 2 必做内容：

1. 修复前端生产资源 404 和 hydration 问题
2. 新增多 Agent scene runtime
3. 为 scene 级 turn-by-turn 记录建表
4. 新增 `scene_01_intro` 的真实多 Agent 回合执行
5. 新增用于回放和状态展示的 API DTO
6. 重做首页和 simulation 详情页
7. 新增 scene 回放页
8. 使用浏览器工具实际检查 UI 和交互结果

### 2.2 暂不做范围

Phase 2 明确不做：

1. 全部 9 个场景都升级成多 Agent
2. 实验分支系统
3. 最终完整报告页
4. 多用户系统
5. 流式 token 级实时打字效果
6. 完整移动端独立设计系统

### 2.3 场景范围

Phase 2 只要求：

1. `scene_01_intro` 完整升级为多 Agent runtime
2. `scene_02_free_talk` 预留接口和结构，但不要求必须在本阶段完成

---

## 3. 当前问题与设计原则

### 3.1 当前问题

当前实现存在以下问题：

1. `Director` 既是导演，又在替 Agent 做结果裁决，角色职责过重
2. `guest_directives` 只是占位字段，不是真实 Agent 执行结果
3. live LLM 输出存在 schema 漂移，必须显式做协议规范化
4. 前端页面是调试面板，不是产品页面
5. 前端生产容器的 `_next/static` 资源存在 404，运行链路本身不稳

### 3.2 Phase 2 设计原则

Phase 2 必须遵守：

1. 先把单场景多 Agent runtime 做稳，再扩更多场景
2. `Director` 只负责场景编排和裁决，不直接代替所有 Agent 发言
3. 每个 Agent 必须有独立输入、独立输出、独立审计记录
4. 前端不直接暴露所有底层 JSON 给用户
5. 所有 UI 交付必须经过浏览器级检查，不接受“代码看起来没问题”

---

## 4. 架构升级目标

Phase 1 的执行链路是：

```text
worker
  ->
director (single call)
  ->
validated output
  ->
state apply
```

Phase 2 要升级为：

```text
worker
  ->
director_plan
  ->
agent_turn_loop
  ->
scene_referee / director_finalize
  ->
validated scene result
  ->
state apply
  ->
scene replay DTO
```

### 4.1 新角色职责

#### Director

职责：

1. 定义本场 scene 的目标和 tension
2. 指定参与者、回合顺序、每个 Agent 的 directive
3. 提供 stop condition
4. 在最后阶段生成结构化收束结果，或交给 Referee 模块收束

不负责：

1. 替所有 Agent 逐句表演
2. 直接绕过 transcript 凭空决定结果

#### Agent

职责：

1. 基于自己的人设、局部可见上下文和 director directive 生成本角色的发言与行为
2. 只输出自己角色的内容
3. 保持人格一致性

不负责：

1. 决定整个场景最终关系结果
2. 读取自己不该知道的全局信息

#### Scene Referee / Director Finalize

职责：

1. 汇总 turn transcript
2. 抽取 major events / event tags
3. 生成关系变量变化
4. 输出可持久化的 scene 结果

不负责：

1. 重新创造一条与 transcript 无关的新剧情

#### State Engine

职责：

1. 应用 delta
2. 刷新 relationship status
3. 写 snapshot
4. 写 audit logs

---

## 5. 多 Agent Runtime 设计

### 5.1 Phase 2 必须实现的最小真实多 Agent 流程

`scene_01_intro` 的最小多 Agent 流程固定为：

1. `DirectorPlan`
2. `ProtagonistTurn`
3. `GuestTurn #1`
4. `GuestTurn #2`
5. 如果场景里有第三位 guest，则可选 `GuestTurn #3`
6. `DirectorFinalize` 或 `SceneRefereeResult`

### 5.2 Turn Loop 规则

每个场景必须支持：

1. 最少 3 个 turn
2. 最多 8 个 turn
3. 每个 turn 必须记录 `speaker`
4. 每个 turn 必须记录 `visible_context`
5. 每个 turn 必须记录 `utterance`
6. 每个 turn 必须记录 `intent_tags`
7. 每个 turn 必须记录 `target_guest_ids`

### 5.3 局部可见性规则

Agent 输入必须做可见性裁剪：

1. 每个 Agent 只能看到 scene 当前共享上下文
2. 每个 Agent 可以看到自己的人设和对主角的关系状态
3. 不允许看到其他 Agent 的隐藏心理状态全文
4. 不允许直接看到最终裁决字段

### 5.4 Scene Stop Condition

`scene_01_intro` 的 stop condition 固定为：

1. 所有主要角色至少完成一轮有效互动
2. Director 认为初始印象已形成
3. Transcript 达到最小信息量阈值

---

## 6. 新的结构化对象

Phase 2 至少新增以下 schema。

### 6.1 DirectorPlan

```json
{
  "scene_id": "scene_01_intro",
  "scene_goal": "建立第一印象和初始吸引力",
  "scene_frame": "阳光房初见，围绕城市通勤和节目第一印象破冰",
  "participants": [
    {
      "guest_id": "protagonist_id",
      "name": "林夏",
      "role": "protagonist"
    },
    {
      "guest_id": "guest_01",
      "name": "周予安",
      "role": "guest"
    }
  ],
  "turn_order": ["protagonist", "guest_01", "guest_02"],
  "agent_directives": [
    {
      "guest_id": "guest_01",
      "directive": "以稳定回应降低陌生感"
    }
  ],
  "evaluation_focus": [
    "initial_attraction",
    "comfort",
    "curiosity"
  ],
  "stop_condition": "所有核心参与者完成首次有效互动"
}
```

### 6.2 AgentTurn

```json
{
  "speaker_guest_id": "guest_01",
  "speaker_name": "周予安",
  "turn_index": 2,
  "utterance": "你这个比喻挺准，早高峰确实像被迫参与结构实验。",
  "behavior_summary": "主动接话，语气稳定，不抢场",
  "intent_tags": ["build_comfort", "signal_interest"],
  "target_guest_ids": ["protagonist_id"],
  "self_observation": "她有观察力，适合继续接近"
}
```

### 6.3 SceneRefereeResult

```json
{
  "scene_id": "scene_01_intro",
  "scene_summary": "初见完成，稳定型和火花型对象都留下了不同风格的第一印象。",
  "major_events": [
    {
      "title": "稳定回应降低陌生感",
      "event_tags": ["value_alignment"]
    }
  ],
  "relationship_deltas": [
    {
      "guest_id": "guest_01",
      "changes": {
        "initial_attraction": 8,
        "comfort": 10,
        "curiosity": 6
      },
      "reason": "对话中稳定接话和细节感明显降低了主角焦虑。"
    }
  ],
  "next_tension": "下一场自由交流会把第一印象转化成真实相处感。"
}
```

---

## 7. 数据表设计

Phase 2 在保留 Phase 1 表的基础上，新增以下表。

### 7.1 `scene_messages`

用途：

1. 存储每个 turn 的可回放消息
2. 支持前端 scene timeline 展示

字段建议：

1. `id`
2. `simulation_run_id`
3. `scene_run_id`
4. `turn_index`
5. `speaker_guest_id`
6. `speaker_name`
7. `message_role`
8. `utterance`
9. `behavior_summary`
10. `intent_tags JSONB`
11. `target_guest_ids JSONB`
12. `visible_context_summary JSONB`
13. `raw_output JSONB`
14. `created_at`

### 7.2 `agent_turns`

用途：

1. 记录每个 Agent 的调用输入输出
2. 区分前端回放数据和后端审计数据

字段建议：

1. `id`
2. `simulation_run_id`
3. `scene_run_id`
4. `turn_index`
5. `guest_id`
6. `agent_name`
7. `status`
8. `input_payload JSONB`
9. `raw_output JSONB`
10. `normalized_output JSONB`
11. `error_message`
12. `started_at`
13. `finished_at`
14. `created_at`

### 7.3 `scene_artifacts`

用途：

1. 存储场景计划、裁决结果、scene replay 用的结构化对象

字段建议：

1. `id`
2. `simulation_run_id`
3. `scene_run_id`
4. `artifact_type`
5. `payload JSONB`
6. `created_at`

`artifact_type` 至少包括：

1. `director_plan`
2. `scene_referee_result`
3. `scene_replay_dto`

---

## 8. API 设计

Phase 2 需要在保留 Phase 1 API 的基础上新增以下接口。

### 8.1 保留接口

保留：

1. `POST /api/projects`
2. `POST /api/projects/{project_id}/guests/import`
3. `GET /api/projects/{project_id}`
4. `POST /api/projects/{project_id}/simulations`
5. `GET /api/simulations/{simulation_id}`

### 8.2 改造 `GET /api/simulations/{simulation_id}`

从“最小状态返回”升级为“总览 DTO”。

新增返回字段：

1. `scene_timeline_preview`
2. `relationship_cards`
3. `latest_scene_replay_url`
4. `active_tension`

### 8.3 新增 `GET /api/simulations/{simulation_id}/scenes/{scene_run_id}`

用途：

1. 获取某一场 scene 的完整回放数据

返回至少包括：

1. `scene_plan`
2. `messages`
3. `major_events`
4. `relationship_deltas`
5. `next_tension`

### 8.4 新增 `GET /api/simulations/{simulation_id}/timeline`

用途：

1. 获取 simulation 总时间线
2. 支持前端总览页

返回至少包括：

1. 每个 scene 的状态
2. 每个 scene 的简要摘要
3. 每个 scene 的 tension

### 8.5 新增 `GET /api/simulations/{simulation_id}/relationships`

用途：

1. 单独为关系面板提供数据

返回至少包括：

1. `guest_id`
2. `guest_name`
3. `status`
4. `trend`
5. `top_reasons`
6. `surface_metrics`

---

## 9. Worker 执行时序

### 9.1 Phase 2 标准时序

```text
claim scene_run
  ->
load simulation context
  ->
build director input
  ->
call director_plan
  ->
persist director_plan artifact
  ->
for turn in turn_order:
    build agent input
    call agent
    normalize output
    persist agent_turn
    persist scene_message
  ->
build referee input from transcript
  ->
call scene_referee / director_finalize
  ->
validate final result
  ->
apply relationship deltas
  ->
write state_snapshot
  ->
write audit_logs
  ->
mark scene completed
```

### 9.2 Worker 失败恢复规则

Phase 2 必须支持：

1. 单个 `agent_turn` 失败时，整个 scene_run 标记 failed
2. 失败时必须保留已经生成的 director_plan 和已完成 turn
3. 重试时允许从头重跑整个 scene
4. Phase 2 暂不做“从第 N turn 断点续跑”

### 9.3 幂等规则

必须保证：

1. 同一 `scene_run` 同时只有一个 worker 执行
2. 同一轮 `turn_index + guest_id` 不重复写入成功记录
3. `scene_referee_result` 和 `state_snapshot` 在同一事务边界内提交

---

## 10. 前端页面规划

Phase 2 至少做 4 个页面层级。

### 10.1 首页 `/`

目标：

1. 不再是原始 JSON 导入面板
2. 成为“新建实验”的入口页

必须展示：

1. 产品说明区
2. 主角信息卡
3. 嘉宾卡列表
4. 策略卡选择器
5. 创建 simulation 主按钮

可以保留：

1. 一个折叠的“高级 JSON 编辑器”，仅供调试

### 10.2 Simulation 总览页 `/simulations/{id}`

目标：

1. 成为 simulation 的主页面，不再只展示 JSON

必须展示：

1. simulation status
2. 当前 scene
3. 进度时间线
4. 当前 tension
5. 关系概览卡片
6. 最新 scene 摘要
7. 跳转到 scene 回放页

### 10.3 Scene 回放页 `/simulations/{id}/scenes/{sceneRunId}`

目标：

1. 显示真实多 Agent 回放

必须展示：

1. director 开场说明
2. turn-by-turn transcript timeline
3. 每条消息的 speaker
4. major events
5. 本场状态变化卡片
6. next tension

### 10.4 关系观察页 `/simulations/{id}/relationships`

目标：

1. 集中展示当前关系走向

必须展示：

1. 每位嘉宾当前状态
2. 趋势标签
3. 1-2 条关键原因
4. 不直接暴露所有底层 metrics

---

## 11. 前端设计要求

Phase 2 的 UI 不接受“后台管理页 + 原始 JSON”的形态。

必须达到：

1. 首页有明确 Hero、实验入口和人物卡片结构
2. Simulation 总览页有明显信息层级
3. Scene 回放页必须是 timeline，不是 JSON dump
4. 关系卡片必须是可读叙事卡，而不是指标表
5. 桌面和移动端都必须可用

避免：

1. 大面积裸文本
2. 用户必须读 JSON 才能理解结果
3. 所有信息塞进同一个页面

---

## 12. 浏览器检查与 MCP 验证要求

Phase 2 必须把浏览器检查纳入实现流程。

建议固定使用现有 `browse` skill 的方式做验证。

每个关键页面都必须检查：

1. `goto`
2. `snapshot -i -a`
3. `console`
4. `network`
5. `responsive`

必须覆盖：

1. 首页
2. simulation 总览页
3. scene 回放页
4. relationships 页

必须保留的验证证据：

1. 桌面截图
2. 移动截图
3. 控制台错误结果
4. 网络失败结果

硬性要求：

1. 不允许 `_next/static` 资源 404
2. 不允许关键 API 500
3. 不允许页面停在永久 loading 状态

---

## 13. 实现顺序

Phase 2 必须按下面顺序推进。

### Step 1：修前端运行链路

完成：

1. 修复生产环境 `_next/static` 404
2. 确保首页和详情页 hydration 正常
3. 浏览器控制台无关键报错

### Step 2：定义多 Agent schema

完成：

1. 定义 `DirectorPlan`
2. 定义 `AgentTurn`
3. 定义 `SceneRefereeResult`
4. 定义对应 API DTO

### Step 3：新增数据库表和迁移

完成：

1. `scene_messages`
2. `agent_turns`
3. `scene_artifacts`
4. Alembic migration

### Step 4：实现 scene_01_intro 多 Agent runtime

完成：

1. director plan 调用
2. 2-3 个 Agent turn loop
3. referee/finalize 调用
4. transcript 落库
5. snapshot 落库

### Step 5：重做前端页面

完成：

1. 首页
2. simulation 总览页
3. scene 回放页
4. relationships 页

### Step 6：浏览器级验收

完成：

1. 桌面端检查
2. 移动端检查
3. 控制台检查
4. 网络检查

---

## 14. Phase 2 验收标准

这一节是最重要的。只有全部满足，Phase 2 才算完成。

### 14.1 后端验收标准

必须同时满足：

1. `scene_01_intro` 不再只是单次 Director 输出，而是至少 3 个 turn 的真实多 Agent transcript
2. 每个 Agent turn 都能在数据库中查到独立记录
3. `GET /api/simulations/{id}/scenes/{sceneRunId}` 能返回可回放数据
4. `director_plan`、`director_raw_output`、`director_validated_output`、`agent_turns`、`scene_referee_result` 都有审计记录
5. live 百炼模式下，连续 3 次运行 `scene_01_intro`，至少 3 次都能完成，不允许因 schema 漂移直接失败
6. worker 失败时，scene_run 会标记 failed 且保留已产生日志

### 14.2 前端验收标准

必须同时满足：

1. 首页不再要求用户直接编辑整块 JSON 才能完成主流程
2. simulation 总览页能显示当前 scene、进度、关系概览、最新摘要
3. scene 回放页能逐条显示 transcript
4. relationships 页能显示每位嘉宾的状态和关键原因
5. 所有关键页面在桌面宽度下可正常操作
6. 所有关键页面在移动宽度下不出现布局崩坏

### 14.3 浏览器验收标准

必须同时满足：

1. 首页 `console` 无关键错误
2. 首页 `network` 无 `_next/static` 404
3. simulation 总览页 `console` 无关键错误
4. scene 回放页 `network` 无关键 API 失败
5. relationships 页能正常渲染而不是 loading 卡死
6. 至少提供 4 张截图证据：
   - 首页桌面
   - simulation 总览页桌面
   - scene 回放页桌面
   - 任一关键页移动端

### 14.4 用户体验验收标准

必须同时满足：

1. 用户可以看懂“谁说了什么”
2. 用户可以看懂“为什么关系变了”
3. 用户不需要阅读原始 JSON 才能理解场景结果
4. 页面信息层级符合产品阅读习惯，而不是开发调试习惯

### 14.5 明确判定为未完成的情况

出现下面任一情况，Phase 2 一律判定为未完成：

1. 只有 Director 输出，没有真实 Agent turn
2. transcript 只存在内存里，没有落库
3. 页面只是把更多 JSON dump 到前端
4. 浏览器里仍然有 `_next/static` 404
5. 页面能打开但客户端逻辑没跑起来
6. live 模式只成功一次，不能稳定重复运行

---

## 15. 推荐文件清单

建议至少新增或改造这些文件：

```text
backend/app/models/scene_message.py
backend/app/models/agent_turn.py
backend/app/models/scene_artifact.py
backend/app/schemas/scene_runtime.py
backend/app/services/director/planner.py
backend/app/services/agents/runtime.py
backend/app/services/agents/guest_agent.py
backend/app/services/simulation/scene_runtime.py
backend/app/api/routes/scenes.py
backend/alembic/versions/0002_phase2_runtime.py

frontend/app/page.tsx
frontend/app/simulations/[id]/page.tsx
frontend/app/simulations/[id]/scenes/[sceneRunId]/page.tsx
frontend/app/simulations/[id]/relationships/page.tsx
frontend/components/*
frontend/lib/api.ts
```

---

## 16. 风险与应对

### 风险 1：Agent turn 太自由导致人格漂移

应对：

1. 每个 Agent 只拿局部可见上下文
2. Director 先下 directive
3. Referee 只根据 transcript 裁决

### 风险 2：live LLM schema 继续漂移

应对：

1. 继续保留 normalize 层
2. 明确区分 raw_output 和 validated_output
3. 对异常格式保留原始日志

### 风险 3：前端做成漂亮但不可验证

应对：

1. 所有页面必须用浏览器工具验证
2. 截图、console、network 三者都要留证据

### 风险 4：范围失控

应对：

1. Phase 2 只要求 `scene_01_intro` 真正升级
2. `scene_02_free_talk` 只预留结构
3. 不要顺手扩成 9 场景

---

## 17. 下一 session 启动指令

下面这段文字是为下一个 session 的 agent 准备的。清空上下文后，直接把这段发给新 agent 即可。
同样内容也已经单独保存到 [NEXT_SESSION_PROMPT.md](/Users/tangbao/project/恋爱模拟器/NEXT_SESSION_PROMPT.md)。

```text
你现在接手 /Users/tangbao/project/恋爱模拟器 的 Phase 2 实现。

先阅读这些文档，并以它们为唯一当前目标来源：
1. /Users/tangbao/project/恋爱模拟器/PHASE2_PLAN.md
2. /Users/tangbao/project/恋爱模拟器/PHASE1_IMPLEMENTATION.md
3. /Users/tangbao/project/恋爱模拟器/BACKEND_ARCHITECTURE.md
4. /Users/tangbao/project/恋爱模拟器/SCENE_DESIGN.md
5. /Users/tangbao/project/恋爱模拟器/STATE_UPDATE_RULES.md
6. /Users/tangbao/project/恋爱模拟器/Soul.md
7. /Users/tangbao/project/恋爱模拟器/API_Test.py

你的任务不是讨论，而是直接连续实现 PHASE2_PLAN.md，直到 Phase 2 的验收标准满足为止。

你必须按下面顺序主动使用本地 skill：
1. `investigate`
作用：先找清楚并修复当前真实阻塞问题，尤其是前端 `_next/static` 404、hydration/页面 loading 卡死、live LLM schema 漂移。
2. `browse`
作用：真实打开页面检查 `console`、`network`、`snapshot/screenshot`、响应式结果。每个关键 UI 节点完成后都必须再次使用。
3. `design-review`
作用：在页面可以正常运行后，直接把首页、simulation 总览页、scene 回放页、relationships 页做成可用产品界面，而不是调试面板。
4. `qa`
作用：Phase 2 功能完成后，系统化测试并修剩余问题，直到达到可交付状态。
5. `review`
作用：所有实现完成后，再做一次结构性代码审查，检查多 Agent runtime、事务边界、接口和风险点。

执行约束：
1. 不要向用户询问任务拆分或是否继续，直接做
2. 先修前端生产资源 404 和 hydration 问题
3. 然后实现多 Agent runtime：director_plan -> agent_turn_loop -> referee/finalize -> state apply
4. 然后重做前端页面：首页、simulation 总览页、scene 回放页、relationships 页
5. 每完成关键 UI 节点，都必须用 `browse` 真实打开页面检查：
   - console
   - network
   - snapshot / screenshot
   - 必要时 responsive
6. 必须优先保证 live 百炼模式可稳定跑通，不要只在 mock 模式下自证成功
7. 所有新增接口、数据表、worker 时序都必须对照 PHASE2_PLAN.md
8. 在想结束之前，逐条对照 PHASE2_PLAN.md 的“Phase 2 验收标准”，未全部满足不得结束

已知事实：
1. Phase 1 已完成，最小闭环已打通
2. 现有 live director 已经能调用阿里云 DashScope 百炼兼容接口
3. 现有前端页面在生产容器中存在 _next/static 404，必须优先修复
4. 当前 scene_01_intro 仍然不是完整多 Agent runtime
5. 本地已经有 DashScope 兼容调用参考代码，见 /Users/tangbao/project/恋爱模拟器/API_Test.py

环境与模型要求：
1. 优先使用当前环境中的 DASHSCOPE_API_KEY
2. 默认使用 DIRECTOR_PROVIDER_MODE=auto
3. 如需参考百炼兼容调用方式，直接看 API_Test.py

你的目标是交付代码，而不是只写分析。
```

---

## 18. 状态

STATUS: READY_FOR_IMPLEMENTATION

这份文档已经足够让下一个 session 直接进入实现阶段，不需要再做额外规划。
