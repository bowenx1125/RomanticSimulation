## 恋爱模拟器 Version 0.1

这份文档是当前阶段的统一基线，供后续实现团队查阅。

目标不是描述所有长期愿景，而是明确：

1. 当前确认的 MVP 是什么
2. 技术路线和架构怎么定
3. 第一阶段实现先做什么
4. 哪些内容明确不在当前版本范围内

## 1. 产品定位

产品不是单纯的恋爱匹配打分器，而是“恋爱可能性实验室”。

用户一方面扮演恋综中的主角嘉宾，把自己投放进节目；另一方面又是实验者，可以创建实验分支，修改人格和策略，观察关系走向如何变化。

产品核心价值：

1. 展示关系如何一步步变化
2. 展示哪些策略和行为推动了升温或降温
3. 解释为什么没谈上，或者为什么谈上了
4. 允许用户在实验分支中重跑关键场景，观察不同走向

## 2. 当前 MVP 范围

### 2.1 MVP 目标

第一版要证明 3 件事：

1. 恋综场景驱动的模拟是否真的有趣
2. 不同人格和策略是否会稳定地产生不同关系结果
3. 结果是否足够可解释，能让用户愿意继续重跑实验

### 2.2 MVP 核心功能

MVP 包含以下能力：

1. 导入聊天记录、嘉宾背景和补充描述
2. 构建主角和其他嘉宾的初始 `Soul`
3. 按固定恋综场景推进一局模拟
4. 每个场景结束后记录状态变更和关键事件
5. 产出最终关系故事结算
6. 基于主线创建实验分支，重跑后续场景

### 2.3 MVP 形态

当前版本是：

1. 单用户内部验证型 Web 产品
2. Local-first 运行
3. 使用真实多 Agent 架构
4. 由场景导演统一约束每个场景的结构化结果

## 3. 已确认的技术决策

以下决策已经确认，不再反复讨论：

1. MVP 范围：保留较完整的版本，不做极度收缩
2. 后端形态：单体后端，但内部模块边界明确
3. 执行方式：异步任务流水线
4. 状态真相源：数据库主存储
5. LLM 角色：LLM 主导场景走向与结果
6. 安全壳：必须有场景编排器和审计日志
7. 场景执行方式：导演式两阶段
8. Agent 架构：真实多 Agent
9. 用户系统：单用户内部验证型 MVP
10. 部署形态：Local-first + Docker Compose
11. 技术栈：Next.js App Router + FastAPI + Worker + Postgres + Redis
12. 编排模式：数据库驱动编排
13. 导演输出：严格 schema 的 JSON

## 4. 架构总览

```text
┌────────────────────┐
│   Next.js Frontend │
│                    │
│ - 导入资料          │
│ - 查看角色/Soul     │
│ - 发起模拟          │
│ - 查看进度/结果      │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│    FastAPI API     │
│                    │
│ - project/session   │
│ - import endpoints  │
│ - simulation APIs   │
│ - result APIs       │
└─────────┬──────────┘
          │
          ▼
┌─────────────────────────────────────┐
│              Postgres               │
│                                     │
│ projects / guest_profiles           │
│ simulation_runs / scene_runs        │
│ relationship_states                 │
│ state_snapshots / audit_logs        │
│ final_reports                       │
└───────┬───────────────────────┬─────┘
        │                       │
        ▼                       ▼
┌──────────────┐        ┌─────────────────────┐
│ Redis        │        │ Worker              │
│              │        │                     │
│ - queue      │        │ - simulation runner │
│ - locks      │        │ - scene director    │
│ - dedupe     │        │ - guest agents      │
└──────────────┘        │ - state applier     │
                        │ - report generator  │
                        └─────────┬───────────┘
                                  │
                                  ▼
                        ┌─────────────────────┐
                        │   LLM Provider      │
                        │                     │
                        │ - scene director     │
                        │ - guest agents       │
                        │ - report writer      │
                        └─────────────────────┘
```

