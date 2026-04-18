## 第一阶段实现计划

这份文档定义“第一步实现”到底要做什么，供后续多 Agent 团队直接拆工。

## 1. 第一阶段目标

第一阶段只做一件事：

打通从“创建项目”到“执行第一个场景”再到“查看结果”的最小闭环。

不追求完整玩法，不追求漂亮 UI，不追求全部场景。

## 2. 第一阶段完成后，应该能演示什么

演示脚本应当是：

1. 启动本地服务
2. 创建一个项目
3. 导入主角和 2-3 位嘉宾资料
4. 发起一局模拟
5. Worker 执行 `scene_01_intro`
6. 前端页面显示：
   - 当前 simulation status
   - 当前 scene status
   - director 输出摘要
   - 一份 state snapshot

## 3. 实施分工建议

如果后续要拉多 Agent 团队，第一阶段建议分成 4 个子任务：

### Agent 1: 基础后端骨架

负责：

1. 建 `backend/` 基础目录
2. FastAPI app 启动
3. DB 连接和基础配置
4. 核心 ORM 模型骨架
5. 初始 Alembic migration

### Agent 2: Simulation 状态机

负责：

1. `simulation_runs` 和 `scene_runs` 状态机
2. `POST /simulations`
3. `GET /simulations/{id}`
4. scene claim / retry 基础逻辑

### Agent 3: Director + Worker

负责：

1. worker 启动骨架
2. `scene_01_intro` 的 director input builder
3. director schema 校验
4. 审计日志落库

### Agent 4: 最小前端

负责：

1. Next.js 初始化
2. 项目创建页或最简入口页
3. simulation detail 页面
4. 轮询 simulation status

## 4. 第一阶段文件目标

建议第一阶段至少落下这些文件：

```text
backend/app/main.py
backend/app/core/config.py
backend/app/core/db.py
backend/app/models/*.py
backend/app/schemas/*.py
backend/app/api/routes/projects.py
backend/app/api/routes/simulations.py
backend/app/services/simulation/*.py
backend/app/services/director/*.py
backend/app/workers/worker.py
backend/alembic/*

frontend/app/page.tsx
frontend/app/simulations/[id]/page.tsx
frontend/lib/api.ts

docker-compose.yml
```

## 5. 第一阶段验收标准

只有同时满足下面条件，第一阶段才算完成：

1. 本地能通过一个命令起服务
2. API 能创建 project
3. API 能创建 simulation_run
4. Worker 能领取 `scene_01_intro`
5. director 输出通过 schema 校验
6. scene 结果能落库
7. 前端能看到 simulation 状态和 scene 摘要

## 6. 第一阶段的关键风险

### 风险 1：director 输出不稳定

应对：

1. 第一阶段就做严格 schema
2. director 输出失败时直接标记 scene failed
3. 保留原始输出日志

### 风险 2：scene 执行到一半写脏数据

应对：

1. 状态应用必须事务化
2. `scene_run` 更新和 `audit_log` 更新放在同一事务边界内

### 风险 3：前后端一起开工导致接口反复变

应对：

1. 先锁 DTO
2. 前端只吃固定字段：
   - simulation status
   - current scene
   - scene summary
   - audit snippet

## 7. 第一阶段不应该做的事

下面这些如果有人开始做，说明范围跑偏了：

1. 直接做全部 9 场景
2. 直接做实验分支 UI
3. 直接做复杂认证系统
4. 直接做流式逐句对话 UI
5. 直接做完整报告页

## 8. 第一阶段结束后的下一步

第一阶段完成后，第二阶段按这个顺序推进：

1. `scene_02_free_talk`
2. `scene_03_date_pick`
3. 最小结果页
4. branch creation
5. branch rerun
