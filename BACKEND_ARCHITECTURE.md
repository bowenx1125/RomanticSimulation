## 后端架构方案

这份文档定义 Version 0.1 的后端边界、模块职责、数据流和第一阶段代码骨架方向。

## 1. 技术栈

后端采用：

1. `FastAPI`
2. `SQLAlchemy 2.x`
3. `Pydantic v2`
4. `Alembic`
5. `Celery` 或等价 Worker 执行器
6. `Postgres`
7. `Redis`

## 2. 目录建议

```text
backend/
  app/
    api/
      routes/
    core/
      config.py
      db.py
      logging.py
    models/
    schemas/
    services/
      ingestion/
      soul_builder/
      simulation/
      director/
      agents/
      reporting/
    workers/
    prompts/
    tests/
  alembic/
  requirements.txt
```

## 3. 模块职责

### 3.1 api

只负责：

1. 接收请求
2. 调用 service
3. 返回 DTO

禁止：

1. 直接拼 prompt
2. 直接操作复杂状态机
3. 直接跨多表更新场景结果

### 3.2 services/ingestion

职责：

1. 读取导入资料
2. 清洗原始文本
3. 抽取嘉宾、关系对象、背景信息
4. 输出结构化中间数据

### 3.3 services/soul_builder

职责：

1. 基于中间数据构建 `guest_profiles`
2. 生成初始 `Soul snapshot`
3. 初始化初始关系状态

### 3.4 services/simulation

职责：

1. 创建 `simulation_run`
2. 初始化 `scene_runs`
3. 控制状态机推进
4. 控制失败重试和暂停恢复

### 3.5 services/director

职责：

1. 组装 `Scene Director` 输入上下文
2. 调用 LLM
3. 校验 schema
4. 返回结构化导演结果

### 3.6 services/agents

职责：

1. 基于导演约束唤起各 Guest Agent
2. 生成代表性行为摘要或对白片段
3. 保留每个 Agent 的输入输出日志

### 3.7 services/reporting

职责：

1. 生成最终关系结算
2. 生成实验分支对比
3. 输出前端可消费的结果 DTO

## 4. 数据流

```text
POST /simulations
  ->
create simulation_run
  ->
seed scene_runs
  ->
enqueue first runnable scene
  ->
worker claim scene_run
  ->
load current project state
  ->
call director
  ->
validate output
  ->
call guest agents
  ->
apply state changes
  ->
persist audit + snapshot
  ->
mark next scene queued
```

## 5. 第一阶段必须实现的 API

第一阶段只需要 5 个 API：

1. `POST /projects`
创建项目

2. `POST /projects/{project_id}/guests/import`
导入嘉宾资料

3. `GET /projects/{project_id}`
查看项目基础信息

4. `POST /projects/{project_id}/simulations`
创建一局模拟

5. `GET /simulations/{simulation_id}`
查看当前模拟状态和场景进度

## 6. 第一阶段必须实现的 Worker 能力

第一阶段只跑通：

1. `scene_01_intro`

Worker 必须支持：

1. 领取待执行 `scene_run`
2. 加锁避免重复执行
3. 调用导演
4. 校验导演 JSON
5. 落库 `scene_run`、`state_snapshot`、`audit_log`
6. 更新 `simulation_run.current_scene_index`

## 7. 核心模型建议

建议第一阶段先做这几类 ORM 模型：

1. `Project`
2. `GuestProfile`
3. `SimulationRun`
4. `SceneRun`
5. `RelationshipState`
6. `StateSnapshot`
7. `AuditLog`

## 8. 幂等和失败恢复

这是第一阶段就必须设计进去的。

规则：

1. 同一个 `scene_run` 只能有一个 worker 执行
2. `scene_run` 写结果必须事务化
3. 如果写一半失败，整个场景回滚
4. 如果 worker 崩溃，超时后的 `scene_run` 允许重新 claim
5. 重试必须保留 `retry_count`

## 9. 审计日志要求

每个场景至少写入以下日志：

1. director input summary
2. director raw output
3. validated structured output
4. guest agent outputs
5. applied state changes
6. error info if failed

## 10. 第一阶段不做

后端第一阶段明确不做：

1. 全部 9 个场景
2. 分支对比
3. 最终完整报告
4. 多用户隔离
5. 云端部署

## 11. 第一阶段交付物

如果后续多 Agent 团队开始干活，后端组第一阶段交付物应该是：

1. 基础 FastAPI 服务可启动
2. Postgres schema 和 Alembic 初始迁移
3. Redis + Worker 能联通
4. `POST /simulations` 能创建模拟
5. Worker 能执行 `scene_01_intro`
6. `GET /simulations/{id}` 能看到执行结果