## 5. 核心模块

后端虽然是单体，但必须按模块实现：

1. `ingestion`
说明：导入和解析聊天记录、背景资料、补充文档。

2. `soul_builder`
说明：根据资料生成初始 `Soul` 和初始关系状态。

3. `simulation_orchestrator`
说明：创建和推进 `simulation_run` 与 `scene_run`。

4. `scene_director`
说明：组织导演 Prompt，拿到场景级结构化结果。

5. `agent_runtime`
说明：驱动每位角色 Agent，在导演约束下生成局部行为和对白片段。

6. `state_engine`
说明：把导演输出和 Agent 行为转换成状态更新、快照和审计日志。

7. `reporting`
说明：生成最终结算、分支对比和解释性报告。

## 6. 核心执行链路

```text
用户点击“开始模拟”
  ->
API 创建 simulation_run
  ->
生成 9 个 scene_run
  ->
Worker 抢到当前待执行 scene_run
  ->
读取主角 Soul、其他嘉宾 Soul、关系状态、策略卡、历史场景记录
  ->
Scene Director 输出严格 JSON:
  - scene_summary
  - major_events
  - guest directives
  - relationship_deltas
  - next tension
  ->
各 Guest Agent 基于导演约束生成代表性行为/对白片段
  ->
State Engine 应用状态更新
  ->
写入 audit_logs + state_snapshots
  ->
下一个 scene_run 进入执行
  ->
最终生成 final_report
```

## 7. 最小数据模型

MVP 至少需要以下核心实体：

1. `projects`
2. `guest_profiles`
3. `simulation_runs`
4. `scene_runs`
5. `relationship_states`
6. `state_snapshots`
7. `audit_logs`
8. `final_reports`

建议：

1. `Postgres` 做唯一真相源
2. `Redis` 不持久化业务真相，只做队列、锁、防重
3. 场景导演输出和审计内容优先存 `JSONB`

## 8. 当前版本明确不做

以下内容不在 Version 0.1 范围内：

1. 多用户注册登录和复杂权限系统
2. 公网部署、多环境运维和线上成本优化
3. 实时逐句直播式对聊界面
4. 协作式 workspace
5. 自动化 Prompt 评测平台
6. 移动端独立客户端

## 9. 第一阶段实现目标

Version 0.1 的第一阶段不是写完全部功能，而是打通最小主链路：

1. 起前后端和基础依赖
2. 建核心数据库表
3. 实现 `create simulation_run`
4. 实现 `scene_01` 的导演执行和落库
5. 能在前端看到模拟任务状态和 `scene_01` 的结构化结果

第一阶段验收标准：

1. 可以本地一键启动基础服务
2. 可以创建一个项目和一组嘉宾资料
3. 可以创建一局模拟
4. Worker 能成功执行 `scene_01`
5. Postgres 中能看到 `scene_run`、`audit_log`、`state_snapshot`
6. 前端能查看本局模拟的当前状态

## 10. 与现有文档的关系

本文件不替代其他详细文档，而是作为总索引。

详细定义仍以以下文件为准：

1. [product.md](/Users/tangbao/project/恋爱模拟器/product.md)
2. [Soul.md](/Users/tangbao/project/恋爱模拟器/Soul.md)
3. [SCENE_DESIGN.md](/Users/tangbao/project/恋爱模拟器/SCENE_DESIGN.md)
4. [STATE_UPDATE_RULES.md](/Users/tangbao/project/恋爱模拟器/STATE_UPDATE_RULES.md)

## 11. 后续实现优先级

实现顺序建议固定为：

1. `BACKEND_ARCHITECTURE.md`
2. `PROMPT_ARCHITECTURE.md`
3. 第一阶段代码骨架
4. `scene_01` 到 `scene_03`
5. 基础结果页
6. 实验分支复制
7. 完整 9 场景和最终报告
