from __future__ import annotations

from datetime import datetime, timezone

from src.classifier import VideoClassifier
from src.config import TopicConfig
from src.models import VideoDetails


def test_rule_based_classifier_uses_video_channel_metadata_defaults() -> None:
    config = TopicConfig(
        topics=["AI/湲곗닠", "湲고?"],
        keyword_map={"AI/湲곗닠": ["llm"]},
        include_topics=["AI/湲곗닠", "湲고?"],
        tracked_channels=[],
        channel_topic_map={},
    )
    classifier = VideoClassifier(config, allow_rule_based_fallback=True)
    video = VideoDetails(
        video_id="v1",
        title="No keyword title",
        description="No keyword description",
        channel_id="c1",
        channel_title="Configured Channel",
        published_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
        thumbnail_url="",
        duration="PT1M",
        view_count=None,
        url="https://www.youtube.com/watch?v=v1",
        channel_importance="high",
        default_topic="AI/湲곗닠",
        summary_required=True,
    )

    result = classifier.classify(video)

    assert result.topic == "AI/湲곗닠"
    assert result.watch_priority == "High"
