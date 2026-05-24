from __future__ import annotations

import json
import logging
import re
from typing import Any

from .config import DEFAULT_TOPIC, TopicConfig
from .collector import normalize_channel_name
from .models import ClassifiedVideo, VideoDetails

LOGGER = logging.getLogger(__name__)

WATCH_PRIORITIES = {"High", "Medium", "Low"}


class VideoClassifier:
    def __init__(
        self,
        topic_config: TopicConfig,
        openai_api_key: str | None = None,
        allow_rule_based_fallback: bool = False,
        model: str = "gpt-4.1-mini",
    ) -> None:
        self.topic_config = topic_config
        self.openai_api_key = openai_api_key
        self.allow_rule_based_fallback = allow_rule_based_fallback
        self.model = model

    def classify_many(self, videos: list[VideoDetails]) -> list[ClassifiedVideo]:
        classified = [self.classify(video) for video in videos]
        allowed = set(self.topic_config.include_topics)
        return [item for item in classified if item.topic in allowed]

    def classify(self, video: VideoDetails) -> ClassifiedVideo:
        if not self.openai_api_key:
            return self._rule_based(video)

        try:
            payload = self._classify_with_openai(video)
            return ClassifiedVideo(
                video=video,
                topic=self._valid_topic(payload.get("topic")),
                subtopic=str(payload.get("subtopic") or ""),
                summary_ko=str(payload.get("summary_ko") or ""),
                watch_priority=self._valid_priority(payload.get("watch_priority")),
                keywords=[str(keyword) for keyword in payload.get("keywords", [])][:8],
            )
        except Exception as exc:
            if not self.allow_rule_based_fallback:
                raise
            LOGGER.warning("OpenAI classification failed; using rule-based fallback: %s", exc)
            self.openai_api_key = None
            return self._rule_based(video)

    def _classify_with_openai(self, video: VideoDetails) -> dict[str, Any]:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is not installed") from exc

        client = OpenAI(api_key=self.openai_api_key)
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "topic": {"type": "string", "enum": self.topic_config.topics},
                "subtopic": {"type": "string"},
                "summary_ko": {"type": "string"},
                "watch_priority": {"type": "string", "enum": ["High", "Medium", "Low"]},
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 8,
                },
            },
            "required": ["topic", "subtopic", "summary_ko", "watch_priority", "keywords"],
        }
        response = client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You classify and summarize YouTube videos for a Korean daily digest. "
                        "Use only the provided metadata. If the description is sparse, say so briefly. "
                        "Return concise Korean summaries."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "title": video.title,
                            "channel": video.channel_title,
                            "description": video.description[:4000],
                            "publishedAt": video.published_at.isoformat(),
                            "topics": self.topic_config.topics,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "youtube_video_digest",
                    "schema": schema,
                    "strict": True,
                }
            },
        )
        return json.loads(response.output_text)

    def _rule_based(self, video: VideoDetails) -> ClassifiedVideo:
        title_text = video.title.lower()
        classification_text = f"{video.title}\n{video.channel_title}".lower()
        summary_text = f"{video.title}\n{video.channel_title}\n{video.description}".lower()
        selected_topic = _best_topic(title_text, self.topic_config.keyword_map)
        if selected_topic == DEFAULT_TOPIC:
            selected_topic = _best_topic(classification_text, self.topic_config.keyword_map)
        if selected_topic == DEFAULT_TOPIC:
            selected_topic = self._topic_from_channel(video.channel_title)

        description = video.description.strip().replace("\n", " ")
        if description:
            summary = description[:180]
            if len(description) > 180:
                summary += "..."
        else:
            summary = "제목과 채널 정보만 확인 가능해 상세 요약은 제한적이다."

        return ClassifiedVideo(
            video=video,
            topic=selected_topic,
            subtopic="자동 키워드 분류",
            summary_ko=summary,
            watch_priority="Medium",
            keywords=_matched_keywords(summary_text, self.topic_config.keyword_map.get(selected_topic, [])),
        )

    def _valid_topic(self, topic: Any) -> str:
        topic_str = str(topic or DEFAULT_TOPIC)
        if topic_str in self.topic_config.topics:
            return topic_str
        return DEFAULT_TOPIC

    def _valid_priority(self, priority: Any) -> str:
        priority_str = str(priority or "Medium")
        if priority_str in WATCH_PRIORITIES:
            return priority_str
        return "Medium"

    def _topic_from_channel(self, channel_title: str) -> str:
        normalized_channel = normalize_channel_name(channel_title)
        for configured_channel, topic in self.topic_config.channel_topic_map.items():
            if normalize_channel_name(configured_channel) == normalized_channel:
                return topic
        return DEFAULT_TOPIC


def _matched_keywords(text: str, keywords: list[str]) -> list[str]:
    normalized_text = text.lower()
    return [keyword for keyword in keywords if _keyword_in_text(normalized_text, keyword.lower())][:8]


def _keyword_in_text(text: str, keyword: str) -> bool:
    if keyword.isascii() and keyword.replace("&", "").replace(" ", "").replace(".", "").isalnum():
        return re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", text) is not None
    return keyword in text


def _topic_matches(text: str, keywords: list[str]) -> bool:
    matched = _matched_keywords(text, keywords)
    return bool(matched)


def _best_topic(text: str, keyword_map: dict[str, list[str]]) -> str:
    best_topic = DEFAULT_TOPIC
    best_score = 0
    for topic, keywords in keyword_map.items():
        matched = _matched_keywords(text, keywords)
        if not _topic_matches(text, keywords):
            continue
        score = len(matched)
        if any(keyword in {"ai", "llm", "chatgpt", "claude", "openai"} for keyword in matched):
            score += 2
        if any(keyword in {"금리", "주식", "환율", "cpi", "부동산", "재테크", "금융", "코스피", "코스닥", "나스닥", "비트코인", "채권", "연준", "fomc"} for keyword in matched):
            score += 2
        if score > best_score:
            best_topic = topic
            best_score = score
    return best_topic
