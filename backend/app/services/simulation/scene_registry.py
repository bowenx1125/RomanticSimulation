SCENE_01_CODE = "scene_01_intro"
SCENE_02_CODE = "scene_02_free_talk"
SCENE_03_CODE = "scene_03_random_date"
SCENE_04_CODE = "scene_04_group_dinner"
SCENE_05_CODE = "scene_05_conversation_choosing"

PHASE3_SCENE_REGISTRY = {
    SCENE_01_CODE: {
        "scene_index": 1,
        "runtime": "multi_round_group",
        "status": "active",
        "min_turns": 6,
        "max_turns": 12,
    },
    SCENE_02_CODE: {
        "scene_index": 2,
        "runtime": "multi_round_group",
        "status": "active",
        "min_turns": 8,
        "max_turns": 16,
    },
    SCENE_03_CODE: {
        "scene_index": 3,
        "runtime": "multi_round_group",
        "status": "active",
        "min_turns": 4,
        "max_turns": 16,
    },
    SCENE_04_CODE: {
        "scene_index": 4,
        "runtime": "multi_round_group",
        "status": "active",
        "min_turns": 8,
        "max_turns": 16,
    },
    SCENE_05_CODE: {
        "scene_index": 5,
        "runtime": "multi_round_group",
        "status": "active",
        "min_turns": 4,
        "max_turns": 14,
    },
}
