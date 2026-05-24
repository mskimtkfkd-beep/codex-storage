from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from .models import SubscriptionChannel, VideoDetails
from .youtube_client import YouTubeClient

LOGGER = logging.getLogger(__name__)


def cutoff_for_lookback(now: datetime | None = None, hours: int = 24) -> datetime:
    reference = now or datetime.now(timezone.utc)
    return reference.astimezone(timezone.utc) - timedelta(hours=hours)


def collect_recent_videos(
    youtube_client: YouTubeClient,
    now: datetime | None = None,
    lookback_hours: int = 24,
    tracked_channels: list[str] | None = None,
) -> list[VideoDetails]:
    cutoff = cutoff_for_lookback(now=now, hours=lookback_hours)
    channels = youtube_client.list_subscriptions()
    channels = filter_tracked_channels(channels, tracked_channels or [])

    candidate_ids: list[str] = []
    for channel in channels:
        uploads = youtube_client.list_recent_upload_activities(channel, cutoff)
        candidate_ids.extend(upload.video_id for upload in uploads if upload.published_at >= cutoff)

    videos = youtube_client.get_videos(candidate_ids)
    filtered = [video for video in videos if video.published_at >= cutoff]
    filtered.sort(key=lambda video: video.published_at, reverse=True)
    LOGGER.info(
        "Collected recent videos candidates=%s filtered=%s cutoff=%s",
        len(candidate_ids),
        len(filtered),
        cutoff.isoformat(),
    )
    return filtered


def filter_tracked_channels(
    channels: list[SubscriptionChannel],
    tracked_channels: list[str],
) -> list[SubscriptionChannel]:
    if not tracked_channels:
        return channels

    tracked_names = {normalize_channel_name(channel) for channel in tracked_channels}
    filtered = [
        channel
        for channel in channels
        if normalize_channel_name(channel.title) in tracked_names
    ]
    missing = sorted(tracked_names - {normalize_channel_name(channel.title) for channel in filtered})
    if missing:
        LOGGER.warning("Tracked channels not found in subscriptions: %s", ", ".join(missing))
    LOGGER.info("Filtered tracked channels count=%s total_subscriptions=%s", len(filtered), len(channels))
    return filtered


def normalize_channel_name(value: str) -> str:
    normalized = value.casefold()
    for token in (" ", "_", "-", "ㅣ", "|", ":", "[", "]"):
        normalized = normalized.replace(token, "")
    return normalized
