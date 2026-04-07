from __future__ import annotations

from app.services.simulation.scene_registry import (
    SCENE_01_CODE,
    SCENE_02_CODE,
    SCENE_03_CODE,
    SCENE_04_CODE,
    SCENE_05_CODE,
    SCENE_06_CODE,
    SCENE_07_CODE,
)


SCENE_CONFIG = {
    SCENE_01_CODE: {
        "scene_goal": "建立全员对全员的第一轮关系偏置和场内张力图",
        "scene_frame": "阳光房初见，围绕城市通勤、节目第一印象与彼此气场做第一轮多人破冰。",
        "scene_level": "level_01_beginning_appeal",
        "min_turns": 6,
        "max_turns": 6,
        "planned_rounds": 3,
        "phase_outline": [
            "Round 1 opening",
            "Round 1 response cluster",
            "Round 2 follow-up",
            "Round 2 cross-talk",
            "Round 3 escalation / clarification",
        ],
    },
    SCENE_02_CODE: {
        "scene_goal": "从表面好感转向互动舒适度、被理解感与多人场中的偏好迁移",
        "scene_frame": "第一次自由交流，围绕工作节奏、亲密关系期待和节目内的观察展开更深一点的多人对话。",
        "scene_level": "level_01_beginning_appeal",
        "min_turns": 8,
        "max_turns": 8,
        "planned_rounds": 4,
        "phase_outline": [
            "Round 1 topic pick-up",
            "Round 2 deeper question",
            "Round 3 direct cross-talk",
            "Round 4 clarification / choice tension",
        ],
    },
    SCENE_03_CODE: {
        "scene_goal": "通过随机 1v1 约会打破初始偏好，识别意外升温与无火花组合",
        "scene_frame": "抽签后进行随机约会，用户策略只能轻微影响匹配倾向，重点观察偶然连接。",
        "scene_level": "level_01_beginning_appeal",
        "min_turns": 4,
        "max_turns": 16,
        "planned_rounds": 3,
        "phase_outline": [
            "Round 1 random matching",
            "Round 2 mini dates",
            "Round 3 scene wrap-up",
        ],
    },
    SCENE_04_CODE: {
        "scene_goal": "把随机约会后的信号放回全员晚餐场，暴露竞争关系与社交稳定度",
        "scene_frame": "多人晚餐场中，偏好释放、旁观判断和竞争压力同步发生并影响下一场主动选择。",
        "scene_level": "level_02_relationship_promotion",
        "min_turns": 8,
        "max_turns": 10,
        "planned_rounds": 4,
        "phase_outline": [
            "Round 1 dinner warm-up",
            "Round 2 attention shift",
            "Round 3 competition exposure",
            "Round 4 closing residue",
        ],
    },
    SCENE_05_CODE: {
        "scene_goal": "通过每位参与者主动选择 1 人交流，明确关系推进方向并识别互选与错位",
        "scene_frame": "承接多人晚餐后的公开信号，每位参与者做出一次主动选择并完成一轮交流。",
        "scene_level": "level_02_relationship_promotion",
        "min_turns": 4,
        "max_turns": 10,
        "planned_rounds": 3,
        "phase_outline": [
            "Round 1 choose target",
            "Round 2 directed conversation",
            "Round 3 mismatch residue",
        ],
    },
    SCENE_06_CODE: {
        "scene_goal": "通过私密信号揭示真实偏好与期待落空，放大关系误判与推进意愿",
        "scene_frame": "每位参与者至少发送一条私密信号，在揭示阶段观察被接收、被误判与落空波动。",
        "scene_level": "level_02_relationship_promotion",
        "min_turns": 4,
        "max_turns": 8,
        "planned_rounds": 3,
        "phase_outline": [
            "Round 1 private signal send",
            "Round 2 interpretation and reveal",
            "Round 3 expectation miss settling",
        ],
    },
    SCENE_07_CODE: {
        "scene_goal": "把私密信号转成主动邀约行动，显化竞争、拒绝与fallback分化",
        "scene_frame": "全员进入主动邀约与竞争阶段，处理撞车邀请、被拒后转向与退场。",
        "scene_level": "level_02_relationship_promotion",
        "min_turns": 4,
        "max_turns": 8,
        "planned_rounds": 3,
        "phase_outline": [
            "Round 1 invitation launch",
            "Round 2 competition resolution",
            "Round 3 fallback or withdrawal",
        ],
    },
}
