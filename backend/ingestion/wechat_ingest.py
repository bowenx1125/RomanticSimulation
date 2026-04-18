from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from app.schemas.project import ParticipantEditablePersonality, ParticipantImportPayload


SEGMENT_HEADER_RE = re.compile(r"^###\s+片段\d+（(?P<date>\d{4}-\d{2}-\d{2})）$")
MESSAGE_RE = re.compile(r"^(?P<speaker>[^:：]+)[:：]\s*(?P<text>.+?)\s*$")


@dataclass
class ChatMessage:
    speaker: str
    text: str
    timestamp: str | None = None


@dataclass
class WeChatRuleFeatures:
    initiative_score: float
    avg_message_length: float
    response_latency: float | None
    message_count: int
    target_message_count: int
    counterpart_message_count: int
    question_ratio: float
    exclamation_ratio: float


@dataclass
class WeChatLLMFeatures:
    emotional_expression: float
    tone: str
    attachment_style: str
    preferred_traits: list[str]
    disliked_traits: list[str]
    summary: str


@dataclass
class WeChatIngestResult:
    participant_name: str
    parsed_messages: list[ChatMessage]
    rule_features: WeChatRuleFeatures
    llm_features: WeChatLLMFeatures
    editable_personality: dict
    personality_summary: dict


def parse_markdown(markdown_text: str) -> list[ChatMessage]:
    messages: list[ChatMessage] = []
    current_date: str | None = None

    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line or line == "---":
            continue

        header_match = SEGMENT_HEADER_RE.match(line)
        if header_match:
            current_date = header_match.group("date")
            continue

        message_match = MESSAGE_RE.match(line)
        if not message_match:
            continue

        messages.append(
            ChatMessage(
                speaker=message_match.group("speaker").strip(),
                text=message_match.group("text").strip(),
                timestamp=current_date,
            )
        )

    return messages


def extract_features(messages: list[ChatMessage], target_name: str) -> WeChatRuleFeatures:
    if not messages:
        raise ValueError("No chat messages could be parsed from the markdown file.")

    normalized_target = target_name.casefold()
    target_messages = [message for message in messages if message.speaker.casefold() == normalized_target]
    counterpart_messages = [message for message in messages if message.speaker.casefold() != normalized_target]

    if not target_messages:
        raise ValueError(f"No messages found for target participant '{target_name}'.")

    initiative_openings = 0
    total_segments = 0
    previous_date: str | None = None
    previous_speaker: str | None = None
    for message in messages:
        is_new_segment = message.timestamp != previous_date
        if is_new_segment:
            total_segments += 1
            if message.speaker.casefold() == normalized_target:
                initiative_openings += 1
        previous_date = message.timestamp
        previous_speaker = message.speaker

    if total_segments == 0:
        total_segments = 1

    initiative_score = initiative_openings / total_segments
    avg_message_length = mean(len(message.text) for message in target_messages)
    question_ratio = sum("?" in message.text or "？" in message.text for message in target_messages) / len(
        target_messages
    )
    exclamation_ratio = sum("!" in message.text or "！" in message.text for message in target_messages) / len(
        target_messages
    )

    # Cleaned markdown contains date-level slices but no exact times, so latency is unavailable.
    response_latency = None

    return WeChatRuleFeatures(
        initiative_score=initiative_score,
        avg_message_length=avg_message_length,
        response_latency=response_latency,
        message_count=len(messages),
        target_message_count=len(target_messages),
        counterpart_message_count=len(counterpart_messages),
        question_ratio=question_ratio,
        exclamation_ratio=exclamation_ratio,
    )


