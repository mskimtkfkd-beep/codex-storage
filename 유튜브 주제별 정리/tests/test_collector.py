from __future__ import annotations

from datetime import datetime, timezone

from src.collector import collect_recent_videos, cutoff_for_lookback, filter_tracked_channels
from src.models import ActivityUpload, SubscriptionChannel, TrackedChannel, VideoDetails


def test_cutoff_for_lookback_uses_exact_24_hours() -> None:
    now = datetime(2026, 5, 24, 8, 0, tzinfo=timezone.utc)
    assert cutoff_for_lookback(now) == datetime(2026, 5, 23, 8, 0, tzinfo=timezone.utc)


def test_collect_recent_videos_includes_boundary_and_excludes_older() -> None:
    now = datetime(2026, 5, 24, 8, 0, tzinfo=timezone.utc)
    cutoff = datetime(2026, 5, 23, 8, 0, tzinfo=timezone.utc)
    older = datetime(2026, 5, 23, 7, 59, 59, tzinfo=timezone.utc)
    client = FakeYouTubeClient(
        activities=[
            ActivityUpload("boundary", "c1", "Channel", cutoff),
            ActivityUpload("older", "c1", "Channel", older),
        ],
        videos=[
            make_video("boundary", cutoff),
            make_video("older", older),
        ],
    )

    result = collect_recent_videos(client, now=now)

    assert [video.video_id for video in result] == ["boundary"]


def test_collect_recent_videos_filters_to_tracked_channels() -> None:
    now = datetime(2026, 5, 24, 8, 0, tzinfo=timezone.utc)
    cutoff = datetime(2026, 5, 23, 8, 0, tzinfo=timezone.utc)
    client = FakeYouTubeClient(
        activities=[
            ActivityUpload("tracked", "c1", "Tracked Channel", cutoff),
            ActivityUpload("other", "c2", "Other Channel", cutoff),
        ],
        videos=[
            make_video("tracked", cutoff, channel_id="c1", channel_title="Tracked Channel"),
            make_video("other", cutoff, channel_id="c2", channel_title="Other Channel"),
        ],
        channels=[
            SubscriptionChannel(channel_id="c1", title="Tracked Channel"),
            SubscriptionChannel(channel_id="c2", title="Other Channel"),
        ],
    )

    result = collect_recent_videos(client, now=now, tracked_channels=["trackedchannel"])

    assert [video.video_id for video in result] == ["tracked"]


def test_collect_recent_videos_uses_configured_public_channels() -> None:
    now = datetime(2026, 5, 24, 8, 0, tzinfo=timezone.utc)
    cutoff = datetime(2026, 5, 23, 8, 0, tzinfo=timezone.utc)
    channels = [
        TrackedChannel(
            channel_id="c1",
            title="Configured Channel",
            importance="high",
            default_topic="AI/기술",
            summary_required=True,
        )
    ]
    client = FakeYouTubeClient(
        activities=[ActivityUpload("configured", "c1", "Configured Channel", cutoff)],
        videos=[make_video("configured", cutoff, channel_id="c1", channel_title="Configured Channel")],
        channels=[],
    )

    result = collect_recent_videos(client, now=now, configured_channels=channels)

    assert client.list_subscriptions_called is False
    assert client.upload_playlist_requests == ["c1"]
    assert [video.video_id for video in result] == ["configured"]
    assert result[0].channel_importance == "high"
    assert result[0].default_topic == "AI/기술"


def test_filter_tracked_channels_normalizes_common_name_variants() -> None:
    channels = [
        SubscriptionChannel(channel_id="c1", title="안될공학 - IT 테크 신기술"),
        SubscriptionChannel(channel_id="c2", title="머니올라_KBS"),
    ]

    result = filter_tracked_channels(channels, ["안될공학 it 테크 신기술", "머니올라 kbs"])

    assert [channel.channel_id for channel in result] == ["c1", "c2"]


class FakeYouTubeClient:
    def __init__(
        self,
        activities: list[ActivityUpload],
        videos: list[VideoDetails],
        channels: list[SubscriptionChannel] | None = None,
    ) -> None:
        self.activities = activities
        self.videos = videos
        self.channels = channels or [SubscriptionChannel(channel_id="c1", title="Channel")]
        self.list_subscriptions_called = False
        self.upload_playlist_requests: list[str] = []

    def list_subscriptions(self) -> list[SubscriptionChannel]:
        self.list_subscriptions_called = True
        return self.channels

    def list_recent_upload_activities(
        self,
        channel: SubscriptionChannel,
        published_after: datetime,
    ) -> list[ActivityUpload]:
        return [activity for activity in self.activities if activity.channel_id == channel.channel_id]

    def get_videos(self, video_ids: list[str]) -> list[VideoDetails]:
        ids = set(video_ids)
        return [video for video in self.videos if video.video_id in ids]

    def get_upload_playlist_id(self, channel: TrackedChannel) -> str:
        self.upload_playlist_requests.append(channel.channel_id)
        return f"UU{channel.channel_id}"

    def list_recent_playlist_uploads(
        self,
        channel: TrackedChannel,
        uploads_playlist_id: str,
        published_after: datetime,
    ) -> list[ActivityUpload]:
        return [activity for activity in self.activities if activity.channel_id == channel.channel_id]


def make_video(
    video_id: str,
    published_at: datetime,
    channel_id: str = "c1",
    channel_title: str = "Channel",
) -> VideoDetails:
    return VideoDetails(
        video_id=video_id,
        title=f"Video {video_id}",
        description="description",
        channel_id=channel_id,
        channel_title=channel_title,
        published_at=published_at,
        thumbnail_url="https://example.com/thumb.jpg",
        duration="PT1M",
        view_count=1,
        url=f"https://www.youtube.com/watch?v={video_id}",
    )
