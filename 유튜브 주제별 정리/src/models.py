from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class SubscriptionChannel:
    channel_id: str
    title: str
    description: str = ""
    thumbnail_url: str = ""


@dataclass(frozen=True)
class ActivityUpload:
    video_id: str
    channel_id: str
    channel_title: str
    published_at: datetime


@dataclass(frozen=True)
class VideoDetails:
    video_id: str
    title: str
    description: str
    channel_id: str
    channel_title: str
    published_at: datetime
    thumbnail_url: str
    duration: str
    view_count: int | None
    url: str


@dataclass(frozen=True)
class ClassifiedVideo:
    video: VideoDetails
    topic: str
    subtopic: str
    summary_ko: str
    watch_priority: str
    keywords: list[str] = field(default_factory=list)

