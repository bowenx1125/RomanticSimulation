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
1. 不要向用户询问任务拆分或是否继续，直接做。
2. 先修前端生产资源 404 和 hydration 问题。
3. 然后实现多 Agent runtime：`director_plan -> agent_turn_loop -> referee/finalize -> state apply`。
4. 然后重做前端页面：首页、simulation 总览页、scene 回放页、relationships 页。
5. 每完成关键 UI 节点，都必须用 `browse` 真实打开页面检查：
   - `console`
   - `network`
   - `snapshot / screenshot`
   - 必要时 `responsive`
6. 必须优先保证 live 百炼模式可稳定跑通，不要只在 mock 模式下自证成功。
7. 所有新增接口、数据表、worker 时序都必须对照 `PHASE2_PLAN.md`。
8. 在想结束之前，逐条对照 `PHASE2_PLAN.md` 的“Phase 2 验收标准”，未全部满足不得结束。

已知事实：
1. Phase 1 已完成，最小闭环已打通。
2. 现有 live director 已经能调用阿里云 DashScope 百炼兼容接口。
3. 现有前端页面在生产容器中存在 `_next/static` 404，必须优先修复。
4. 当前 `scene_01_intro` 仍然不是完整多 Agent runtime。
5. 本地已经有 DashScope 兼容调用参考代码，见 `/Users/tangbao/project/恋爱模拟器/API_Test.py`。

环境与模型要求：
1. 优先使用当前环境中的 `DASHSCOPE_API_KEY`。
2. 默认使用 `DIRECTOR_PROVIDER_MODE=auto`。
3. 如需参考百炼兼容调用方式，直接看 `API_Test.py`。

你的目标是交付代码，而不是只写分析。