def call_llm(messages: list[ChatMessage], target_name: str) -> WeChatLLMFeatures:
    from openai import OpenAI
    from app.core.config import get_settings

    settings = get_settings()
    client = OpenAI(
        api_key=settings.dashscope_api_key,
        base_url=settings.dashscope_base_url,
        timeout=20.0,
    )

    sample_lines = [
        f"{message.speaker}: {message.text}"
        for message in messages[:80]
    ]
    prompt_payload = {
        "task": "Analyze the romantic-interaction style of the target speaker from WeChat dialogue.",
        "target_name": target_name,
        "requirements": {
            "emotional_expression": "0 to 1 float, where 1 means highly expressive and emotionally explicit",
            "tone": ["playful", "cold", "neutral"],
            "attachment_style": ["secure", "avoidant", "anxious"],
            "preferred_traits": "2 to 4 short lowercase trait tags describing what kind of person the target likely prefers in romance",
            "disliked_traits": "2 to 4 short lowercase trait tags describing what kind of person the target likely dislikes or avoids in romance",
            "summary": "One concise Chinese sentence describing interpersonal style",
        },
        "rules": [
            "Only analyze the target speaker, not the counterpart.",
            "Be deterministic and conservative. Do not hallucinate trauma or life history.",
            "Infer from wording style, initiative, responsiveness, warmth, explicit affection, and avoidance patterns.",
            "Trait tags should be short and reusable, such as warm, proactive, stable, cold, ambiguous, clingy.",
            "Return valid JSON only.",
        ],
        "dialogue_sample": sample_lines,
    }

    completion = client.chat.completions.create(
        model=settings.director_model,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "You analyze behavioral patterns from chat logs. "
                    "Return a single JSON object with keys emotional_expression, tone, attachment_style, preferred_traits, disliked_traits, summary."
                ),
            },
            {"role": "user", "content": json.dumps(prompt_payload, ensure_ascii=False)},
        ],
        response_format={"type": "json_object"},
    )
    content = completion.choices[0].message.content or "{}"
    payload = json.loads(extract_json_block(content))

    emotional_expression = float(payload.get("emotional_expression", 0.5))
    tone = str(payload.get("tone", "neutral")).strip().lower()
    attachment_style = str(payload.get("attachment_style", "secure")).strip().lower()
    preferred_traits = normalize_trait_list(payload.get("preferred_traits"))
    disliked_traits = normalize_trait_list(payload.get("disliked_traits"))
    summary = str(payload.get("summary", "")).strip() or f"{target_name} 的表达偏谨慎，仍需更多样本确认。"

    if tone not in {"playful", "cold", "neutral"}:
        tone = "neutral"
    if attachment_style not in {"secure", "avoidant", "anxious"}:
        attachment_style = "secure"

    return WeChatLLMFeatures(
        emotional_expression=max(0.0, min(1.0, emotional_expression)),
        tone=tone,
        attachment_style=attachment_style,
        preferred_traits=preferred_traits,
        disliked_traits=disliked_traits,
        summary=summary,
    )


