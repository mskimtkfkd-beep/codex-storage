from __future__ import annotations

from datetime import datetime, timezone

from src.classifier import VideoClassifier
from src.config import TopicConfig
from src.models import VideoDetails


def test_rule_based_classifier_uses_keywords() -> None:
    config = TopicConfig(
        topics=["AI/기술", "기타"],
        keyword_map={"AI/기술": ["llm", "자동화"]},
        include_topics=["AI/기술"],
        tracked_channels=[],
        channel_topic_map={},
    )
    classifier = VideoClassifier(config, allow_rule_based_fallback=True)
    video = VideoDetails(
        video_id="v1",
        title="LLM 업무 자동화",
        description="업무 자동화 사례를 설명합니다.",
        channel_id="c1",
        channel_title="AI Channel",
        published_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
        thumbnail_url="",
        duration="PT1M",
        view_count=None,
        url="https://www.youtube.com/watch?v=v1",
    )

    result = classifier.classify(video)

    assert result.topic == "AI/기술"
    assert result.watch_priority == "Medium"
    assert "llm" in result.keywords


def test_rule_based_classifier_uses_channel_topic_when_keywords_do_not_match() -> None:
    config = TopicConfig(
        topics=["AI/기술", "경제/재테크", "기타"],
        keyword_map={"AI/기술": ["llm"], "경제/재테크": ["금리"]},
        include_topics=["AI/기술", "경제/재테크"],
        tracked_channels=["CONNECT AI LAB"],
        channel_topic_map={"CONNECT AI LAB": "AI/기술"},
    )
    classifier = VideoClassifier(config, allow_rule_based_fallback=True)
    video = VideoDetails(
        video_id="v1",
        title="새로운 영상",
        description="키워드가 없는 설명입니다.",
        channel_id="c1",
        channel_title="connect ai lab",
        published_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
        thumbnail_url="",
        duration="PT1M",
        view_count=None,
        url="https://www.youtube.com/watch?v=v1",
    )

    result = classifier.classify(video)

    assert result.topic == "AI/기술"


def test_rule_based_classifier_prefers_title_topic_over_channel_default() -> None:
    config = TopicConfig(
        topics=["경제/재테크", "정치/사회", "기타"],
        keyword_map={"경제/재테크": ["경제"], "정치/사회": ["트럼프"]},
        include_topics=["경제/재테크", "정치/사회", "기타"],
        tracked_channels=["연합뉴스경제TV"],
        channel_topic_map={"연합뉴스경제TV": "경제/재테크"},
    )
    classifier = VideoClassifier(config, allow_rule_based_fallback=True)
    video = VideoDetails(
        video_id="v1",
        title="백악관 접근하려던 총격범 사살, 트럼프는 무사",
        description="",
        channel_id="c1",
        channel_title="연합뉴스경제TV",
        published_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
        thumbnail_url="",
        duration="PT1M",
        view_count=None,
        url="https://www.youtube.com/watch?v=v1",
    )

    result = classifier.classify(video)

    assert result.topic == "정치/사회"