def map_to_personality(
    target_name: str,
    rule_features: WeChatRuleFeatures,
    llm_features: WeChatLLMFeatures,
) -> tuple[dict, ParticipantImportPayload]:
    initiative = clamp_0_100(35 + rule_features.initiative_score * 45 + rule_features.question_ratio * 20)
    emotional_openness = clamp_0_100(
        25
        + llm_features.emotional_expression * 55
        + rule_features.exclamation_ratio * 10
        + min(rule_features.avg_message_length, 20) * 0.6
    )
    extroversion = clamp_0_100(
        30
        + rule_features.initiative_score * 30
        + min(rule_features.avg_message_length, 18) * 1.2
        + (8 if llm_features.tone == "playful" else -6 if llm_features.tone == "cold" else 0)
    )

    conflict_style = {
        "secure": "steady_boundary",
        "avoidant": "observe_then_withdraw",
        "anxious": "press_then_clarify",
    }[llm_features.attachment_style]
    self_esteem_stability = {
        "secure": 68,
        "avoidant": 54,
        "anxious": 43,
    }[llm_features.attachment_style]

    communication_style = {
        "playful": "direct",
        "cold": "gentle",
        "neutral": "balanced",
    }[llm_features.tone]
    reassurance_need = {
        "secure": "medium",
        "avoidant": "low",
        "anxious": "high",
    }[llm_features.attachment_style]

    editable_personality = ParticipantEditablePersonality(
        extroversion=extroversion,
        initiative=initiative,
        emotional_openness=emotional_openness,
        attachment_style=llm_features.attachment_style,
        conflict_style=conflict_style,
        self_esteem_stability=self_esteem_stability,
        pace_preference="gradual_but_clear",
        commitment_goal="serious_relationship",
        preferred_traits=llm_features.preferred_traits,
        disliked_traits=llm_features.disliked_traits,
        boundaries={"hard_boundaries": [], "soft_boundaries": []},
        expression_style={
            "communication_style": communication_style,
            "reassurance_need": reassurance_need,
        },
    )

    participant_payload = ParticipantImportPayload(
        name=target_name,
        cast_role="main_cast",
        background_summary=f"基于 WeChat 聊天记录提取出的互动画像，样本消息 {rule_features.target_message_count} 条。",
        personality_summary=llm_features.summary,
        attachment_style=llm_features.attachment_style,
        personality_tags=[
            llm_features.tone,
            llm_features.attachment_style,
            *llm_features.preferred_traits[:2],
            "wechat_ingested",
        ],
        preferred_traits=llm_features.preferred_traits,
        disliked_traits=llm_features.disliked_traits,
        editable_personality=editable_personality,
        is_active=True,
    )

    personality_summary = {
        "extroversion": extroversion,
        "emotional_openness": emotional_openness,
        "initiative": initiative,
        "attachment_style": llm_features.attachment_style,
        "tone": llm_features.tone,
        "emotional_expression": llm_features.emotional_expression,
        "preferred_traits": llm_features.preferred_traits,
        "disliked_traits": llm_features.disliked_traits,
        "rule_features": {
            "initiative_score": round(rule_features.initiative_score, 3),
            "avg_message_length": round(rule_features.avg_message_length, 2),
            "response_latency": rule_features.response_latency,
            "message_count": rule_features.message_count,
            "target_message_count": rule_features.target_message_count,
        },
        "llm_summary": llm_features.summary,
    }

    return personality_summary, participant_payload


def create_participant(file_path: str, markdown_text: str) -> WeChatIngestResult:
    participant_name = Path(file_path).stem
    parsed_messages = parse_markdown(markdown_text)
    rule_features = extract_features(parsed_messages, participant_name)
    llm_features = call_llm(parsed_messages, participant_name)
    personality_summary, participant_payload = map_to_personality(
        participant_name,
        rule_features,
        llm_features,
    )
    return WeChatIngestResult(
        participant_name=participant_name,
        parsed_messages=parsed_messages,
        rule_features=rule_features,
        llm_features=llm_features,
        editable_personality=participant_payload.editable_personality.model_dump(),
        personality_summary=personality_summary,
    )


def build_participant_payload_from_markdown(file_path: str, markdown_text: str) -> tuple[WeChatIngestResult, ParticipantImportPayload]:
    participant_name = Path(file_path).stem
    parsed_messages = parse_markdown(markdown_text)
    rule_features = extract_features(parsed_messages, participant_name)
    llm_features = call_llm(parsed_messages, participant_name)
    personality_summary, participant_payload = map_to_personality(
        participant_name,
        rule_features,
        llm_features,
    )
    return (
        WeChatIngestResult(
            participant_name=participant_name,
            parsed_messages=parsed_messages,
            rule_features=rule_features,
            llm_features=llm_features,
            editable_personality=participant_payload.editable_personality.model_dump(),
            personality_summary=personality_summary,
        ),
        participant_payload,
    )


def extract_json_block(text: str) -> str:
    match = re.search(r"\{.*\}", text, flags=re.S)
    return match.group(0) if match else text


def clamp_0_100(value: float) -> int:
    return max(0, min(100, int(round(value))))


def normalize_trait_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        text = str(item).strip().lower().replace(" ", "_")
        if not text or text in normalized:
            continue
        normalized.append(text)
    return normalized[:4]
